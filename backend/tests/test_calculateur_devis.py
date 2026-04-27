"""Tests du moteur de calcul de devis (Sprint 3 Lot 2).

Stratégie : valeurs simples, vérifiables à la main. Le but n'est PAS
de matcher une réalité ICE (Lot 4 — calibration ICE reportée), mais de
prouver que le moteur calcule juste sa propre logique.

- Tests unitaires : méthodes pures, sans DB, valeurs choisies pour
  donner des arrondis ronds (ml=1000, largeur=0.330, etc.)
- Tests intégration : 2 cas inventés sur la DB seedée. Vérifient la
  cohérence interne (somme postes = coût revient, prix vente = coût
  × (1+marge), durées dérivées correctes).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.schemas.devis import DevisInput, PartenaireSTForfait
from app.services.calculateur_devis import (
    CalculateurDevis,
    CalculateurError,
    _cout_horaire_structure,
    _cout_op_selon_unite,
    _duree_finition_h_for_op,
    _duree_roulage_h,
    _p1_matiere,
    _p2_encres,
    _p3_outillage,
    _p4_roulage,
    _p5_chutes,
    _p7_frais_gx,
    _surface_m2,
)

client = TestClient(app)  # nécessaire pour activer la fixture seed_db_before_each_test


# ---------------------------------------------------------------------------
# Tests unitaires — fonctions pures, pas de DB
# ---------------------------------------------------------------------------


def test_p1_matiere_simple():
    # 1000 ml × 0.330 m × 1.20 €/m² = 396.00 €
    assert _p1_matiere(ml=1000, largeur_bande_m=0.330, prix_m2_eur=1.20) == pytest.approx(396.0)


def test_p2_encres_simple():
    # 1000 × 0.330 × 4 couleurs × 0.003 €/m²/couleur = 3.96 €
    assert _p2_encres(ml=1000, largeur_bande_m=0.330, nb_couleurs=4, ratio_encre_m2_couleur=0.003) == pytest.approx(3.96)


def test_p3_outillage_passthrough():
    assert _p3_outillage(250.0) == 250.0
    assert _p3_outillage(0.0) == 0.0


def test_duree_roulage_h_simple():
    # 6000 ml à 6000 m/h = 1.00 h
    assert _duree_roulage_h(ml=6000, vitesse_moyenne_m_h=6000) == pytest.approx(1.0)


def test_p4_roulage_simple():
    # (calage 0.50 + roulage 1.00) × 60 €/h = 90.00 €
    assert _p4_roulage(duree_calage_h=0.50, duree_roulage_h=1.00, cout_horaire_machine=60.0) == pytest.approx(90.0)


def test_p5_chutes_simple():
    # P1 = 400 €, taux 5 % → 20.00 €
    assert _p5_chutes(p1_matiere_eur=400.0, taux_chutes=0.05) == pytest.approx(20.0)


def test_p6_op_m2():
    # 1000 ml × 0.330 m × 0.10 €/m² = 33.00 €
    assert _cout_op_selon_unite("m2", 0.10, ml=1000, largeur_bande_m=0.330, etiq_total=0) == pytest.approx(33.0)


def test_p6_op_ml():
    # 2000 ml × 0.10 €/ml = 200.00 €
    assert _cout_op_selon_unite("ml", 0.10, ml=2000, largeur_bande_m=0.330, etiq_total=0) == pytest.approx(200.0)


def test_p6_op_unite():
    # 5000 étiq × 0.05 €/unité = 250.00 €
    assert _cout_op_selon_unite("unite", 0.05, ml=0, largeur_bande_m=0, etiq_total=5000) == pytest.approx(250.0)


def test_p6_op_millier():
    # 10000 étiq / 1000 × 2.00 €/millier = 20.00 €
    assert _cout_op_selon_unite("millier", 2.00, ml=0, largeur_bande_m=0, etiq_total=10000) == pytest.approx(20.0)


def test_p6_op_unite_inconnue_raises():
    with pytest.raises(CalculateurError):
        _cout_op_selon_unite("kg", 1.0, ml=0, largeur_bande_m=0, etiq_total=0)


def test_duree_finition_h_for_op_m2():
    # 1000 ml × 0.330 m × 0.06 min/m² = 19.8 min = 0.33 h
    assert _duree_finition_h_for_op("m2", 0.06, ml=1000, largeur_bande_m=0.330, etiq_total=0) == pytest.approx(0.33)


def test_duree_finition_h_zero_si_temps_null():
    assert _duree_finition_h_for_op("m2", 0.0, ml=1000, largeur_bande_m=0.330, etiq_total=0) == 0.0


def test_cout_horaire_structure():
    # 12 650 €/mois / 600 h = 21.0833... €/h
    assert _cout_horaire_structure(12650.0, 600.0) == pytest.approx(21.083333, rel=1e-5)


def test_cout_horaire_structure_zero_heures_raises():
    with pytest.raises(CalculateurError):
        _cout_horaire_structure(12650.0, 0.0)


def test_p7_frais_gx_simple():
    # 2.5 h × 20 €/h = 50.00 €
    assert _p7_frais_gx(heures_dossier=2.5, cout_horaire_structure_eur=20.0) == pytest.approx(50.0)


def test_surface_m2_simple():
    assert _surface_m2(ml=1000, largeur_bande_m=0.330) == pytest.approx(330.0)


# ---------------------------------------------------------------------------
# Tests intégration — touchent la DB seedée par conftest
# ---------------------------------------------------------------------------


def test_compute_devis_simple_coherence_interne():
    """Devis minimal (sans finition, sans ST) — vérifie la cohérence
    interne : somme des postes = coût de revient, prix vente = coût
    × (1 + marge), durée roulage = ml / vitesse moyenne machine."""
    payload = DevisInput(
        ml=4000,
        largeur_bande_m=0.330,
        nb_couleurs=2,
        etiq_total=5000,
        machine_id=1,  # Mark Andy P5, vitesse_moyenne 6000 m/h, calage 0.50 h
        complexe_id=1,
        outillage_eur=250.0,
    )
    with SessionLocal() as session:
        out = CalculateurDevis(session).compute(payload)

    # Surface = ml × largeur
    assert out.surface_m2 == pytest.approx(4000 * 0.330)

    # Durée roulage = 4000 / 6000 = 0.6667 h
    assert out.duree_roulage_h == pytest.approx(4000 / 6000, rel=1e-3)
    assert out.duree_calage_h == pytest.approx(0.50)
    # Pas d'opération finition → durée finition = 0
    assert out.duree_finition_h == 0.0

    # Coût de revient = somme des 7 postes
    somme = (
        out.p1_matiere_eur
        + out.p2_encres_eur
        + out.p3_outillage_eur
        + out.p4_roulage_eur
        + out.p5_chutes_eur
        + out.p6_finition_eur
        + out.p7_frais_gx_eur
    )
    assert somme == pytest.approx(out.cout_revient_eur, rel=1e-4)

    # Prix de vente = coût × (1 + marge), marge persona = 18 %
    assert out.pct_marge_appliquee == pytest.approx(0.18)
    assert out.prix_vente_ht_eur == pytest.approx(
        out.cout_revient_eur * 1.18, rel=1e-4
    )

    # P3 = outillage saisi
    assert out.p3_outillage_eur == 250.0

    # P5 chutes = P1 × 5 %
    assert out.p5_chutes_eur == pytest.approx(out.p1_matiere_eur * 0.05, rel=1e-5)


def test_compute_devis_avec_finition_et_st_augmente_p6():
    """Ajouter une opération finition + un partenaire ST doit augmenter P6
    et le coût de revient. La marge override doit prendre le pas sur le
    pct_marge_defaut entreprise."""
    base = DevisInput(
        ml=4000,
        largeur_bande_m=0.330,
        nb_couleurs=4,
        etiq_total=20000,
        machine_id=1,
        complexe_id=1,
        outillage_eur=800.0,
    )
    enrichi = DevisInput(
        ml=4000,
        largeur_bande_m=0.330,
        nb_couleurs=4,
        etiq_total=20000,
        machine_id=1,
        complexe_id=1,
        outillage_eur=800.0,
        operations_finition_ids=[1],  # 1ère opération finition seedée
        partenaires_st=[
            PartenaireSTForfait(partenaire_st_id=1, montant_eur=200.0)
        ],
        pct_marge_override=0.30,  # preset Premium
    )
    with SessionLocal() as session:
        calc = CalculateurDevis(session)
        out_base = calc.compute(base)
        out_enrichi = calc.compute(enrichi)

    # P6 enrichi > P6 base (op interne + forfait ST 200 €)
    assert out_enrichi.p6_finition_eur > out_base.p6_finition_eur
    assert out_enrichi.p6_finition_eur >= out_base.p6_finition_eur + 200.0

    # Coût de revient enrichi > coût de revient base
    assert out_enrichi.cout_revient_eur > out_base.cout_revient_eur

    # Marge override Premium 30 %
    assert out_enrichi.pct_marge_appliquee == pytest.approx(0.30)
    assert out_enrichi.prix_vente_ht_eur == pytest.approx(
        out_enrichi.cout_revient_eur * 1.30, rel=1e-4
    )


def test_compute_devis_machine_inexistante_raises():
    payload = DevisInput(
        ml=1000,
        largeur_bande_m=0.330,
        nb_couleurs=2,
        etiq_total=1000,
        machine_id=9999,
        complexe_id=1,
    )
    with SessionLocal() as session:
        with pytest.raises(CalculateurError, match="Machine 9999"):
            CalculateurDevis(session).compute(payload)


def test_compute_devis_complexe_inexistant_raises():
    payload = DevisInput(
        ml=1000,
        largeur_bande_m=0.330,
        nb_couleurs=2,
        etiq_total=1000,
        machine_id=1,
        complexe_id=9999,
    )
    with SessionLocal() as session:
        with pytest.raises(CalculateurError, match="Complexe 9999"):
            CalculateurDevis(session).compute(payload)
