"""Poste 3 — Outillage / Clichés (refonte Sprint 5 Lot 5c en 2 sous-postes).

Sous-postes :

  3a Clichés      : nb_couleurs_total × tarif("cliche_prix_couleur")
                    Inchangé depuis Sprint 3 Lot 3d.

  3b Outil découpe :
    SI devis.outil_decoupe_existant = True :
        cout = 0 €  (outil amorti, pas de re-facturation)
    SINON (nouvel outil) :
        cout_base = tarif("outil_base_eur") + (nb_traces_complexite × tarif("outil_par_trace_eur"))
        SI devis.forme_speciale :
            cout = cout_base × tarif("surcout_forme_speciale_pct")
        SINON :
            cout = cout_base

    Validation arithmétique (avec valeurs seed défaut S9 v2 200/50/1.40) :
      Existant                                      :   0 €
      Nouveau · 1 tracé   · simple                  : 250 €
      Nouveau · 4 tracés  · simple                  : 400 €
      Nouveau · 4 tracés  · forme spéciale (×1.40)  : 560 €

Total P3 = 3a + 3b. Le `outil_decoupe_id` n'impacte pas le calcul (cas
existant = 0 € quel que soit l'outil identifié), il sert uniquement à
tracer dans `details` pour audit en démo.

Sprint 9 v2 Lot 9b : les 3 constantes outillage (200/50/1.40) sont
migrées vers la table `tarif_poste` (Dette 1 résorbée). Valeurs seedées
identiques aux constantes en dur → V1a/V1b/V1b forme spé EXACT préservés.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.tarif_poste import get_by_cle
from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine.errors import CostEngineError

logger = logging.getLogger(__name__)


def _get_tarif_value(db: Session, cle: str) -> Decimal:
    """Charge la valeur d'un paramètre tarifaire ou lève une erreur explicite.

    Centralise la lecture pour Sprint 9 v2 — toutes les valeurs paramétrables
    du moteur transitent par `tarif_poste`.
    """
    tarif = get_by_cle(db, cle)
    if tarif is None:
        raise CostEngineError(
            f"Tarif {cle!r} introuvable — seed tarif_poste manquant"
        )
    return Decimal(tarif.valeur_defaut)


class CalculateurPoste3ClichesOutillage:
    POSTE_NUMERO = 3
    LIBELLE = "Outillage / Clichés"

    def __init__(self, db: Session) -> None:
        self.db = db

    def calculer(self, devis: DevisInput) -> PosteResult:
        # 3a Clichés (inchangé Sprint 3)
        prix_couleur = _get_tarif_value(self.db, "cliche_prix_couleur")
        nb_couleurs_total = sum(devis.nb_couleurs_par_type.values())
        cout_3a = (Decimal(nb_couleurs_total) * prix_couleur).quantize(Decimal("0.01"))

        # 3b Outil découpe — Sprint 9 v2 : lecture des 3 valeurs depuis tarif_poste
        if devis.outil_decoupe_existant:
            cout_3b = Decimal("0.00")
            mode_outil = "existant"
            surcout_pct = 0
        else:
            outil_base = _get_tarif_value(self.db, "outil_base_eur")
            outil_par_trace = _get_tarif_value(self.db, "outil_par_trace_eur")
            cout_base = outil_base + (
                Decimal(devis.nb_traces_complexite) * outil_par_trace
            )
            if devis.forme_speciale:
                surcout_factor = _get_tarif_value(
                    self.db, "surcout_forme_speciale_pct"
                )
                cout_3b = (cout_base * surcout_factor).quantize(Decimal("0.01"))
                # Le pct affiché = (factor - 1) × 100 (ex. 1.40 → 40 %)
                surcout_pct = int(((surcout_factor - Decimal("1")) * Decimal("100")).quantize(Decimal("1")))
            else:
                cout_3b = cout_base.quantize(Decimal("0.01"))
                surcout_pct = 0
            mode_outil = "nouveau"

        cout_total = (cout_3a + cout_3b).quantize(Decimal("0.01"))

        logger.info(
            "P3 Outillage/Clichés: 3a=%s + 3b=%s = %s € (mode_outil=%s)",
            cout_3a, cout_3b, cout_total, mode_outil,
        )
        return PosteResult(
            poste_numero=self.POSTE_NUMERO,
            libelle=self.LIBELLE,
            montant_eur=cout_total,
            details={
                # 3a
                "nb_couleurs_total": nb_couleurs_total,
                "prix_par_couleur_eur": float(prix_couleur),
                "cout_3a_cliches_eur": float(cout_3a),
                # 3b
                "mode_outil": mode_outil,
                "cout_3b_outil_eur": float(cout_3b),
                "outil_decoupe_id": devis.outil_decoupe_id,
                "nb_traces_complexite": devis.nb_traces_complexite,
                "forme_speciale": "true" if devis.forme_speciale else "false",
                "surcout_forme_speciale_pct": surcout_pct,
            },
        )
