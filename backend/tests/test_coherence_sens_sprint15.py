"""Tests du module coherence_sens — Sprint 15 Lot 4.

Couvre les 3 règles métier (inversion_cliche / ajustement_rebobineuse /
confirmation_client) + le fallback `sens_demande_du_devis()` qui lit
le sens d'enroulement du 1er lot du devis.

Aucun appel IA — logique pure sur la convention SE1-SE8 (rotation_se).
"""
from app.db import SessionLocal
from app.models import Devis, LotProduction
from app.services.coherence_sens import (
    diagnostiquer_coherence,
    face_du_sens,
    parse_se,
    sens_demande_du_devis,
)
from tests.test_lot_production_model import (
    _create_devis_minimal,
    _get_fk_ids,
    _onboard_if_needed,
)


# ---------------------------------------------------------------------------
# parse_se / face_du_sens
# ---------------------------------------------------------------------------


def test_parse_se_accepte_se1_a_se8():
    for n in range(1, 9):
        assert parse_se(f"SE{n}") == n


def test_parse_se_tolere_casse_et_espaces():
    assert parse_se(" se3 ") == 3
    assert parse_se("Se7") == 7


def test_parse_se_rejette_invalides():
    assert parse_se(None) is None
    assert parse_se("") is None
    assert parse_se("SE0") is None
    assert parse_se("SE9") is None
    assert parse_se("SE10") is None
    assert parse_se("XY1") is None


def test_face_du_sens_extension_vs_interieur():
    for n in (1, 2, 3, 4):
        assert face_du_sens(n) == "ext"
    for n in (5, 6, 7, 8):
        assert face_du_sens(n) == "int"


# ---------------------------------------------------------------------------
# diagnostiquer_coherence — règles métier
# ---------------------------------------------------------------------------


def test_diagnostic_info_manquante_retourne_none():
    """Si l'un des deux sens est None, le diagnostic ne s'engage pas."""
    diag = diagnostiquer_coherence(None, "SE1", "haut")
    assert diag["coherence_sens"] is None
    assert diag["action_correction_sens"] is None
    assert diag["message_alerte"] is None

    diag = diagnostiquer_coherence("SE1", None, "haut")
    assert diag["coherence_sens"] is None


def test_diagnostic_identique_renvoie_coherent_sans_alerte():
    diag = diagnostiquer_coherence("SE3", "SE3", "haut")
    assert diag["coherence_sens"] is True
    assert diag["action_correction_sens"] is None
    assert diag["message_alerte"] is None


def test_diagnostic_face_opposee_inversion_cliche():
    """Paires opposées : SE1↔SE5, SE2↔SE6, SE3↔SE7, SE4↔SE8."""
    for demande, detecte in (("SE1", "SE5"), ("SE2", "SE6"), ("SE3", "SE7"), ("SE4", "SE8")):
        diag = diagnostiquer_coherence(demande, detecte, "haut")
        assert diag["coherence_sens"] is False
        assert diag["action_correction_sens"] == "inversion_cliche"
        assert "inversion" in diag["message_alerte"].lower()
        assert demande in diag["message_alerte"]
        assert detecte in diag["message_alerte"]


def test_diagnostic_meme_face_rotation_differente_ajustement_rebobineuse():
    """Même face Ext (1-4), rotation différente → rebobineuse."""
    diag = diagnostiquer_coherence("SE1", "SE3", "haut")
    assert diag["coherence_sens"] is False
    assert diag["action_correction_sens"] == "ajustement_rebobineuse"
    assert "rebobineuse" in diag["message_alerte"].lower()


def test_diagnostic_meme_face_int_rotation_differente_ajustement():
    diag = diagnostiquer_coherence("SE6", "SE8", "haut")
    assert diag["coherence_sens"] is False
    assert diag["action_correction_sens"] == "ajustement_rebobineuse"


def test_diagnostic_confiance_faible_force_confirmation_client():
    """`niveau_confiance = 'faible'` prime sur la règle face/rotation —
    on demande à un humain de trancher au lieu d'auto-recommander."""
    # Cas qui aurait normalement été inversion_cliche
    diag = diagnostiquer_coherence("SE1", "SE5", "faible")
    assert diag["coherence_sens"] is False
    assert diag["action_correction_sens"] == "confirmation_client"
    assert "confiance" in diag["message_alerte"].lower()


def test_diagnostic_confiance_moyenne_ne_force_pas_confirmation():
    """Seul niveau_confiance="faible" trigger confirmation_client."""
    diag = diagnostiquer_coherence("SE1", "SE5", "moyen")
    assert diag["action_correction_sens"] == "inversion_cliche"

    diag = diagnostiquer_coherence("SE1", "SE5", "haut")
    assert diag["action_correction_sens"] == "inversion_cliche"


def test_diagnostic_sens_invalides_traites_comme_manquants():
    """Un input "SE9" ou autre → parse_se retourne None → diag None."""
    diag = diagnostiquer_coherence("SE9", "SE1", "haut")
    assert diag["coherence_sens"] is None
    diag = diagnostiquer_coherence("plop", "SE1", "haut")
    assert diag["coherence_sens"] is None


# ---------------------------------------------------------------------------
# sens_demande_du_devis — fallback depuis LotProduction
# ---------------------------------------------------------------------------


def test_sens_demande_du_devis_pas_de_lot_retourne_none():
    """Devis sans LotProduction → fallback None (mode mono-config legacy)."""
    with SessionLocal() as db:
        devis = _create_devis_minimal(db, numero="TEST-CS-DEV-NOLOT-001")
        db.commit()
        assert sens_demande_du_devis(db, devis.id) is None


def test_sens_demande_du_devis_lot_unique_renvoie_se_correspondant():
    """Devis avec 1 lot SE7 → renvoie 'SE7'."""
    _onboard_if_needed()
    with SessionLocal() as db:
        cyl_id, mach_id, mat_id = _get_fk_ids(db)
        devis = _create_devis_minimal(db, numero="TEST-CS-DEV-LOT-001")
        lot = LotProduction(
            devis_id=devis.id,
            entreprise_id=1,
            ordre=1,
            cylindre_id=cyl_id,
            machine_id=mach_id,
            nb_poses_dev=2,
            nb_poses_laize=3,
            sens_enroulement=7,
            quantite=1000,
            matiere_id=mat_id,
        )
        db.add(lot)
        db.commit()

        assert sens_demande_du_devis(db, devis.id) == "SE7"


def test_sens_demande_du_devis_plusieurs_lots_prend_ordre_minimal():
    """Avec plusieurs lots, le 1er (ordre ASC) sert de référence."""
    _onboard_if_needed()
    with SessionLocal() as db:
        cyl_id, mach_id, mat_id = _get_fk_ids(db)
        devis = _create_devis_minimal(db, numero="TEST-CS-DEV-MULTI-001")
        for ordre, sens in ((2, 5), (1, 2), (3, 8)):
            db.add(
                LotProduction(
                    devis_id=devis.id,
                    entreprise_id=1,
                    ordre=ordre,
                    cylindre_id=cyl_id,
                    machine_id=mach_id,
                    nb_poses_dev=2,
                    nb_poses_laize=3,
                    sens_enroulement=sens,
                    quantite=500,
                    matiere_id=mat_id,
                )
            )
        db.commit()

        # Le lot d'ordre 1 a sens 2 → "SE2"
        assert sens_demande_du_devis(db, devis.id) == "SE2"
