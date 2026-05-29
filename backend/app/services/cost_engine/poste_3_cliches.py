"""Poste 3 — Outillage / Clichés (refonte Sprint 5 Lot 5c en 2 sous-postes).

Sous-postes :

  3a Clichés      : nb_couleurs_total × ConfigCouts.cliche_prix_couleur_eur

  3b Outil découpe :
    SI devis.outil_decoupe_existant = True :
        cout = 0 €  (outil amorti, pas de re-facturation)
    SINON (nouvel outil) :
        cout_base = ConfigCouts.outil_base_eur
                  + (nb_traces_complexite × ConfigCouts.outil_par_trace_eur)
        SI devis.forme_speciale :
            cout = cout_base × ConfigCouts.surcout_forme_speciale_facteur
        SINON :
            cout = cout_base

    Validation arithmétique (avec valeurs ICE 200/50/1.40) :
      Existant                                      :   0 €
      Nouveau · 1 tracé   · simple                  : 250 €
      Nouveau · 4 tracés  · simple                  : 400 €
      Nouveau · 4 tracés  · forme spéciale (×1.40)  : 560 €

Total P3 = 3a + 3b. Le `outil_decoupe_id` n'impacte pas le calcul (cas
existant = 0 € quel que soit l'outil identifié), il sert uniquement à
tracer dans `details` pour audit en démo.

Phase 2 Lot 4a (2026-05-29) : les 4 tarifs P3 passent de `TarifPoste`
(legacy, déprécié) à `ConfigCouts` (Stratégique, scopée tenant). Le facteur
forme spéciale a été renommé `_facteur` (et non plus `_pct`) — la valeur
SQL = multiplicateur direct (1.40 = ×1.40). Le pct affiché pour audit reste
calculé à la volée `(factor - 1) × 100`.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine._config_reader import get_config_couts_or_raise

logger = logging.getLogger(__name__)


class CalculateurPoste3ClichesOutillage:
    POSTE_NUMERO = 3
    LIBELLE = "Outillage / Clichés"

    def __init__(self, db: Session, entreprise_id: int) -> None:
        """Sprint 12-C : `entreprise_id` requis pour scoper ConfigCouts."""
        self.db = db
        self.entreprise_id = entreprise_id

    def calculer(self, devis: DevisInput) -> PosteResult:
        config = get_config_couts_or_raise(self.db, self.entreprise_id)

        # 3a Clichés
        prix_couleur = Decimal(str(config.cliche_prix_couleur_eur))
        nb_couleurs_total = sum(devis.nb_couleurs_par_type.values())
        cout_3a = (Decimal(nb_couleurs_total) * prix_couleur).quantize(Decimal("0.01"))

        # 3b Outil découpe
        if devis.outil_decoupe_existant:
            cout_3b = Decimal("0.00")
            mode_outil = "existant"
            surcout_pct = 0
        else:
            outil_base = Decimal(str(config.outil_base_eur))
            outil_par_trace = Decimal(str(config.outil_par_trace_eur))
            cout_base = outil_base + (
                Decimal(devis.nb_traces_complexite) * outil_par_trace
            )
            if devis.forme_speciale:
                surcout_factor = Decimal(str(config.surcout_forme_speciale_facteur))
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
