"""Lot back A — pont cost : `_construire_devis_input_pour_lot` en mode sans outil.

Vérifie qu'un lot `mode_sans_outil` :
  - fait facturer P1 sur la laize STOCK (`laize_papier_mm == laize_stock_mm`) ;
  - calcule un `ml_total` cylinder-free (> 0, sans cylindre) ;
  - propage l'écho `mode_sans_outil` au DevisInput.
Et qu'un lot AVEC outil reste sur le chemin cylindre (non-régression).
"""
from decimal import Decimal

from app.crud.devis import _construire_devis_input_pour_lot
from app.db import SessionLocal
from app.models import CylindreMagnetique, LotProduction, Machine
from tests.test_lot_production_model import _onboard_if_needed

_PAYLOAD = {"format_etiquette_largeur_mm": 50, "format_etiquette_hauteur_mm": 40}


def _ids_demo() -> tuple[int, int]:
    """(machine_id, cylindre_id) actifs du tenant démo (ent 1).

    `_construire_devis_input_pour_lot` lit le 1er Complexe du tenant + la
    machine ; `matiere_id` n'est pas consommé (lot transient, non persisté →
    FK non enforce). L'onboarding peuple cylindres + matières (run_seed seul ne
    les crée pas)."""
    _onboard_if_needed()
    with SessionLocal() as db:
        m = (
            db.query(Machine)
            .filter_by(entreprise_id=1, actif=True, type_machine="presse")
            .order_by(Machine.id)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(CylindreMagnetique.id)
            .first()
        )
        assert m and cyl, "seed démo incomplet (machine/cylindre)"
        return m.id, cyl.id


def test_construire_devis_input_sans_outil_facture_laize_stock():
    machine_id, _ = _ids_demo()
    lot = LotProduction(
        entreprise_id=1,
        devis_id=1,
        ordre=1,
        cylindre_id=None,
        machine_id=machine_id,
        nb_poses_dev=1,
        nb_poses_laize=1,
        sens_enroulement=1,
        quantite=10_000,
        matiere_id=1,
        intervalle_laize_reel_mm=Decimal("3"),
        mode_sans_outil=True,
        laize_stock_mm=Decimal("250"),
    )
    with SessionLocal() as db:
        di = _construire_devis_input_pour_lot(
            lot, _PAYLOAD, db, entreprise_id=1
        )
    assert di.mode_sans_outil is True
    assert di.laize_stock_mm == Decimal("250")
    # P1 facture la laize STOCK entière (déchet inclus).
    assert di.laize_papier_mm == Decimal("250")
    # ml cylinder-free (> 0, sans cylindre).
    assert di.ml_total > 0


def test_construire_devis_input_avec_outil_non_regression():
    machine_id, cyl_id = _ids_demo()
    lot = LotProduction(
        entreprise_id=1,
        devis_id=1,
        ordre=1,
        cylindre_id=cyl_id,
        machine_id=machine_id,
        nb_poses_dev=2,
        nb_poses_laize=3,
        sens_enroulement=1,
        quantite=10_000,
        matiere_id=1,
        mode_sans_outil=False,
    )
    with SessionLocal() as db:
        di = _construire_devis_input_pour_lot(
            lot, _PAYLOAD, db, entreprise_id=1
        )
    assert di.mode_sans_outil is False
    assert di.laize_stock_mm is None
    assert di.ml_total > 0
