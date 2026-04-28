"""Tests unitaires des 7 calculateurs (S3 Lot 3d).

Chaque calculateur est testé sur la DB seedée (fixture autouse run_seed)
+ son cas d'erreur principal. Tests d'intégration de l'orchestrateur
dans test_cost_engine_orchestrator.py.
"""
from decimal import Decimal

import pytest

from app.db import SessionLocal
from app.schemas.devis import DevisInput, PartenaireSTForfait
from app.services.cost_engine import CostEngineError
from app.services.cost_engine.poste_1_matiere import CalculateurPoste1Matiere
from app.services.cost_engine.poste_2_encres import CalculateurPoste2Encres
from app.services.cost_engine.poste_3_cliches import (
    CalculateurPoste3ClichesOutillage,
)
from app.services.cost_engine.poste_4_calage import CalculateurPoste4Calage
from app.services.cost_engine.poste_5_roulage import CalculateurPoste5Roulage
from app.services.cost_engine.poste_6_finitions import CalculateurPoste6Finitions
from app.services.cost_engine.poste_7_mo import CalculateurPoste7MO


def _devis_median() -> DevisInput:
    """Cas-test médian — utilisé par tous les tests calculateurs.

    Voir test_cost_engine_benchmark.py pour le détail des choix
    (complexe id=31 VELIN_STANDARD_80 = ~25 % production réelle,
    machine id=1 Mark Andy P5 = la plus utilisée).
    """
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


# ---------------------------------------------------------------------------
# P1 Matière
# ---------------------------------------------------------------------------


def test_p1_matiere_derive_prix_kg_from_complexe():
    """VELIN_STANDARD_80 : prix_m2=0.35, grammage=80 → prix_kg=4.375 €/kg.
    laize_machine=230 mm × 3000 ml = 690 m² × 80g/1000 = 55.2 kg × 4.375 = 241.50 €.
    """
    with SessionLocal() as db:
        result = CalculateurPoste1Matiere(db).calculer(_devis_median())
    assert result.poste_numero == 1
    assert result.montant_eur == Decimal("241.50")
    assert result.details["prix_kg_source"] == "complexe_derived"
    assert result.details["laize_machine_mm"] == 230
    assert result.details["grammage_g_m2"] == 80


def test_p1_matiere_raises_when_complexe_has_no_grammage():
    """Complexe id=1 (BOPP_BLANC_50) a grammage_g_m2 NULL — erreur explicite."""
    devis = _devis_median().model_copy(update={"complexe_id": 1})
    with SessionLocal() as db:
        with pytest.raises(CostEngineError, match="grammage_g_m2"):
            CalculateurPoste1Matiere(db).calculer(devis)


# ---------------------------------------------------------------------------
# P2 Encres
# ---------------------------------------------------------------------------


def test_p2_encres_sum_per_type():
    """4 process_cmj + 1 pantone sur 660 m² imprimés.
    process_cmj : 660 × 4 × 2/1000 × 15.75 = 83.16 €
    pantone : 660 × 1 × 2/1000 × 21.50 = 28.38 €
    Total : 111.54 €
    """
    with SessionLocal() as db:
        result = CalculateurPoste2Encres(db).calculer(_devis_median())
    assert result.montant_eur == Decimal("111.54")
    assert result.details["process_cmj_nb_couleurs"] == 4
    assert result.details["pantone_nb_couleurs"] == 1


def test_p2_encres_raises_on_unknown_type_encre():
    devis = _devis_median().model_copy(
        update={"nb_couleurs_par_type": {"process_xyz_inexistant": 2}}
    )
    with SessionLocal() as db:
        with pytest.raises(CostEngineError, match="type_encre"):
            CalculateurPoste2Encres(db).calculer(devis)


# ---------------------------------------------------------------------------
# P3 Clichés
# ---------------------------------------------------------------------------


def test_p3_v1a_existing_tool_5_couleurs():
    """V1a : 5 couleurs × 45 = 225 € (3a) + outil existant 0 € (3b) = 225 €."""
    with SessionLocal() as db:
        result = CalculateurPoste3ClichesOutillage(db).calculer(_devis_median())
    assert result.montant_eur == Decimal("225.00")
    assert result.details["nb_couleurs_total"] == 5
    assert result.details["mode_outil"] == "existant"
    assert result.details["cout_3a_cliches_eur"] == 225.0
    assert result.details["cout_3b_outil_eur"] == 0.0


def test_p3_zero_couleurs_outil_existant_returns_zero():
    devis = _devis_median().model_copy(update={"nb_couleurs_par_type": {}})
    with SessionLocal() as db:
        result = CalculateurPoste3ClichesOutillage(db).calculer(devis)
    assert result.montant_eur == Decimal("0.00")


def test_p3_outil_nouveau_4_traces_simple():
    """Nouvel outil, 4 tracés simples : 200 + 4×50 = 400 €. Total P3 = 225 + 400 = 625."""
    devis = _devis_median().model_copy(
        update={"outil_decoupe_existant": False, "nb_traces_complexite": 4}
    )
    with SessionLocal() as db:
        result = CalculateurPoste3ClichesOutillage(db).calculer(devis)
    assert result.montant_eur == Decimal("625.00")
    assert result.details["mode_outil"] == "nouveau"
    assert result.details["cout_3b_outil_eur"] == 400.0
    assert result.details["surcout_forme_speciale_pct"] == 0


def test_p3_outil_nouveau_4_traces_forme_speciale():
    """Nouvel outil, 4 tracés + forme spé : (200 + 4×50) × 1.40 = 560 €. Total P3 = 785."""
    devis = _devis_median().model_copy(
        update={
            "outil_decoupe_existant": False,
            "nb_traces_complexite": 4,
            "forme_speciale": True,
        }
    )
    with SessionLocal() as db:
        result = CalculateurPoste3ClichesOutillage(db).calculer(devis)
    assert result.montant_eur == Decimal("785.00")
    assert result.details["cout_3b_outil_eur"] == 560.0
    assert result.details["surcout_forme_speciale_pct"] == 40
    assert result.details["forme_speciale"] == "true"


# ---------------------------------------------------------------------------
# P4 Calage (forfait)
# ---------------------------------------------------------------------------


def test_p4_calage_forfait():
    """Forfait fixe 225 €/devis, indépendant du devis."""
    with SessionLocal() as db:
        result = CalculateurPoste4Calage(db).calculer(_devis_median())
    assert result.montant_eur == Decimal("225.00")
    assert result.details["mode"] == "forfait"
    assert result.details["operations_count"] == 0


# ---------------------------------------------------------------------------
# P5 Roulage
# ---------------------------------------------------------------------------


def test_p5_roulage_mark_andy_3000ml():
    """3000 ml ÷ 6000 m/h (Mark Andy) = 0.5 h × 375 €/h = 187.50 €."""
    with SessionLocal() as db:
        result = CalculateurPoste5Roulage(db).calculer(_devis_median())
    assert result.montant_eur == Decimal("187.50")
    assert result.details["machine_nom"] == "Mark Andy P5"


def test_p5_roulage_raises_on_unknown_machine():
    devis = _devis_median().model_copy(update={"machine_id": 9999})
    with SessionLocal() as db:
        with pytest.raises(CostEngineError, match="Machine"):
            CalculateurPoste5Roulage(db).calculer(devis)


# ---------------------------------------------------------------------------
# P6 Finitions
# ---------------------------------------------------------------------------


def test_p6_finitions_base_plus_st():
    """surface_utile=660m² × 0.125 €/m² = 82.50 € base, + 50 € ST = 132.50 €."""
    with SessionLocal() as db:
        result = CalculateurPoste6Finitions(db).calculer(_devis_median())
    assert result.montant_eur == Decimal("132.50")
    assert result.details["nb_forfaits_st"] == 1


def test_p6_finitions_without_st_only_base():
    devis = _devis_median().model_copy(update={"forfaits_st": []})
    with SessionLocal() as db:
        result = CalculateurPoste6Finitions(db).calculer(devis)
    assert result.montant_eur == Decimal("82.50")
    assert result.details["nb_forfaits_st"] == 0


# ---------------------------------------------------------------------------
# P7 MO
# ---------------------------------------------------------------------------


def test_p7_mo_derived_from_machine():
    """heures_calage(1.0) + heures_prod(3000/6000=0.5) = 1.5h × 70 €/h = 105 €."""
    with SessionLocal() as db:
        result = CalculateurPoste7MO(db).calculer(_devis_median())
    assert result.montant_eur == Decimal("105.00")
    assert result.details["heures_source"] == "derived_machine"
    assert result.details["heures_total"] == 1.5


def test_p7_mo_uses_override_when_provided():
    """Override 2.5 h × 70 €/h = 175 €."""
    devis = _devis_median().model_copy(
        update={"heures_dossier_override": Decimal("2.5")}
    )
    with SessionLocal() as db:
        result = CalculateurPoste7MO(db).calculer(devis)
    assert result.montant_eur == Decimal("175.00")
    assert result.details["heures_source"] == "override"
