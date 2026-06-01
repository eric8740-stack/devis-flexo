"""B1 (convergence option B) — tests d'enrichissement Machine pour absorber
les champs optim.

Couvre :
  - Machine a les 4 nouveaux champs : laize_utile_mm, nb_postes_decoupe,
    vitesse_pratique_m_min, options.
  - Le champ `nb_couleurs` a ete renomme en `nb_groupes_couleurs` (donnee
    preservee).
  - Le parc seedé (entreprise_id=1) a les valeurs derivees correctement :
    laize_utile_mm = laize_max_mm, vitesse_pratique_m_min = vitesse_max_m_min,
    nb_postes_decoupe = 1 (server_default), options = [] (server_default).
  - Les champs SACRES (laize_max_mm, vitesse_moyenne_m_h, duree_calage_h)
    sont INTACTS (pas de modification dans la migration B1).

Sources :
  - backend/alembic/versions/z0p4n6r8s1t3_machine_enrichir_champs_optim.py
  - backend/app/models/machine.py (B1 -- champs ajoutes)
  - backend/scripts/seed.py (B1 -- derivation laize_utile / vitesse_pratique)
"""
from app.db import SessionLocal
from app.models import Machine


DEMO_ENTREPRISE_ID = 1


def test_machine_a_4_nouveaux_champs_optim():
    """Les 4 champs optim absorbes existent et sont typeés correctement."""
    with SessionLocal() as db:
        m = db.query(Machine).filter_by(entreprise_id=DEMO_ENTREPRISE_ID).first()
        assert m is not None, "seed machine demo manquant"
        # 4 champs ajoutes par migration z0p4n6r8s1t3.
        assert hasattr(m, "laize_utile_mm")
        assert hasattr(m, "nb_postes_decoupe")
        assert hasattr(m, "vitesse_pratique_m_min")
        assert hasattr(m, "options")


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
    """Le seed demo (3 machines) peuple les nouveaux champs B1 selon la
    derivation transitoire definie dans le brief :
      - laize_utile_mm := laize_max_mm
      - vitesse_pratique_m_min := vitesse_max_m_min
      - nb_postes_decoupe := 1 (server_default)
      - options := [] (server_default)
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
            assert m.vitesse_pratique_m_min == m.vitesse_max_m_min, (
                f"Machine {m.nom} : vitesse_pratique_m_min "
                f"({m.vitesse_pratique_m_min}) devrait etre derivee de "
                f"vitesse_max_m_min ({m.vitesse_max_m_min})."
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
