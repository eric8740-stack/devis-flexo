"""Tests agrégateur cost_engine multi-lots (Sprint 13 avenant — PR A commit 4).

Couvre :
  - L'agrégateur appelle le moteur N fois (une fois par lot).
  - La somme prix_vente_ht est correcte.
  - Validation d'entrée : liste vide → ValueError.
  - SACRED preservation : pour 1 lot reproduisant V1a, le coût agrégé
    est strictement égal au coût mono-config V1a (1 449,09 €).
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.devis import DevisOutput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine_aggregator import (
    CoutAgrege,
    CoutLot,
    calculer_devis_multilots,
)


def _devis_output_mock(
    prix_vente: float, cout_revient: float, calage: float = 0.0
) -> DevisOutput:
    """Construit un DevisOutput minimaliste pour tester l'agrégateur sans
    monter une vraie chaîne MoteurDevis + DB. DevisOutput exige exactement
    7 postes (P1..P7) ; on met `calage` sur le **poste 4** (calage) et le
    reste du coût sur P1, pour que Σ postes == cout_revient (bug #5 dédup)."""
    montants = {
        1: Decimal(str(cout_revient)) - Decimal(str(calage)),
        4: Decimal(str(calage)),
    }
    postes = [
        PosteResult(
            poste_numero=i,
            libelle=f"Poste {i}",
            montant_eur=montants.get(i, Decimal("0")),
            details={},
        )
        for i in range(1, 8)
    ]
    return DevisOutput(
        cout_revient_eur=Decimal(str(cout_revient)),
        pct_marge_appliquee=Decimal("0.18"),
        prix_vente_ht_eur=Decimal(str(prix_vente)),
        prix_au_mille_eur=Decimal("0"),
        postes=postes,
        mode="manuel",
    )


def test_aggregateur_appelle_cost_engine_n_fois():
    """3 lots → MoteurDevis.calculer appelé 3 fois, 1 fois par lot."""
    mock_moteur = MagicMock()
    mock_moteur.calculer.side_effect = [
        _devis_output_mock(100, 80),
        _devis_output_mock(200, 160),
        _devis_output_mock(300, 240),
    ]
    with patch(
        "app.services.cost_engine_aggregator.MoteurDevis",
        return_value=mock_moteur,
    ):
        # 3 DevisInput "fake" (les valeurs ne comptent pas, le moteur est mocké).
        inputs = [MagicMock(), MagicMock(), MagicMock()]
        result = calculer_devis_multilots(db=MagicMock(), entreprise_id=1, devis_inputs=inputs)
    assert mock_moteur.calculer.call_count == 3
    assert result.nb_lots == 3
    assert len(result.details_par_lot) == 3


def test_aggregateur_somme_avec_dedup_signatures_distinctes():
    """Bug #5 : Σ avec dédup calage active. Deux lots de montages DISTINCTS
    (signatures différentes) → AUCUNE dédup → somme pleine (les 2 calages
    sont conservés car ce sont 2 vrais montages)."""
    mock_moteur = MagicMock()
    mock_moteur.calculer.side_effect = [
        _devis_output_mock(123.45, 100, calage=50),
        _devis_output_mock(876.55, 700, calage=50),
    ]
    with patch(
        "app.services.cost_engine_aggregator.MoteurDevis",
        return_value=mock_moteur,
    ):
        result = calculer_devis_multilots(
            db=MagicMock(),
            entreprise_id=1,
            devis_inputs=[MagicMock(), MagicMock()],
            montage_signatures=[(1, 1, 1, 3), (2, 1, 1, 3)],  # cylindres ≠
        )
    # Signatures distinctes → pas de dédup → 123.45 + 876.55 = 1000.00.
    assert result.prix_vente_ht_total_eur == Decimal("1000.00")
    assert result.cout_revient_total_eur == Decimal("800.00")


def test_aggregateur_sans_signatures_somme_pure():
    """`montage_signatures=None` → comportement historique : somme pure,
    calage par lot (non-régressif pour les appelants legacy)."""
    mock_moteur = MagicMock()
    mock_moteur.calculer.side_effect = [
        _devis_output_mock(123.45, 100, calage=50),
        _devis_output_mock(876.55, 700, calage=50),
    ]
    with patch(
        "app.services.cost_engine_aggregator.MoteurDevis",
        return_value=mock_moteur,
    ):
        result = calculer_devis_multilots(
            db=MagicMock(), entreprise_id=1,
            devis_inputs=[MagicMock(), MagicMock()],
        )
    assert result.prix_vente_ht_total_eur == Decimal("1000.00")
    assert result.cout_revient_total_eur == Decimal("800.00")


def test_aggregateur_dedup_calage_meme_montage():
    """Bug #5 cœur : 2 lots de MÊME signature (même outil, bobine différente)
    → le calage du 2e lot est DÉDUIT (1 seul calage pour le montage)."""
    mock_moteur = MagicMock()
    # 2 lots identiques : cout_revient=1000 dont calage=225 ; prix=1000×1.18.
    mock_moteur.calculer.side_effect = [
        _devis_output_mock(1180.00, 1000, calage=225),
        _devis_output_mock(1180.00, 1000, calage=225),
    ]
    with patch(
        "app.services.cost_engine_aggregator.MoteurDevis",
        return_value=mock_moteur,
    ):
        result = calculer_devis_multilots(
            db=MagicMock(), entreprise_id=1,
            devis_inputs=[MagicMock(), MagicMock()],
            montage_signatures=[(7, 1, 1, 3), (7, 1, 1, 3)],  # même montage
        )
    # Lot 1 intact (1180 / 1000). Lot 2 dédup : cout 1000-225=775,
    # prix 775×1.18=914.50. Total = 2094.50 / 1775.
    assert result.cout_revient_total_eur == Decimal("1775.00")
    assert result.prix_vente_ht_total_eur == Decimal("2094.50")
    # Trace d'audit : lot 2 marqué dédupliqué (225), lot 1 non (0).
    assert Decimal(result.details_par_lot[0].details["calage_montage_deduplique_eur"]) == 0
    assert Decimal(result.details_par_lot[1].details["calage_montage_deduplique_eur"]) == Decimal("225")
    # Le lot 2 dédupliqué porte bien le coût réduit.
    assert result.details_par_lot[1].cout_revient_eur == Decimal("775")


def test_aggregateur_un_lot_jamais_dedup_sacred():
    """SACRED : un devis à 1 lot n'est JAMAIS touché (1ʳᵉ signature toujours
    conservée) — garantit tripwire P0b 704,07 € inchangé."""
    mock_moteur = MagicMock()
    mock_moteur.calculer.return_value = _devis_output_mock(704.07, 596.67, calage=225)
    with patch(
        "app.services.cost_engine_aggregator.MoteurDevis",
        return_value=mock_moteur,
    ):
        result = calculer_devis_multilots(
            db=MagicMock(), entreprise_id=1,
            devis_inputs=[MagicMock()],
            montage_signatures=[(7, 1, 1, 3)],
        )
    assert result.prix_vente_ht_total_eur == Decimal("704.07")  # calage conservé
    assert Decimal(result.details_par_lot[0].details["calage_montage_deduplique_eur"]) == 0


def test_aggregateur_raise_si_lots_vides():
    """Pas de lots → ValueError (un devis a au moins 1 lot)."""
    with pytest.raises(ValueError, match="ne peut pas être vide"):
        calculer_devis_multilots(db=MagicMock(), entreprise_id=1, devis_inputs=[])


def test_aggregateur_un_lot_preserve_resultat_moteur_exact():
    """SACRED : pour 1 seul lot, le coût agrégé est exactement le coût retourné
    par le moteur (pas de transformation, pas d'arrondi destructif).
    1449.09 € reproduit exactement (cas V1a)."""
    mock_moteur = MagicMock()
    mock_moteur.calculer.return_value = _devis_output_mock(1449.09, 1228.04)
    with patch(
        "app.services.cost_engine_aggregator.MoteurDevis",
        return_value=mock_moteur,
    ):
        result = calculer_devis_multilots(
            db=MagicMock(),
            entreprise_id=1,
            devis_inputs=[MagicMock()],
        )
    assert result.prix_vente_ht_total_eur == Decimal("1449.09")
    assert result.cout_revient_total_eur == Decimal("1228.04")
    assert result.nb_lots == 1
    assert result.details_par_lot[0].prix_vente_ht_eur == Decimal("1449.09")
    # Sanity sur les dataclasses exposées
    assert isinstance(result, CoutAgrege)
    assert isinstance(result.details_par_lot[0], CoutLot)
