"""Agrégateur cost_engine multi-lots (Sprint 13 avenant).

Permet de calculer le coût total d'un devis fractionné en N lots de
production (matières et configurations différentes par lot).

SACRED INVARIANT — logique cost_engine INCHANGÉE
------------------------------------------------
Cet agrégateur appelle `MoteurDevis.calculer()` N fois (une fois par
lot) avec des `DevisInput` indépendants. Aucune modification du moteur
de calcul. Les valeurs EXACT V1a (1 449,09 €), V1b (1 921,09 €),
V1b silhouette (2 109,89 €), V7a (6,85 €/1000), V8a-e sont préservées
**par lot** : si un lot reproduit un cas figé, son coût est strictement
identique à un calcul mono-config.

Le moteur reste stateless une fois instancié — on instancie `MoteurDevis`
une seule fois (overhead constant) puis on l'appelle N fois.

API
---
`calculer_devis_multilots(db, entreprise_id, devis_inputs)` →
`CoutAgrege(cout_total_ht_eur, details_par_lot=list[CoutLot])`.

Chaque `CoutLot` porte le détail brut du moteur (`PosteResult` + métadonnées)
pour audit / debug, le coût HT du lot et son indice (0..N-1).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.devis import DevisInput, DevisOutput, DevisOutputMatching
from app.services.cost_engine.orchestrator import MoteurDevis


@dataclass(frozen=True)
class CoutLot:
    """Résultat de calcul d'un lot individuel.

    `ordre` : position du lot dans le devis (0..N-1, indice de la liste
              d'inputs passée à l'agrégateur).
    `prix_vente_ht_eur` : prix de vente HT calculé par le moteur pour ce lot.
    `cout_revient_eur`  : coût de revient HT calculé par le moteur.
    `details` : dump brut du DevisOutput (postes, métadonnées) pour audit.
    """

    ordre: int
    prix_vente_ht_eur: Decimal
    cout_revient_eur: Decimal
    details: dict[str, Any]


@dataclass(frozen=True)
class CoutAgrege:
    """Résultat agrégé d'un devis multi-lots.

    `prix_vente_ht_total_eur` = Σ prix_vente_ht_eur par lot. Pas de remise
    ni de bonus quantité agrégés à ce niveau : le moteur applique déjà le
    barème dégressif PAR lot (sur sa propre quantité). Une politique
    commerciale "prix dégressif sur quantité totale" est hors-scope ici.
    """

    prix_vente_ht_total_eur: Decimal
    cout_revient_total_eur: Decimal
    nb_lots: int
    details_par_lot: list[CoutLot]


def calculer_devis_multilots(
    db: Session,
    entreprise_id: int,
    devis_inputs: list[DevisInput],
) -> CoutAgrege:
    """Calcule un devis multi-lots en appelant le moteur N fois.

    Args:
      db: SQLAlchemy session (passée au moteur pour lecture tarif_poste,
          tarif_encre, etc.).
      entreprise_id: scope multi-tenant strict (cf MoteurDevis.__init__).
      devis_inputs: 1..N inputs moteur indépendants, chacun représentant
          un lot avec ses propres matière/cylindre/quantité/poses.

    Returns:
      CoutAgrege avec total + détail par lot.

    Raises:
      ValueError si devis_inputs est vide (un devis a au moins 1 lot).

    Cost engine n'est PAS modifié : chaque DevisInput est traité de
    manière indépendante exactement comme un devis mono-config. Les
    sacrés EXACT sont donc préservés par lot.
    """
    if not devis_inputs:
        raise ValueError(
            "calculer_devis_multilots : la liste de lots ne peut pas être vide."
        )

    moteur = MoteurDevis(db, entreprise_id)
    details_par_lot: list[CoutLot] = []
    prix_vente_total = Decimal("0")
    cout_revient_total = Decimal("0")

    for ordre, devis_input in enumerate(devis_inputs):
        result = moteur.calculer(devis_input)
        prix_vente_lot, cout_revient_lot = _extraire_couts(result)
        prix_vente_total += prix_vente_lot
        cout_revient_total += cout_revient_lot
        details_par_lot.append(
            CoutLot(
                ordre=ordre,
                prix_vente_ht_eur=prix_vente_lot,
                cout_revient_eur=cout_revient_lot,
                details=result.model_dump(mode="json"),
            )
        )

    return CoutAgrege(
        prix_vente_ht_total_eur=prix_vente_total.quantize(Decimal("0.01")),
        cout_revient_total_eur=cout_revient_total.quantize(Decimal("0.01")),
        nb_lots=len(devis_inputs),
        details_par_lot=details_par_lot,
    )


def _extraire_couts(
    result: DevisOutput | DevisOutputMatching,
) -> tuple[Decimal, Decimal]:
    """Extrait (prix_vente_ht, cout_revient) du résultat moteur.

    En mode matching, le résultat est multi-candidats : on prend le 1er
    cylindre proposé (équivalent du choix par défaut UI). En mode manuel,
    le résultat est mono : on lit directement.
    """
    if isinstance(result, DevisOutputMatching):
        # Mode matching : 1..3 candidats, on prend le 1er (meilleur match).
        if not result.candidats:
            raise ValueError(
                "Mode matching : moteur n'a produit aucun candidat cylindre."
            )
        c = result.candidats[0]
        return c.prix_vente_ht_eur, c.cout_revient_eur
    return result.prix_vente_ht_eur, result.cout_revient_eur
