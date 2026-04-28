"""Tests d'intégration de l'orchestrateur MoteurDevis (S3 Lot 3d)."""
from decimal import Decimal

from app.db import SessionLocal
from app.schemas.devis import DevisInput, PartenaireSTForfait
from app.services.cost_engine import MoteurDevis


def _devis_median() -> DevisInput:
    return DevisInput(
        complexe_id=31,
        laize_utile_mm=220,
        ml_total=3000,
        nb_couleurs_par_type={"process_cmj": 4, "pantone": 1},
        machine_id=1,
        forfaits_st=[
            PartenaireSTForfait(partenaire_st_id=1, montant_eur=Decimal("50.00"))
        ],
    )


def test_orchestrateur_returns_7_postes_in_order():
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_median())
    assert len(out.postes) == 7
    assert [p.poste_numero for p in out.postes] == [1, 2, 3, 4, 5, 6, 7]


def test_orchestrateur_total_matches_sum_of_postes():
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_median())
    expected_sum = sum((p.montant_eur for p in out.postes), Decimal(0))
    assert out.cout_revient_eur == expected_sum.quantize(Decimal("0.01"))


def test_orchestrateur_uses_entreprise_marge_default_when_no_override():
    """entreprise.pct_marge_defaut = 0.18 (seed persona PRD)."""
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_median())
    assert out.pct_marge_appliquee == Decimal("0.18")


def test_orchestrateur_uses_override_when_provided():
    devis = _devis_median().model_copy(
        update={"pct_marge_override": Decimal("0.30")}
    )
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(devis)
    assert out.pct_marge_appliquee == Decimal("0.30")
    expected_ht = (out.cout_revient_eur * Decimal("1.30")).quantize(Decimal("0.01"))
    assert out.prix_vente_ht_eur == expected_ht


def test_orchestrateur_computes_prix_au_mille_v1a():
    """V1a (defaults format 60×40, 3p1d, ml=3000) :
    etiq_par_pose = 3000 × 1000 // (40 + 3) = 69767
    nb_etiq_total = 3 × 1 × 69767 = 209301
    prix_au_mille = 1449.09 × 1000 / 209301 = 6.92 €/1000
    """
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_median())
    assert out.prix_au_mille_eur == Decimal("6.92")
