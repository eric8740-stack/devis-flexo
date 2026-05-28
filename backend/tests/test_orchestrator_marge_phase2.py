"""Phase 2 Lot 2 — résolution de la marge depuis ConfigCouts par tenant.

Couvre :
- la marge lue depuis `ConfigCouts.marge_standard_pct` (et non plus
  `Entreprise.pct_marge_defaut`) ;
- l'isolation multi-tenant (tenant A vs tenant B → chacun sa marge,
  aucune fuite via l'ancien `select(Entreprise).limit(1)`) ;
- le comportement explicite quand la config est absente (erreur claire,
  pas de retour silencieux à 0.18).

Indépendant du benchmark figé (qui couvre déjà la conservation des sacrés
V1a/V1b/…). Ici on isole spécifiquement la résolution de marge.
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
from app.services.cost_engine import MoteurDevis
from app.services.cost_engine.errors import CostEngineError

# Minimal tarifs pour faire tourner le moteur (mêmes valeurs ICE que le
# benchmark fixture, sauf marge — variable selon le scénario testé).
_TARIF_POSTE_MIN = [
    ("matiere_prix_kg_defaut", 1, "Prix matière par kilo", Decimal("1.7500"), "€/kg"),
    ("cliche_prix_couleur", 3, "Cliché par couleur", Decimal("45.0000"), "€/couleur"),
    ("calage_forfait", 4, "Calage forfaitaire", Decimal("225.0000"), "€/devis"),
    ("roulage_prix_horaire", 5, "Prix horaire roulage", Decimal("375.0000"), "€/h"),
    ("marge_confort_roulage_mm", 1, "Marge confort", Decimal("10.0000"), "mm"),
    ("finitions_prix_m2", 6, "Prix finitions", Decimal("0.1250"), "€/m²"),
    ("mo_prix_horaire", 7, "Prix horaire MO", Decimal("70.0000"), "€/h"),
    ("outil_base_eur", 3, "Outil base", Decimal("200.0000"), "€"),
    ("outil_par_trace_eur", 3, "Outil par trace", Decimal("50.0000"), "€"),
    ("surcout_forme_speciale_pct", 3, "Surcoût forme spé", Decimal("1.4000"), "×"),
]
_TARIF_ENCRE_MIN = [
    ("process_cmj", "Process CMJ", Decimal("15.75"), Decimal("2.000")),
    ("pantone", "Pantone", Decimal("21.50"), Decimal("2.000")),
    ("blanc_high_opaque", "Blanc HO", Decimal("14.00"), Decimal("2.000")),
]


def _seed_tenant(
    db: Session,
    entreprise_id: int,
    marge_standard_pct: Decimal | None,
    complexe_id: int,
    machine_id: int,
    tarif_id_offset: int = 0,
) -> None:
    """Insère un tenant complet pour faire tourner le moteur. Si
    `marge_standard_pct` est None, on n'insère PAS de ConfigCouts (cas
    «config absente» testé)."""
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
            nom=f"Mark Andy P5 #{entreprise_id}",
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
    if marge_standard_pct is not None:
        db.add(
            ConfigCouts(
                entreprise_id=entreprise_id,
                marge_standard_pct=marge_standard_pct,
                cout_exploitation_machine_eur_h=Decimal("50.00"),
                cout_operateur_eur_h=Decimal("25.00"),
                cout_energies_eur_h=Decimal("3.50"),
                cout_fixe_atelier_eur_mois=Decimal("2500.00"),
                cout_fixe_maintenance_eur_mois=Decimal("800.00"),
                buffer_rebut_pct=Decimal("2.50"),
                buffer_setup_pct=Decimal("1.00"),
            )
        )
    for i, (cle, poste, libelle, val, unite) in enumerate(_TARIF_POSTE_MIN):
        db.add(
            TarifPoste(
                id=tarif_id_offset + i + 1,
                entreprise_id=entreprise_id,
                cle=f"{cle}_t{entreprise_id}",  # cle unique cross-tenant : suffixée
                poste_numero=poste,
                libelle=libelle,
                valeur_defaut=val,
                unite=unite,
            )
        )
    for i, (type_encre, libelle, prix, ratio) in enumerate(_TARIF_ENCRE_MIN):
        db.add(
            TarifEncre(
                id=tarif_id_offset + 100 + i + 1,
                entreprise_id=entreprise_id,
                type_encre=f"{type_encre}_t{entreprise_id}",
                libelle=libelle,
                prix_kg_defaut=prix,
                ratio_g_m2_couleur=ratio,
            )
        )


@pytest.fixture
def in_memory_db() -> Iterator[sessionmaker]:
    """Session SQLite in-memory vierge, sans seed CSV."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionFix = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield SessionFix
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# UNIT — `_resolve_pct_marge` lit ConfigCouts.marge_standard_pct
# ---------------------------------------------------------------------------


def test_marge_lue_depuis_config_couts(in_memory_db):
    """Tenant avec ConfigCouts.marge_standard_pct = 22 % → fraction 0.22."""
    with in_memory_db() as db:
        _seed_tenant(db, entreprise_id=1, marge_standard_pct=Decimal("22.00"),
                     complexe_id=1, machine_id=1)
        db.commit()
        moteur = MoteurDevis(db, entreprise_id=1)
        # Accès direct au helper interne pour isoler la résolution.
        devis = DevisInput(
            complexe_id=1, laize_utile_mm=220, ml_total=3000,
            nb_couleurs_par_type={}, machine_id=1, forfaits_st=[],
        )
        assert moteur._resolve_pct_marge(devis) == Decimal("0.22")


def test_override_devis_prioritaire_sur_config(in_memory_db):
    """`devis.pct_marge_override` court-circuite la lecture ConfigCouts."""
    with in_memory_db() as db:
        _seed_tenant(db, entreprise_id=1, marge_standard_pct=Decimal("22.00"),
                     complexe_id=1, machine_id=1)
        db.commit()
        moteur = MoteurDevis(db, entreprise_id=1)
        devis = DevisInput(
            complexe_id=1, laize_utile_mm=220, ml_total=3000,
            nb_couleurs_par_type={}, machine_id=1, forfaits_st=[],
            pct_marge_override=Decimal("0.45"),
        )
        assert moteur._resolve_pct_marge(devis) == Decimal("0.45")


# ---------------------------------------------------------------------------
# ISOLATION multi-tenant
# ---------------------------------------------------------------------------


def test_isolation_multi_tenant_chaque_tenant_sa_marge(in_memory_db):
    """Tenant A (18 %) et Tenant B (30 %) cohabitent — aucune fuite. L'ancien
    bug `select(Entreprise).limit(1)` aurait servi la marge du 1er tenant
    à tout le monde ; après fix, chaque tenant reçoit la sienne."""
    with in_memory_db() as db:
        _seed_tenant(db, entreprise_id=1, marge_standard_pct=Decimal("18.00"),
                     complexe_id=1, machine_id=1, tarif_id_offset=0)
        _seed_tenant(db, entreprise_id=2, marge_standard_pct=Decimal("30.00"),
                     complexe_id=2, machine_id=2, tarif_id_offset=1000)
        db.commit()
        devis_factory = lambda complexe_id, machine_id: DevisInput(
            complexe_id=complexe_id, laize_utile_mm=220, ml_total=3000,
            nb_couleurs_par_type={}, machine_id=machine_id, forfaits_st=[],
        )
        marge_a = MoteurDevis(db, entreprise_id=1)._resolve_pct_marge(
            devis_factory(1, 1)
        )
        marge_b = MoteurDevis(db, entreprise_id=2)._resolve_pct_marge(
            devis_factory(2, 2)
        )
        assert marge_a == Decimal("0.18")
        assert marge_b == Decimal("0.30")
        # Et l'inverse : tenant 1 ne récupère JAMAIS la marge de 2.
        assert marge_a != marge_b


# ---------------------------------------------------------------------------
# Config absente → erreur explicite (pas de fallback silencieux)
# ---------------------------------------------------------------------------


def test_config_couts_absente_leve_cost_engine_error(in_memory_db):
    """Tenant sans ConfigCouts (cas onboarding incomplet) → erreur claire,
    pas de retour silencieux à l'ancienne constante 0.18."""
    with in_memory_db() as db:
        # marge_standard_pct=None → on n'insère PAS de ConfigCouts.
        _seed_tenant(db, entreprise_id=1, marge_standard_pct=None,
                     complexe_id=1, machine_id=1)
        db.commit()
        moteur = MoteurDevis(db, entreprise_id=1)
        devis = DevisInput(
            complexe_id=1, laize_utile_mm=220, ml_total=3000,
            nb_couleurs_par_type={}, machine_id=1, forfaits_st=[],
        )
        with pytest.raises(CostEngineError, match="ConfigCouts introuvable"):
            moteur._resolve_pct_marge(devis)


def test_config_couts_absente_avec_override_continue(in_memory_db):
    """`devis.pct_marge_override` reste prioritaire même quand ConfigCouts
    manque — pas d'erreur (le moteur doit pouvoir tourner sur override)."""
    with in_memory_db() as db:
        _seed_tenant(db, entreprise_id=1, marge_standard_pct=None,
                     complexe_id=1, machine_id=1)
        db.commit()
        moteur = MoteurDevis(db, entreprise_id=1)
        devis = DevisInput(
            complexe_id=1, laize_utile_mm=220, ml_total=3000,
            nb_couleurs_par_type={}, machine_id=1, forfaits_st=[],
            pct_marge_override=Decimal("0.42"),
        )
        assert moteur._resolve_pct_marge(devis) == Decimal("0.42")
