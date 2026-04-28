"""Poste 3 — Outillage / Clichés (refonte Sprint 5 Lot 5c en 2 sous-postes).

Sous-postes :

  3a Clichés      : nb_couleurs_total × tarif("cliche_prix_couleur")
                    Inchangé depuis Sprint 3 Lot 3d.

  3b Outil découpe :
    SI devis.outil_decoupe_existant = True :
        cout = 0 €  (outil amorti, pas de re-facturation)
    SINON (nouvel outil) :
        cout_base = 200 + (nb_traces_complexite × 50)
        SI devis.forme_speciale :
            cout = cout_base × 1.40    (surcoût plaque +40 %)
        SINON :
            cout = cout_base

    Validation arithmétique :
      Existant                                      :   0 €
      Nouveau · 1 tracé   · simple                  : 250 €
      Nouveau · 4 tracés  · simple                  : 400 €
      Nouveau · 4 tracés  · forme spéciale (×1.40)  : 560 €

Total P3 = 3a + 3b. Le `outil_decoupe_id` n'impacte pas le calcul (cas
existant = 0 € quel que soit l'outil identifié), il sert uniquement à
tracer dans `details` pour audit en démo.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.tarif_poste import get_by_cle
from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine.errors import CostEngineError

logger = logging.getLogger(__name__)

COUT_OUTIL_BASE_FIXE = Decimal("200")
COUT_OUTIL_PAR_TRACE = Decimal("50")
SURCOUT_FORME_SPECIALE = Decimal("1.40")


class CalculateurPoste3ClichesOutillage:
    POSTE_NUMERO = 3
    LIBELLE = "Outillage / Clichés"

    def __init__(self, db: Session) -> None:
        self.db = db

    def calculer(self, devis: DevisInput) -> PosteResult:
        # 3a Clichés (inchangé Sprint 3)
        tarif = get_by_cle(self.db, "cliche_prix_couleur")
        if tarif is None:
            raise CostEngineError(
                "Tarif 'cliche_prix_couleur' introuvable — seed tarif_poste manquant"
            )
        prix_couleur = Decimal(tarif.valeur_defaut)
        nb_couleurs_total = sum(devis.nb_couleurs_par_type.values())
        cout_3a = (Decimal(nb_couleurs_total) * prix_couleur).quantize(Decimal("0.01"))

        # 3b Outil découpe
        if devis.outil_decoupe_existant:
            cout_3b = Decimal("0.00")
            mode_outil = "existant"
            surcout_pct = 0
        else:
            cout_base = COUT_OUTIL_BASE_FIXE + (
                Decimal(devis.nb_traces_complexite) * COUT_OUTIL_PAR_TRACE
            )
            if devis.forme_speciale:
                cout_3b = (cout_base * SURCOUT_FORME_SPECIALE).quantize(Decimal("0.01"))
                surcout_pct = 40
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


# Alias rétrocompat pour orchestrator (sera mis à jour dans cette même PR)
CalculateurPoste3Cliches = CalculateurPoste3ClichesOutillage
