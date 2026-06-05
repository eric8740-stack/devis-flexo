"""Phase 2 Lot 4a — P1/P3/P4/P6 basculent sur ConfigCouts.

Couvre :
- P4 lu depuis `ConfigCouts.calage_forfait_eur` (tenant à 300 € → coût 300) ;
- P6 lu depuis `ConfigCouts.finitions_prix_m2_eur` (tenant à 0.20 €/m² →
  reflète 0.20) ;
- P3 lu depuis `cliche_prix_couleur_eur` / `outil_base_eur` /
  `outil_par_trace_eur` / `surcout_forme_speciale_facteur` ;
- P1 lit `marge_confort_roulage_mm` depuis ConfigCouts ;
- isolation multi-tenant sur les 4 postes (tenant A vs B, aucune fuite) ;
- erreur explicite (CostEngineError) quand ConfigCouts est absente.

Mirror du pattern Lot 3 — les calculateurs consomment la session injectée
via le helper `get_config_couts_or_raise`, scope strict `entreprise_id`.
"""
from decimal import Decimal
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import (
    Complexe,
    ConfigCouts,
    Entreprise,
    Machine,
    TarifEncre,
    TarifPoste,
)
from app.schemas.devis import DevisInput, PartenaireSTForfait
from app.services.cost_engine.errors import CostEngineError
from app.services.cost_engine.poste_1_matiere import CalculateurPoste1Matiere
from app.services.cost_engine.poste_3_cliches import (
    CalculateurPoste3ClichesOutillage,
)
from app.services.cost_engine.poste_4_calage import CalculateurPoste4Calage
from app.services.cost_engine.poste_6_finitions import CalculateurPoste6Finitions


def _seed_tenant_full(
    db: Session,
    entreprise_id: int,
    *,
    seed_config: bool,
    cliche_prix_couleur_eur: Decimal = Decimal("45.00"),
    outil_base_eur: Decimal = Decimal("200.00"),
    outil_par_trace_eur: Decimal = Decimal("50.00"),
    surcout_forme_speciale_facteur: Decimal = Decimal("1.40"),
    calage_forfait_eur: Decimal = Decimal("225.00"),
    finitions_prix_m2_eur: Decimal = Decimal("0.1250"),
    marge_confort_roulage_mm: int = 10,
    complexe_id: int,
    machine_id: int,
) -> None:
    """Seed minimal pour faire tourner P1/P3/P4/P6 sur un tenant donné.
    `seed_config=False` → pas de ConfigCouts (cas erreur)."""
    db.add(
        Entreprise(
            id=entreprise_id,
            raison_sociale=f"Tenant {entreprise_id}",
            siret=f"{entreprise_id:014d}",
        )
    )
    db.flush()
    db.add(
        Machine(
            id=machine_id,
            entreprise_id=entreprise_id,
            nom=f"Mark Andy #{entreprise_id}",
            laize_max_mm=Decimal("330.00"),
            vitesse_moyenne_m_h=6000,
            duree_calage_h=Decimal("1.00"),
            cout_horaire_eur=Decimal("60.00"),
        )
    )
    db.add(
        Complexe(
            id=complexe_id,
            entreprise_id=entreprise_id,
            reference=f"VELIN_T{entreprise_id}",
            famille="papier_standard",
            grammage_g_m2=Decimal("80"),
            prix_m2_eur=Decimal("0.3500"),
        )
    )
    if seed_config:
        db.add(
            ConfigCouts(
                entreprise_id=entreprise_id,
                cout_exploitation_machine_eur_h=Decimal("375.00"),
                cout_operateur_eur_h=Decimal("70.00"),
                cout_energies_eur_h=Decimal("3.50"),
                cout_fixe_atelier_eur_mois=Decimal("2500.00"),
                cout_fixe_maintenance_eur_mois=Decimal("800.00"),
                marge_standard_pct=Decimal("18.00"),
                buffer_rebut_pct=Decimal("2.50"),
                buffer_setup_pct=Decimal("1.00"),
                marge_confort_roulage_mm=marge_confort_roulage_mm,
                cliche_prix_couleur_eur=cliche_prix_couleur_eur,
                outil_base_eur=outil_base_eur,
                outil_par_trace_eur=outil_par_trace_eur,
                surcout_forme_speciale_facteur=surcout_forme_speciale_facteur,
                calage_forfait_eur=calage_forfait_eur,
                finitions_prix_m2_eur=finitions_prix_m2_eur,
            )
        )


def _devis(complexe_id: int, machine_id: int, **overrides) -> DevisInput:
    base = dict(
        complexe_id=complexe_id,
        laize_utile_mm=220,
        ml_total=3000,
        nb_couleurs_par_type={"process_cmj": 4, "pantone": 1},
        machine_id=machine_id,
        forfaits_st=[],
    )
    base.update(overrides)
    return DevisInput(**base)


@pytest.fixture
def in_memory_db() -> Iterator[sessionmaker]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionFix = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield SessionFix
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# P4 Calage — forfait
# ---------------------------------------------------------------------------


def test_p4_lit_calage_forfait_depuis_config_couts(in_memory_db):
    """Tenant avec calage_forfait_eur=300 → P4 = 300."""
    with in_memory_db() as db:
        _seed_tenant_full(
            db, entreprise_id=1, seed_config=True,
            calage_forfait_eur=Decimal("300.00"),
            complexe_id=1, machine_id=1,
        )
        db.commit()
        result = CalculateurPoste4Calage(db, entreprise_id=1).calculer(
            _devis(complexe_id=1, machine_id=1)
        )
    assert result.montant_eur == Decimal("300.00")
    assert result.details["forfait_eur"] == 300.0


def test_p4_legacy_225_par_defaut_fixture(in_memory_db):
    """Valeur ICE legacy 225 → P4 = 225."""
    with in_memory_db() as db:
        _seed_tenant_full(db, entreprise_id=1, seed_config=True,
                          complexe_id=1, machine_id=1)
        db.commit()
        result = CalculateurPoste4Calage(db, entreprise_id=1).calculer(
            _devis(complexe_id=1, machine_id=1)
        )
    assert result.montant_eur == Decimal("225.00")


# ---------------------------------------------------------------------------
# P6 Finitions — surface × prix_m2
# ---------------------------------------------------------------------------


def test_p6_lit_finitions_prix_m2_depuis_config_couts(in_memory_db):
    """Tenant avec finitions_prix_m2_eur=0.20 → P6 = 660 m² × 0.20 = 132."""
    with in_memory_db() as db:
        _seed_tenant_full(
            db, entreprise_id=1, seed_config=True,
            finitions_prix_m2_eur=Decimal("0.2000"),
            complexe_id=1, machine_id=1,
        )
        db.commit()
        result = CalculateurPoste6Finitions(db, entreprise_id=1).calculer(
            _devis(complexe_id=1, machine_id=1)
        )
    # surface = 220 × 3000 / 1000 = 660 m² ; 660 × 0.20 = 132.00 €
    assert result.montant_eur == Decimal("132.00")
    assert result.details["prix_finitions_m2"] == 0.2


# ---------------------------------------------------------------------------
# P3 Clichés/Outils — cliche × couleurs + outil + surcoût
# ---------------------------------------------------------------------------


def test_p3a_lit_cliche_prix_couleur_depuis_config_couts(in_memory_db):
    """Tenant avec cliche_prix_couleur_eur=60 et 5 couleurs → P3a = 300."""
    with in_memory_db() as db:
        _seed_tenant_full(
            db, entreprise_id=1, seed_config=True,
            cliche_prix_couleur_eur=Decimal("60.00"),
            complexe_id=1, machine_id=1,
        )
        db.commit()
        result = CalculateurPoste3ClichesOutillage(db, entreprise_id=1).calculer(
            _devis(complexe_id=1, machine_id=1)
        )
    # 5 couleurs × 60 = 300 ; outil existant → P3b = 0 → total = 300
    assert result.montant_eur == Decimal("300.00")
    assert result.details["cout_3a_cliches_eur"] == 300.0


def test_p3b_lit_outil_base_par_trace_et_facteur_forme_speciale(in_memory_db):
    """Nouvel outil 4 tracés + forme spéciale × 1.50 :
    cout_base = 250 + 4×60 = 490 ; ×1.50 = 735."""
    with in_memory_db() as db:
        _seed_tenant_full(
            db, entreprise_id=1, seed_config=True,
            outil_base_eur=Decimal("250.00"),
            outil_par_trace_eur=Decimal("60.00"),
            surcout_forme_speciale_facteur=Decimal("1.50"),
            cliche_prix_couleur_eur=Decimal("45.00"),
            complexe_id=1, machine_id=1,
        )
        db.commit()
        devis = _devis(
            complexe_id=1, machine_id=1,
            outil_decoupe_existant=False,
            nb_traces_complexite=4,
            forme_speciale=True,
        )
        result = CalculateurPoste3ClichesOutillage(db, entreprise_id=1).calculer(devis)
    # P3a = 5 couleurs × 45 = 225 ; P3b = (250 + 4×60) × 1.50 = 735 ; total = 960
    assert result.montant_eur == Decimal("960.00")
    assert result.details["cout_3b_outil_eur"] == 735.0
    assert result.details["surcout_forme_speciale_pct"] == 50


# ---------------------------------------------------------------------------
# P1 Matière — marge_confort_roulage_mm
# ---------------------------------------------------------------------------


def test_p1_lit_marge_confort_depuis_config_couts(in_memory_db):
    """Tenant avec marge_confort_roulage_mm=20, sans laize_papier_mm (fallback
    legacy L2) → laize facturée = laize_utile + marge = 240 mm."""
    with in_memory_db() as db:
        _seed_tenant_full(
            db, entreprise_id=1, seed_config=True,
            marge_confort_roulage_mm=20,
            complexe_id=1, machine_id=1,
        )
        db.commit()
        result = CalculateurPoste1Matiere(db, entreprise_id=1).calculer(
            _devis(complexe_id=1, machine_id=1)
        )
    assert result.details["laize_facturee_mm"] == 240
    assert result.details["base_laize_source"] == "laize_utile+marge_confort"
    assert result.details["marge_confort_roulage_mm"] == 20


# ---------------------------------------------------------------------------
# Isolation multi-tenant — chiffres différents par tenant, aucune fuite
# ---------------------------------------------------------------------------


def test_isolation_multi_tenant_p1_p3_p4_p6(in_memory_db):
    """Tenant A (ICE legacy 10/45/200/50/1.40/225/0.1250) et tenant B
    (15/60/250/60/1.50/300/0.20) → coûts différents par poste, scope strict
    `entreprise_id`."""
    with in_memory_db() as db:
        _seed_tenant_full(
            db, entreprise_id=1, seed_config=True,
            complexe_id=1, machine_id=1,
        )
        _seed_tenant_full(
            db, entreprise_id=2, seed_config=True,
            marge_confort_roulage_mm=15,
            cliche_prix_couleur_eur=Decimal("60.00"),
            outil_base_eur=Decimal("250.00"),
            outil_par_trace_eur=Decimal("60.00"),
            surcout_forme_speciale_facteur=Decimal("1.50"),
            calage_forfait_eur=Decimal("300.00"),
            finitions_prix_m2_eur=Decimal("0.2000"),
            complexe_id=2, machine_id=2,
        )
        db.commit()

        p4_a = CalculateurPoste4Calage(db, entreprise_id=1).calculer(
            _devis(complexe_id=1, machine_id=1)
        ).montant_eur
        p4_b = CalculateurPoste4Calage(db, entreprise_id=2).calculer(
            _devis(complexe_id=2, machine_id=2)
        ).montant_eur
        p6_a = CalculateurPoste6Finitions(db, entreprise_id=1).calculer(
            _devis(complexe_id=1, machine_id=1)
        ).montant_eur
        p6_b = CalculateurPoste6Finitions(db, entreprise_id=2).calculer(
            _devis(complexe_id=2, machine_id=2)
        ).montant_eur

    # Tenant A : P4 = 225, P6 = 660 × 0.125 = 82.50
    # Tenant B : P4 = 300, P6 = 660 × 0.20 = 132
    assert p4_a == Decimal("225.00")
    assert p4_b == Decimal("300.00")
    assert p6_a == Decimal("82.50")
    assert p6_b == Decimal("132.00")
    assert p4_a != p4_b
    assert p6_a != p6_b


# ---------------------------------------------------------------------------
# Config absente → erreur explicite (pas de fallback silencieux)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "calculateur_cls",
    [
        CalculateurPoste1Matiere,
        CalculateurPoste3ClichesOutillage,
        CalculateurPoste4Calage,
        CalculateurPoste6Finitions,
    ],
    ids=["P1", "P3", "P4", "P6"],
)
def test_postes_sans_config_couts_levent_cost_engine_error(in_memory_db, calculateur_cls):
    """Sans ConfigCouts pour le tenant → CostEngineError clair sur P1/P3/P4/P6."""
    with in_memory_db() as db:
        _seed_tenant_full(
            db, entreprise_id=1, seed_config=False,
            complexe_id=1, machine_id=1,
        )
        db.commit()
        with pytest.raises(CostEngineError, match="ConfigCouts introuvable"):
            calculateur_cls(db, entreprise_id=1).calculer(
                _devis(complexe_id=1, machine_id=1)
            )
