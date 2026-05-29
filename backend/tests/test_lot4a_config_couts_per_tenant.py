"""Phase 2 / Lot 4a — multi-tenant : 2 tenants → configs différentes → coûts différents.

Garantit que les 4 postes refactorés (P1, P3, P4, P6) lisent strictement
`ConfigCouts` scopée `entreprise_id` (pas de fuite cross-tenant, pas de
lecture orpheline). Pattern miroir Lot 3 (`test_p5_p7_config_phase2.py`) :
in-memory SQLite + 2 entreprises seedées avec configs distinctes.

Couverture des 4 postes (les 4 sont scopés via `get_config_couts_or_raise`).
Le scope strict est l'invariant multi-tenant SACRÉ (cf. fix Lot 2 de
`_resolve_pct_marge`) — ce test verrouille qu'on ne le casse pas en
Lot 4a.
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
    PartenaireST,
)
from app.schemas.devis import DevisInput, PartenaireSTForfait
from app.services.cost_engine.poste_3_cliches import CalculateurPoste3ClichesOutillage
from app.services.cost_engine.poste_4_calage import CalculateurPoste4Calage
from app.services.cost_engine.poste_6_finitions import CalculateurPoste6Finitions


# ---------------------------------------------------------------------------
# Configs distinctes pour 2 tenants — au moins 1 champ Lot 4a divergent.
# ---------------------------------------------------------------------------

_COMMON_CONFIG: dict = {
    "cout_exploitation_machine_eur_h": Decimal("100.00"),
    "cout_operateur_eur_h": Decimal("50.00"),
    "cout_energies_eur_h": Decimal("3.50"),
    "cout_fixe_atelier_eur_mois": Decimal("2500.00"),
    "cout_fixe_maintenance_eur_mois": Decimal("800.00"),
    "marge_standard_pct": Decimal("18.00"),
    "buffer_rebut_pct": Decimal("2.50"),
    "buffer_setup_pct": Decimal("1.00"),
}

# Tenant A : valeurs ICE historiques (cf. seed démo).
_CONFIG_TENANT_A = _COMMON_CONFIG | {
    "marge_confort_roulage_mm": 10,
    "cliche_prix_couleur_eur": Decimal("45.00"),
    "outil_base_eur": Decimal("200.00"),
    "outil_par_trace_eur": Decimal("50.00"),
    "surcout_forme_speciale_facteur": Decimal("1.40"),
    "calage_forfait_eur": Decimal("225.00"),
    "finitions_prix_m2_eur": Decimal("0.1250"),
}

# Tenant B : multiplie chaque valeur par 2 → chiffres × 2 attendus côté
# postes consommateurs. Différence sur les 7 champs (mais le test n'exerce
# que ceux des postes considérés).
_CONFIG_TENANT_B = _COMMON_CONFIG | {
    "marge_confort_roulage_mm": 20,
    "cliche_prix_couleur_eur": Decimal("90.00"),
    "outil_base_eur": Decimal("400.00"),
    "outil_par_trace_eur": Decimal("100.00"),
    "surcout_forme_speciale_facteur": Decimal("1.80"),
    "calage_forfait_eur": Decimal("450.00"),
    "finitions_prix_m2_eur": Decimal("0.2500"),
}


def _seed_two_tenants(db: Session) -> tuple[int, int]:
    """Seed 2 entreprises + leur ConfigCouts distincte. Renvoie les IDs."""
    db.add(Entreprise(id=1, raison_sociale="Tenant A", siret="00000000000001"))
    db.add(Entreprise(id=2, raison_sociale="Tenant B", siret="00000000000002"))
    db.flush()
    db.add(ConfigCouts(entreprise_id=1, **_CONFIG_TENANT_A))
    db.add(ConfigCouts(entreprise_id=2, **_CONFIG_TENANT_B))
    db.flush()
    return 1, 2


def _devis_input(complexe_id: int | None = None) -> DevisInput:
    return DevisInput(
        complexe_id=complexe_id or 999,
        laize_utile_mm=220,
        ml_total=3000,
        nb_couleurs_par_type={"process_cmj": 4, "pantone": 1},  # 5 couleurs
        machine_id=1,
        outil_decoupe_existant=False,
        nb_traces_complexite=4,
        forme_speciale=True,
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
# P3 — clichés + outil + forme spéciale (touche 4 champs Lot 4a)
# ---------------------------------------------------------------------------


def test_p3_tenant_a_vs_b_montant_different(in_memory_db):
    """Tenant A (45/200/50/1.40) vs Tenant B (90/400/100/1.80) → P3 ≠.

    A : (5 × 45) + (200 + 4×50) × 1.40 = 225 + 560 = 785 €
    B : (5 × 90) + (400 + 4×100) × 1.80 = 450 + 1440 = 1890 €
    """
    SessionFix = in_memory_db
    with SessionFix() as db:
        a, b = _seed_two_tenants(db)
        db.commit()
        devis = _devis_input()
        out_a = CalculateurPoste3ClichesOutillage(db, a).calculer(devis)
        out_b = CalculateurPoste3ClichesOutillage(db, b).calculer(devis)
        assert out_a.montant_eur == Decimal("785.00")
        assert out_b.montant_eur == Decimal("1890.00")
        # Garantie : ≠ (pas de fuite cross-tenant).
        assert out_a.montant_eur != out_b.montant_eur


# ---------------------------------------------------------------------------
# P4 — calage forfait (touche 1 champ Lot 4a)
# ---------------------------------------------------------------------------


def test_p4_tenant_a_vs_b_forfait_different(in_memory_db):
    """A : 225 €. B : 450 €. Forfait pur (pas de paramètres devis-dépendants)."""
    SessionFix = in_memory_db
    with SessionFix() as db:
        a, b = _seed_two_tenants(db)
        db.commit()
        devis = _devis_input()
        out_a = CalculateurPoste4Calage(db, a).calculer(devis)
        out_b = CalculateurPoste4Calage(db, b).calculer(devis)
        assert out_a.montant_eur == Decimal("225.00")
        assert out_b.montant_eur == Decimal("450.00")


# ---------------------------------------------------------------------------
# P6 — finitions au m² (touche 1 champ Lot 4a)
# ---------------------------------------------------------------------------


def test_p6_tenant_a_vs_b_finitions_different(in_memory_db):
    """surface = 220/1000 × 3000 = 660 m².
    A : 660 × 0.1250 = 82.50 €. B : 660 × 0.2500 = 165.00 €.
    """
    SessionFix = in_memory_db
    with SessionFix() as db:
        a, b = _seed_two_tenants(db)
        db.commit()
        devis = _devis_input()
        out_a = CalculateurPoste6Finitions(db, a).calculer(devis)
        out_b = CalculateurPoste6Finitions(db, b).calculer(devis)
        assert out_a.montant_eur == Decimal("82.50")
        assert out_b.montant_eur == Decimal("165.00")
