"""Moteur de calcul de devis — 7 postes (Sprint 3, Jalon J2).

Modèle assumé en rupture du PRD initial après confrontation aux 1 243
dossiers ICE Étiquettes (avril 2026) :

    P1 Matière       = ml × largeur_bande_m × prix_m²_complexe
    P2 Encres        = ml × largeur_bande_m × nb_couleurs × ratio_encre
    P3 Outillage     = saisie deviseur (0 sur recommande)
    P4 Roulage       = (calage_h + roulage_h) × cout_horaire_machine
                       avec roulage_h = ml / vitesse_moyenne_machine
    P5 Chutes        = P1 × taux_chutes_entreprise
    P6 Finition      = sum(opérations internes selon unité de facturation)
                     + sum(forfaits sous-traitance saisis à la volée)
    P7 Frais gx      = heures_dossier × cout_horaire_structure
                       avec cout_horaire_structure = total_charges / heures_productives

    Coût de revient = P1 + P2 + P3 + P4 + P5 + P6 + P7
    Prix vente HT   = Coût de revient × (1 + pct_marge)

`pct_marge` provient du curseur deviseur (`pct_marge_override` du payload)
ou, à défaut, de `entreprise.pct_marge_defaut` (18 % preset Compétitif).

Les méthodes `_pX_xxx` sont **statiques et pures** : elles prennent des
primitives Python et retournent un float. Elles sont testables sans DB.
La méthode `compute()` orchestre les lookups DB et appelle les méthodes
pures dans l'ordre.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import (
    ChargeMensuelle,
    Complexe,
    Entreprise,
    Machine,
    OperationFinition,
)
from app.schemas.devis import DevisInput, DevisOutput


class CalculateurError(ValueError):
    """Erreur métier remontée par le moteur (ressource inconnue, etc.).

    Convertie en HTTP 422 par le router.
    """


# ---------------------------------------------------------------------------
# Méthodes pures — testables sans DB
# ---------------------------------------------------------------------------


def _surface_m2(ml: float, largeur_bande_m: float) -> float:
    return ml * largeur_bande_m


def _p1_matiere(ml: float, largeur_bande_m: float, prix_m2_eur: float) -> float:
    return ml * largeur_bande_m * prix_m2_eur


def _p2_encres(
    ml: float, largeur_bande_m: float, nb_couleurs: int, ratio_encre_m2_couleur: float
) -> float:
    return ml * largeur_bande_m * nb_couleurs * ratio_encre_m2_couleur


def _p3_outillage(outillage_eur: float) -> float:
    return outillage_eur


def _duree_roulage_h(ml: float, vitesse_moyenne_m_h: float) -> float:
    return ml / vitesse_moyenne_m_h


def _p4_roulage(
    duree_calage_h: float, duree_roulage_h: float, cout_horaire_machine: float
) -> float:
    return (duree_calage_h + duree_roulage_h) * cout_horaire_machine


def _p5_chutes(p1_matiere_eur: float, taux_chutes: float) -> float:
    return p1_matiere_eur * taux_chutes


def _p6_finition_op(
    unite: str,
    cout_unitaire_eur: float,
    ml: float,
    largeur_bande_m: float,
    etiq_total: int,
) -> tuple[float, float]:
    """Coût + temps consommé pour une opération de finition interne.

    Le temps n'est pas calculé ici — il l'est dans `_duree_finition_h_for_op`
    qui prend `temps_minutes_unite`. Cette fonction renvoie (cout, 0.0)
    pour respecter l'idée 1 fonction = 1 responsabilité.
    """
    cout = _cout_op_selon_unite(unite, cout_unitaire_eur, ml, largeur_bande_m, etiq_total)
    return cout, 0.0


def _cout_op_selon_unite(
    unite: str,
    cout_unitaire_eur: float,
    ml: float,
    largeur_bande_m: float,
    etiq_total: int,
) -> float:
    """Applique l'unité de facturation (m2 / ml / unite / millier)."""
    if unite == "m2":
        return ml * largeur_bande_m * cout_unitaire_eur
    if unite == "ml":
        return ml * cout_unitaire_eur
    if unite == "unite":
        return etiq_total * cout_unitaire_eur
    if unite == "millier":
        return etiq_total / 1000.0 * cout_unitaire_eur
    raise CalculateurError(f"Unité de facturation inconnue : {unite!r}")


def _duree_finition_h_for_op(
    unite: str,
    temps_minutes_unite: float,
    ml: float,
    largeur_bande_m: float,
    etiq_total: int,
) -> float:
    """Temps consommé (en heures) par une op finition interne."""
    if temps_minutes_unite is None or temps_minutes_unite <= 0:
        return 0.0
    if unite == "m2":
        minutes = ml * largeur_bande_m * temps_minutes_unite
    elif unite == "ml":
        minutes = ml * temps_minutes_unite
    elif unite == "unite":
        minutes = etiq_total * temps_minutes_unite
    elif unite == "millier":
        minutes = etiq_total / 1000.0 * temps_minutes_unite
    else:
        raise CalculateurError(f"Unité de facturation inconnue : {unite!r}")
    return minutes / 60.0


def _cout_horaire_structure(
    total_charges_mensuelles: float, heures_productives_mensuelles: float
) -> float:
    if heures_productives_mensuelles <= 0:
        raise CalculateurError(
            "heures_productives_mensuelles doit être > 0 sur entreprise"
        )
    return total_charges_mensuelles / heures_productives_mensuelles


def _p7_frais_gx(heures_dossier: float, cout_horaire_structure_eur: float) -> float:
    return heures_dossier * cout_horaire_structure_eur


# ---------------------------------------------------------------------------
# Orchestration — touche la DB
# ---------------------------------------------------------------------------


class CalculateurDevis:
    """Orchestre les lookups DB + assemble les 7 postes.

    Stateless côté logique : seule la `Session` est conservée. Toute la
    règle métier vit dans les fonctions pures plus haut, ce qui rend
    chaque poste vérifiable indépendamment et à la main.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def compute(self, payload: DevisInput) -> DevisOutput:
        machine = self.session.get(Machine, payload.machine_id)
        if machine is None:
            raise CalculateurError(f"Machine {payload.machine_id} introuvable")

        complexe = self.session.get(Complexe, payload.complexe_id)
        if complexe is None:
            raise CalculateurError(f"Complexe {payload.complexe_id} introuvable")

        entreprise = self.session.scalar(select(Entreprise).limit(1))
        if entreprise is None:
            raise CalculateurError("Aucune entreprise configurée en base")

        operations: list[OperationFinition] = []
        for op_id in payload.operations_finition_ids:
            op = self.session.get(OperationFinition, op_id)
            if op is None:
                raise CalculateurError(f"Opération finition {op_id} introuvable")
            operations.append(op)

        # Lookups paramètres avec valeurs de secours (ne devrait pas arriver
        # avec le seed à jour, mais on reste défensif).
        prix_m2 = float(complexe.prix_m2_eur)
        ratio_encre = float(entreprise.ratio_encre_m2_couleur or 0.003)
        taux_chutes = float(entreprise.taux_chutes_defaut or 0.05)
        heures_productives = float(entreprise.heures_productives_mensuelles or 600)
        cout_horaire_machine = float(machine.cout_horaire_eur or 0)
        duree_calage_h = float(machine.duree_calage_h or 0)
        vitesse_moy = float(machine.vitesse_moyenne_m_h or 6000)

        # Calculs poste par poste
        ml = payload.ml
        largeur = payload.largeur_bande_m
        etiq = payload.etiq_total

        surface = _surface_m2(ml, largeur)
        p1 = _p1_matiere(ml, largeur, prix_m2)
        p2 = _p2_encres(ml, largeur, payload.nb_couleurs, ratio_encre)
        p3 = _p3_outillage(payload.outillage_eur)
        duree_roulage_h = _duree_roulage_h(ml, vitesse_moy)
        p4 = _p4_roulage(duree_calage_h, duree_roulage_h, cout_horaire_machine)
        p5 = _p5_chutes(p1, taux_chutes)

        # P6 : opérations internes + forfaits ST
        p6_internes = 0.0
        duree_finition_h = 0.0
        for op in operations:
            cout_op = _cout_op_selon_unite(
                op.unite_facturation,
                float(op.cout_unitaire_eur or 0),
                ml,
                largeur,
                etiq,
            )
            p6_internes += cout_op
            duree_finition_h += _duree_finition_h_for_op(
                op.unite_facturation,
                float(op.temps_minutes_unite or 0),
                ml,
                largeur,
                etiq,
            )
        p6_st = sum(forfait.montant_eur for forfait in payload.partenaires_st)
        p6 = p6_internes + p6_st

        # P7 frais gx — heures dossier × coût horaire structure
        total_charges = self._total_charges_mensuelles_actives()
        cout_horaire_struct = _cout_horaire_structure(total_charges, heures_productives)
        heures_dossier = duree_calage_h + duree_roulage_h + duree_finition_h
        p7 = _p7_frais_gx(heures_dossier, cout_horaire_struct)

        # Totaux
        cout_revient = p1 + p2 + p3 + p4 + p5 + p6 + p7
        pct_marge = (
            payload.pct_marge_override
            if payload.pct_marge_override is not None
            else float(entreprise.pct_marge_defaut or 0.18)
        )
        prix_vente = cout_revient * (1.0 + pct_marge)

        return DevisOutput(
            p1_matiere_eur=round(p1, 4),
            p2_encres_eur=round(p2, 4),
            p3_outillage_eur=round(p3, 4),
            p4_roulage_eur=round(p4, 4),
            p5_chutes_eur=round(p5, 4),
            p6_finition_eur=round(p6, 4),
            p7_frais_gx_eur=round(p7, 4),
            cout_revient_eur=round(cout_revient, 4),
            pct_marge_appliquee=pct_marge,
            prix_vente_ht_eur=round(prix_vente, 4),
            surface_m2=round(surface, 4),
            duree_calage_h=round(duree_calage_h, 4),
            duree_roulage_h=round(duree_roulage_h, 4),
            duree_finition_h=round(duree_finition_h, 4),
            cout_horaire_structure_eur=round(cout_horaire_struct, 4),
        )

    def _total_charges_mensuelles_actives(self) -> float:
        """Somme des charges en cours (date_fin null ou future)."""
        today = date.today()
        rows = self.session.scalars(
            select(ChargeMensuelle).where(
                or_(
                    ChargeMensuelle.date_fin.is_(None),
                    ChargeMensuelle.date_fin > today,
                )
            )
        ).all()
        return float(sum(float(c.montant_eur) for c in rows))
