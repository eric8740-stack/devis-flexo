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


def _devis_output_mock(prix_vente: float, cout_revient: float) -> DevisOutput:
    """Construit un DevisOutput minimaliste pour tester l'agrégateur sans
    monter une vraie chaîne MoteurDevis + DB. DevisOutput exige exactement
    7 postes (P1..P7), on met le montant total sur P1 et 0 sur les autres."""
    postes = [
        PosteResult(
            poste_numero=i,
            libelle=f"Poste {i}",
            montant_eur=Decimal(str(cout_revient)) if i == 1 else Decimal("0"),
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


def test_aggregateur_somme_correcte():
    """Σ prix_vente_ht_total_eur == somme des prix_vente par lot."""
    mock_moteur = MagicMock()
    mock_moteur.calculer.side_effect = [
        _devis_output_mock(123.45, 100),
        _devis_output_mock(876.55, 700),
    ]
    with patch(
        "app.services.cost_engine_aggregator.MoteurDevis",
        return_value=mock_moteur,
    ):
        result = calculer_devis_multilots(
            db=MagicMock(),
            entreprise_id=1,
            devis_inputs=[MagicMock(), MagicMock()],
        )
    # 123.45 + 876.55 = 1000.00
    assert result.prix_vente_ht_total_eur == Decimal("1000.00")
    assert result.cout_revient_total_eur == Decimal("800.00")


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
