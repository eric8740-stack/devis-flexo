"""B1 (convergence option B) — tests d'enrichissement Machine pour absorber
les champs optim.

Couvre :
  - Machine a les champs : laize_utile_mm, nb_postes_decoupe, options.
    (vitesse_pratique_m_min retiree en B3b migration a1b2c3d4e5f6 --
    le moteur derive `vitesse_moyenne_m_h / 60` a la volee.)
  - Le champ `nb_couleurs` a ete renomme en `nb_groupes_couleurs` (donnee
    preservee).
  - Le parc seedé (entreprise_id=1) a les valeurs derivees correctement :
    laize_utile_mm = laize_max_mm, nb_postes_decoupe = 1 (server_default),
    options = [] (server_default).
  - Les champs SACRES (laize_max_mm, vitesse_moyenne_m_h, duree_calage_h)
    sont INTACTS (pas de modification dans la migration B1).

Sources :
  - backend/alembic/versions/z0p4n6r8s1t3_machine_enrichir_champs_optim.py
  - backend/alembic/versions/a1b2c3d4e5f6_drop_machine_vitesse_pratique_m_min.py (B3b)
  - backend/app/models/machine.py (B1 -- champs ajoutes ; B3b -- drop vitesse_pratique)
  - backend/scripts/seed.py (B1 -- derivation laize_utile)
"""
from app.db import SessionLocal
from app.models import Machine


DEMO_ENTREPRISE_ID = 1


def test_machine_a_champs_optim_b1():
    """Les champs optim B1 existent. `vitesse_pratique_m_min` a ete
    droppee en B3b (migration a1b2c3d4e5f6) -- le moteur derive a la
    volee."""
    with SessionLocal() as db:
        m = db.query(Machine).filter_by(entreprise_id=DEMO_ENTREPRISE_ID).first()
        assert m is not None, "seed machine demo manquant"
        assert hasattr(m, "laize_utile_mm")
        assert hasattr(m, "nb_postes_decoupe")
        assert hasattr(m, "options")
        # B3b : la colonne et l'attribut SQLAlchemy ont disparu.
        assert not hasattr(m, "vitesse_pratique_m_min")


def test_machine_nb_couleurs_renomme_en_nb_groupes_couleurs():
    """L'ancien attribut `nb_couleurs` a disparu, remplace par
    `nb_groupes_couleurs`. La donnee est preservee (P5=8, Atelier2=4)."""
    with SessionLocal() as db:
        m = db.query(Machine).filter_by(entreprise_id=DEMO_ENTREPRISE_ID).first()
        assert m is not None
        # Nouveau nom present.
        assert hasattr(m, "nb_groupes_couleurs")
        # Ancien nom retire du modele SQLAlchemy.
        assert not hasattr(m, "nb_couleurs")


def test_seed_demo_machines_ont_les_valeurs_derivees_b1():
    """Le seed demo (3 machines) peuple les champs B1 selon la derivation
    transitoire definie dans le brief :
      - laize_utile_mm := laize_max_mm
      - nb_postes_decoupe := 1 (server_default)
      - options := [] (server_default)

    NB : `vitesse_pratique_m_min` retiree en B3b (le moteur derive
    `vitesse_moyenne_m_h / 60` a la volee dans `optimisation_loader`).
    """
    with SessionLocal() as db:
        machines = (
            db.query(Machine)
            .filter_by(entreprise_id=DEMO_ENTREPRISE_ID)
            .order_by(Machine.id)
            .all()
        )
        assert len(machines) == 3, (
            f"3 machines demo attendues, got {len(machines)}"
        )
        for m in machines:
            assert m.laize_utile_mm == m.laize_max_mm, (
                f"Machine {m.nom} : laize_utile_mm ({m.laize_utile_mm}) "
                f"devrait etre derivee de laize_max_mm ({m.laize_max_mm})."
            )
            assert m.nb_postes_decoupe == 1, (
                f"Machine {m.nom} : nb_postes_decoupe attendu 1 "
                f"(server_default), got {m.nb_postes_decoupe}"
            )
            assert m.options == [], (
                f"Machine {m.nom} : options attendu [] (server_default), "
                f"got {m.options!r}"
            )


def test_sacred_machine_legacy_champs_intacts():
    """Les champs SACRES lus par cost_engine (cylindre_matcher,
    poste_5_roulage, poste_7_mo) sont INTACTS apres B1. Garde-fou
    benchmark V1a 1 449,09 EUR EXACT preservé."""
    with SessionLocal() as db:
        m = db.query(Machine).filter_by(nom="Mark Andy P5").first()
        assert m is not None, "Mark Andy P5 doit rester seedee (V1a sacred)"
        # Valeurs originales du seed Sprint 2 — pas touchees par B1.
        assert float(m.laize_max_mm) == 330.0
        assert m.vitesse_moyenne_m_h == 6000
        assert float(m.duree_calage_h) == 1.00
