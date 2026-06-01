"""B3a (convergence option B) — tests du repointage du loader optimisation
sur le modèle `Machine` (au lieu de `MachineImprimerie`).

Couvre :
  - `charger_machines_actives(entreprise_id=1)` retourne le parc reel du
    tenant demo (3 machines : Mark Andy P5, Daco D250, Atelier 2).
  - Ne retourne PAS "Mark Andy 2200" (le catalogue MachineImprimerie issu
    de l'onboarding) -- meme si MachineImprimerie est seede dans la base.
  - `vitesse_pratique_m_min` est derivee de `vitesse_moyenne_m_h / 60` :
    P5=6000 m/h -> 100 m/min, Daco=3500 m/h -> 58 m/min, Atelier2=4500 m/h
    -> 75 m/min. Une seule vitesse reelle (B2 decision).
  - Mapping des champs optim B1/B2 : laize_utile_mm, nb_postes_decoupe,
    nb_groupes_couleurs, options.
  - Fallback laize_utile_mm -> laize_max_mm si NULL (nouveau tenant).
  - Machine sans vitesse_moyenne_m_h est silencieusement ECARTEE.
  - Scope multi-tenant strict (tenant A ne voit pas les machines de B).

Sources :
  - backend/app/services/optimisation_loader.py:45-100 (charger_machines_actives)
  - backend/app/routers/optimisation.py:301-307 (nom_par_machine)
"""
from __future__ import annotations

from decimal import Decimal

from app.db import SessionLocal
from app.models import Entreprise, Machine
from app.services.optimisation_loader import charger_machines_actives


DEMO_ENTREPRISE_ID = 1


def _ensure_tenant(db, entreprise_id: int, raison: str) -> Entreprise:
    """Idempotent : cree l'Entreprise temporaire de test si absente."""
    ent = db.query(Entreprise).filter_by(id=entreprise_id).first()
    if ent is None:
        ent = Entreprise(
            id=entreprise_id,
            raison_sociale=raison,
            siret=f"{entreprise_id:014d}",
            is_demo=False,
        )
        db.add(ent)
        db.commit()
    return ent


def test_charger_machines_actives_retourne_parc_reel_pas_mark_andy_2200():
    """Le tenant demo a 3 machines reelles (P5, Daco, Atelier 2). On NE
    DOIT PAS voir "Mark Andy 2200" (catalogue MachineImprimerie)."""
    with SessionLocal() as db:
        machines = charger_machines_actives(db, DEMO_ENTREPRISE_ID)
    noms = sorted(m.nom for m in machines)
    assert noms == [
        "Atelier 2 (vieille presse)",
        "Daco D250 ligne finition",
        "Mark Andy P5",
    ], f"Parc demo attendu (P5/Daco/Atelier 2), obtenu : {noms}"
    # Anti-regression explicite vs le bug B3a corrige : pas de catalogue
    # MachineImprimerie.
    assert "Mark Andy 2200" not in noms


def test_vitesse_pratique_derivee_de_vitesse_moyenne_divisee_60():
    """B3a : vitesse_pratique_m_min = round(vitesse_moyenne_m_h / 60).
    Une seule vitesse reelle, partagee avec cost_engine (SACRED V1a)."""
    with SessionLocal() as db:
        machines = charger_machines_actives(db, DEMO_ENTREPRISE_ID)
    par_nom = {m.nom: m.vitesse_pratique_m_min for m in machines}
    # Cf. seeds/machine.csv : vitesse_moyenne_m_h = 6000/3500/4500
    assert par_nom["Mark Andy P5"] == 100  # 6000 / 60
    assert par_nom["Daco D250 ligne finition"] == 58  # 3500 / 60 = 58.33 -> 58
    assert par_nom["Atelier 2 (vieille presse)"] == 75  # 4500 / 60


def test_mapping_champs_optim_b1_b2():
    """Les champs B1/B2 sont correctement mappes depuis Machine."""
    with SessionLocal() as db:
        machines = charger_machines_actives(db, DEMO_ENTREPRISE_ID)
    p5 = next(m for m in machines if m.nom == "Mark Andy P5")
    # Mark Andy P5 dans le seed : laize=330, nb_groupes_couleurs=8,
    # nb_postes_decoupe=1 (server_default B1), options=[] (server_default B1).
    assert p5.laize_utile_mm == 330.0
    assert p5.nb_groupes_couleurs == 8
    assert p5.nb_postes_decoupe == 1
    assert p5.options == []
    # Daco D250 a nb_groupes_couleurs NULL (ligne finition, pas une presse)
    # -> mappe a 0 (filtre dur capacite couleurs exclura des qu'on demande
    # au moins une couleur).
    daco = next(m for m in machines if m.nom.startswith("Daco"))
    assert daco.nb_groupes_couleurs == 0


def test_laize_utile_fallback_sur_laize_max_si_null():
    """Si `laize_utile_mm` est NULL (nouveau tenant pas configure B2),
    fallback sur `laize_max_mm` (NOT NULL en BDD)."""
    with SessionLocal() as db:
        _ensure_tenant(db, 99, "Tenant test B3a")
        m = Machine(
            entreprise_id=99,
            nom="TEST B3a sans laize_utile",
            laize_max_mm=Decimal("420.00"),
            laize_utile_mm=None,  # explicitement NULL
            vitesse_moyenne_m_h=4800,
            actif=True,
        )
        db.add(m)
        db.commit()
        try:
            machines = charger_machines_actives(db, 99)
            assert len(machines) == 1
            assert machines[0].laize_utile_mm == 420.0  # fallback sur laize_max
        finally:
            db.delete(m)
            db.commit()


def test_machine_sans_vitesse_moyenne_est_ecartee():
    """Une machine sans `vitesse_moyenne_m_h` (NULL ou <= 0) est
    silencieusement exclue : le moteur a besoin d'une vitesse pour scorer."""
    with SessionLocal() as db:
        _ensure_tenant(db, 99, "Tenant test B3a")
        m_sans = Machine(
            entreprise_id=99,
            nom="TEST B3a sans vitesse",
            laize_max_mm=Decimal("330.00"),
            vitesse_moyenne_m_h=None,  # explicitement NULL
            actif=True,
        )
        db.add(m_sans)
        db.commit()
        try:
            machines = charger_machines_actives(db, 99)
            noms = [m.nom for m in machines]
            assert "TEST B3a sans vitesse" not in noms
        finally:
            db.delete(m_sans)
            db.commit()


def test_scope_multi_tenant_strict():
    """`charger_machines_actives(entreprise_id=A)` ne retourne JAMAIS
    les machines de l'entreprise B."""
    with SessionLocal() as db:
        _ensure_tenant(db, 42, "Tenant test B3a multi-tenant")
        m_b = Machine(
            entreprise_id=42,
            nom="TEST B3a machine tenant B",
            laize_max_mm=Decimal("330.00"),
            vitesse_moyenne_m_h=6000,
            actif=True,
        )
        db.add(m_b)
        db.commit()
        try:
            # Tenant demo (1) ne voit pas la machine du tenant 42.
            machines_demo = charger_machines_actives(db, DEMO_ENTREPRISE_ID)
            assert "TEST B3a machine tenant B" not in [
                m.nom for m in machines_demo
            ]
            # Tenant 42 voit sa machine.
            machines_b = charger_machines_actives(db, 42)
            assert any(
                m.nom == "TEST B3a machine tenant B" for m in machines_b
            )
        finally:
            db.delete(m_b)
            db.commit()


def test_machine_inactive_est_ecartee():
    """Filtre `actif=True` : les machines en soft-delete ne remontent pas."""
    with SessionLocal() as db:
        _ensure_tenant(db, 99, "Tenant test B3a")
        m_inactif = Machine(
            entreprise_id=99,
            nom="TEST B3a machine inactive",
            laize_max_mm=Decimal("330.00"),
            vitesse_moyenne_m_h=6000,
            actif=False,  # SOFT DELETE
        )
        db.add(m_inactif)
        db.commit()
        try:
            machines = charger_machines_actives(db, 99)
            assert "TEST B3a machine inactive" not in [m.nom for m in machines]
        finally:
            db.delete(m_inactif)
            db.commit()
