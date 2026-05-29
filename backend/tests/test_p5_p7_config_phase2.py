"""Phase 2 Lot 3 — P5 Roulage et P7 MO basculent sur ConfigCouts.

Couvre :
- P5 lu depuis `ConfigCouts.cout_exploitation_machine_eur_h` (tenant à
  400 €/h → coût reflète 400) ;
- P7 lu depuis `ConfigCouts.cout_operateur_eur_h` (tenant à 80 €/h →
  coût reflète 80) ;
- isolation multi-tenant (tenant A vs tenant B, valeurs différentes,
  aucune fuite cross-tenant) ;
- erreur explicite quand ConfigCouts est absente (pas de fallback
  silencieux sur l'ancien TarifPoste).

Indépendant du benchmark figé (qui couvre les sacrés). Ici on isole le
calcul P5/P7 sur fixtures in-memory pures.
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
from app.schemas.devis import DevisInput
from app.services.cost_engine.errors import CostEngineError
from app.services.cost_engine.poste_5_roulage import CalculateurPoste5Roulage
from app.services.cost_engine.poste_7_mo import CalculateurPoste7MO

# Tarifs minimaux nécessaires aux calculateurs (P5/P7 ne consomment plus de
# TarifPoste après Lot 3, mais d'autres calculateurs pourraient en avoir
# besoin si on les ajoute au test — on ne seede QUE ce qui est utilisé).


def _seed_tenant_p5_p7(
    db: Session,
    entreprise_id: int,
    cout_exploitation_eur_h: Decimal | None,
    cout_operateur_eur_h: Decimal | None,
    machine_id: int,
    *,
    seed_config: bool = True,
) -> None:
    """Seed minimal pour faire tourner P5 et P7 (entreprise + machine +
    éventuellement ConfigCouts). Si `seed_config=False` ou les coûts sont
    None, on n'insère PAS de ConfigCouts → cas «config absente»."""
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
    if seed_config:
        db.add(
            ConfigCouts(
                entreprise_id=entreprise_id,
                cout_exploitation_machine_eur_h=cout_exploitation_eur_h or Decimal("375.00"),
                cout_operateur_eur_h=cout_operateur_eur_h or Decimal("70.00"),
                cout_energies_eur_h=Decimal("3.50"),
                cout_fixe_atelier_eur_mois=Decimal("2500.00"),
                cout_fixe_maintenance_eur_mois=Decimal("800.00"),
                marge_standard_pct=Decimal("18.00"),
                buffer_rebut_pct=Decimal("2.50"),
                buffer_setup_pct=Decimal("1.00"),
            )
        )


def _devis_input(machine_id: int, ml_total: int = 3000) -> DevisInput:
    return DevisInput(
        complexe_id=999,  # P5/P7 ne lisent pas le complexe
        laize_utile_mm=220,
        ml_total=ml_total,
        nb_couleurs_par_type={},
        machine_id=machine_id,
        forfaits_st=[],
    )


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
# P5 Roulage — lu depuis ConfigCouts.cout_exploitation_machine_eur_h
# ---------------------------------------------------------------------------


def test_p5_lit_cout_exploitation_machine_depuis_config_couts(in_memory_db):
    """Tenant avec cout_exploitation=400 €/h → P5 = ml/vitesse × 400."""
    with in_memory_db() as db:
        _seed_tenant_p5_p7(
            db, entreprise_id=1,
            cout_exploitation_eur_h=Decimal("400.00"),
            cout_operateur_eur_h=Decimal("70.00"),
            machine_id=1,
        )
        db.commit()
        result = CalculateurPoste5Roulage(db, entreprise_id=1).calculer(
            _devis_input(machine_id=1)
        )
    # temps = 3000/6000 = 0.5 h × 400 = 200.00 €
    assert result.montant_eur == Decimal("200.00")
    assert result.details["prix_horaire_eur"] == 400.0


def test_p5_legacy_375_par_defaut_fixture(in_memory_db):
    """Avec cout_exploitation=375 €/h (valeur ICE héritée), P5 = 187.50 €
    sur le cas médian (3000 ml / 6000 m/h × 375). Vérifie la continuité."""
    with in_memory_db() as db:
        _seed_tenant_p5_p7(
            db, entreprise_id=1,
            cout_exploitation_eur_h=Decimal("375.00"),
            cout_operateur_eur_h=Decimal("70.00"),
            machine_id=1,
        )
        db.commit()
        result = CalculateurPoste5Roulage(db, entreprise_id=1).calculer(
            _devis_input(machine_id=1)
        )
    assert result.montant_eur == Decimal("187.50")


# ---------------------------------------------------------------------------
# P7 MO — lu depuis ConfigCouts.cout_operateur_eur_h
# ---------------------------------------------------------------------------


def test_p7_lit_cout_operateur_depuis_config_couts(in_memory_db):
    """Tenant avec cout_operateur=80 €/h → P7 = (calage + prod) × 80."""
    with in_memory_db() as db:
        _seed_tenant_p5_p7(
            db, entreprise_id=1,
            cout_exploitation_eur_h=Decimal("375.00"),
            cout_operateur_eur_h=Decimal("80.00"),
            machine_id=1,
        )
        db.commit()
        result = CalculateurPoste7MO(db, entreprise_id=1).calculer(
            _devis_input(machine_id=1)
        )
    # heures = duree_calage 1.0 + (3000 / 6000) = 1.5 h × 80 = 120.00 €
    assert result.montant_eur == Decimal("120.00")
    assert result.details["prix_horaire_mo_eur"] == 80.0


def test_p7_legacy_70_par_defaut_fixture(in_memory_db):
    """Avec cout_operateur=70 €/h (valeur ICE héritée), P7 = 105.00 €
    sur le cas médian (1.0 + 0.5 = 1.5 h × 70)."""
    with in_memory_db() as db:
        _seed_tenant_p5_p7(
            db, entreprise_id=1,
            cout_exploitation_eur_h=Decimal("375.00"),
            cout_operateur_eur_h=Decimal("70.00"),
            machine_id=1,
        )
        db.commit()
        result = CalculateurPoste7MO(db, entreprise_id=1).calculer(
            _devis_input(machine_id=1)
        )
    assert result.montant_eur == Decimal("105.00")


# ---------------------------------------------------------------------------
# Isolation multi-tenant
# ---------------------------------------------------------------------------


def test_p5_p7_isolation_multi_tenant(in_memory_db):
    """Tenant A (P5 375, P7 70) et tenant B (P5 500, P7 100) — chacun sa
    config, aucune fuite. Verrouille le pattern Phase 2 (scope strict
    `filter_by(entreprise_id=...)`)."""
    with in_memory_db() as db:
        _seed_tenant_p5_p7(
            db, entreprise_id=1,
            cout_exploitation_eur_h=Decimal("375.00"),
            cout_operateur_eur_h=Decimal("70.00"),
            machine_id=1,
        )
        _seed_tenant_p5_p7(
            db, entreprise_id=2,
            cout_exploitation_eur_h=Decimal("500.00"),
            cout_operateur_eur_h=Decimal("100.00"),
            machine_id=2,
        )
        db.commit()
        p5_a = CalculateurPoste5Roulage(db, entreprise_id=1).calculer(
            _devis_input(machine_id=1)
        )
        p5_b = CalculateurPoste5Roulage(db, entreprise_id=2).calculer(
            _devis_input(machine_id=2)
        )
        p7_a = CalculateurPoste7MO(db, entreprise_id=1).calculer(
            _devis_input(machine_id=1)
        )
        p7_b = CalculateurPoste7MO(db, entreprise_id=2).calculer(
            _devis_input(machine_id=2)
        )
    # Tenant A : P5 = 0.5 × 375 = 187.50 ; P7 = 1.5 × 70 = 105.00
    assert p5_a.montant_eur == Decimal("187.50")
    assert p7_a.montant_eur == Decimal("105.00")
    # Tenant B : P5 = 0.5 × 500 = 250.00 ; P7 = 1.5 × 100 = 150.00
    assert p5_b.montant_eur == Decimal("250.00")
    assert p7_b.montant_eur == Decimal("150.00")
    # Aucune fuite : les montants A et B sont strictement distincts.
    assert p5_a.montant_eur != p5_b.montant_eur
    assert p7_a.montant_eur != p7_b.montant_eur


# ---------------------------------------------------------------------------
# Config absente → erreur explicite (pas de fallback silencieux)
# ---------------------------------------------------------------------------


def test_p5_sans_config_couts_leve_cost_engine_error(in_memory_db):
    """Tenant sans ConfigCouts (onboarding incomplet) → CostEngineError clair
    sur P5. Pas de retour silencieux à l'ancien TarifPoste."""
    with in_memory_db() as db:
        _seed_tenant_p5_p7(
            db, entreprise_id=1,
            cout_exploitation_eur_h=None,
            cout_operateur_eur_h=None,
            machine_id=1, seed_config=False,
        )
        db.commit()
        with pytest.raises(CostEngineError, match="ConfigCouts introuvable"):
            CalculateurPoste5Roulage(db, entreprise_id=1).calculer(
                _devis_input(machine_id=1)
            )


def test_p7_sans_config_couts_leve_cost_engine_error(in_memory_db):
    """Tenant sans ConfigCouts → CostEngineError clair sur P7."""
    with in_memory_db() as db:
        _seed_tenant_p5_p7(
            db, entreprise_id=1,
            cout_exploitation_eur_h=None,
            cout_operateur_eur_h=None,
            machine_id=1, seed_config=False,
        )
        db.commit()
        with pytest.raises(CostEngineError, match="ConfigCouts introuvable"):
            CalculateurPoste7MO(db, entreprise_id=1).calculer(
                _devis_input(machine_id=1)
            )
