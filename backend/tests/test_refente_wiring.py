"""Lot back B — wiring refente au chiffrage (`_calculer_refente_lots`).

Vérifie qu'un lot « sans outil » génère une ligne refente ADDITIVE quand le
tenant a configuré le taux rebobineuse, et que tout est value-neutral sinon
(config 0, pas de rebobineuse, mode avec outil, 1 fille).
"""
from decimal import Decimal

import pytest

from app.crud.devis import _calculer_refente_lots
from app.db import SessionLocal
from app.models import (
    ConfigCouts,
    Devis,
    LotProduction,
    Machine,
    MachineRebobineuse,
)
from tests.test_lot_production_model import _onboard_if_needed

_PAYLOAD = {"format_etiquette_largeur_mm": 50, "format_etiquette_hauteur_mm": 40}


def _setup(taux: str, gache: str) -> int:
    """Onboard + rebobineuse active + config refente. Retourne machine_id presse."""
    _onboard_if_needed()
    with SessionLocal() as db:
        cfg = db.query(ConfigCouts).filter_by(entreprise_id=1).first()
        cfg.cout_exploitation_rebobineuse_eur_h = Decimal(taux)
        cfg.gache_raccord_pct = Decimal(gache)
        if (
            db.query(MachineRebobineuse).filter_by(entreprise_id=1, actif=True).first()
            is None
        ):
            db.add(
                MachineRebobineuse(
                    entreprise_id=1,
                    nom="Rebobineuse test",
                    laize_max_mm=Decimal("400.00"),
                    diametre_max_mm=300,
                    vitesse_pratique_m_min=200,
                    cout_horaire_eur=Decimal("50.00"),
                    temps_changement_bobine_min=Decimal("2.00"),
                    actif=True,
                )
            )
        machine = (
            db.query(Machine)
            .filter_by(entreprise_id=1, actif=True, type_machine="presse")
            .order_by(Machine.id)
            .first()
        )
        mid = machine.id
        db.commit()
        return mid


def _lot_sans_outil(machine_id: int, **over) -> LotProduction:
    base = dict(
        entreprise_id=1, ordre=1, cylindre_id=None, machine_id=machine_id,
        nb_poses_dev=1, nb_poses_laize=1, sens_enroulement=1, quantite=10_000,
        matiere_id=1, intervalle_laize_reel_mm=Decimal("3"),
        mode_sans_outil=True, laize_stock_mm=Decimal("250"),
    )
    base.update(over)
    return LotProduction(**base)


def test_refente_ligne_additive_quand_configure():
    mid = _setup(taux="60", gache="1")
    devis = Devis(entreprise_id=1, client_id=None)
    with SessionLocal() as db:
        res = _calculer_refente_lots(db, devis, [_lot_sans_outil(mid)], _PAYLOAD, 1)
    assert res is not None
    assert res["applique"] is True
    assert res["nb_lots_refendus"] == 1
    assert Decimal(res["cout_total_refente_eur"]) > 0
    ligne = res["lots"][0]
    assert ligne["nb_filles"] >= 2  # vraie refente
    assert ligne["nb_bobines_total"] >= ligne["nb_filles"]


def test_refente_none_si_config_neutre():
    """Taux + gâche = 0 → aucune ligne (value-neutral, sacrés intouchés)."""
    mid = _setup(taux="0", gache="0")
    devis = Devis(entreprise_id=1, client_id=None)
    with SessionLocal() as db:
        res = _calculer_refente_lots(db, devis, [_lot_sans_outil(mid)], _PAYLOAD, 1)
    assert res is None


def test_refente_none_si_lot_avec_outil():
    """Lot avec outil (mode_sans_outil=False) → pas de refente."""
    mid = _setup(taux="60", gache="1")
    devis = Devis(entreprise_id=1, client_id=None)
    lot = _lot_sans_outil(mid, mode_sans_outil=False, cylindre_id=1)
    with SessionLocal() as db:
        res = _calculer_refente_lots(db, devis, [lot], _PAYLOAD, 1)
    assert res is None


def test_refente_none_si_une_seule_fille():
    """nb_filles_force=1 → pas de slitting réel → pas de poste fantôme."""
    mid = _setup(taux="60", gache="1")
    devis = Devis(entreprise_id=1, client_id=None)
    lot = _lot_sans_outil(mid, nb_filles_force=1)
    with SessionLocal() as db:
        res = _calculer_refente_lots(db, devis, [lot], _PAYLOAD, 1)
    assert res is None
