"""SACRÉ — règle D1 nb_calages = 1 + nb_changements outil/cliché.

Fige la valeur € EXACTE du chemin multi-lots avec calage lié au MONTAGE
(Lot D1). Deux scénarios déterministes (mêmes FKs que le tripwire P0b :
Mark Andy 2200 laize_utile 320, 1er cylindre, 1re matière du tenant démo) :

  - 2 lots de MÊME montage, flags `changement_outil_cliche=False`
    → 1 SEUL calage (lot 2 dédupliqué) → total 1 125,22 €.
  - même devis, lot 2 `changement_outil_cliche=True` (vrai 2e jeu d'outil/
    clichés) → 2 calages → total 1 390,72 €.

Le delta 1 390,72 − 1 125,22 = 265,50 € = exactement 1 calage (225,00 €) ×
(1 + marge 0,18). Le lot 1 seul vaut 695,36 € (= tripwire P0b mono-lot),
cohérence garantie.

⚠️ Si une de ces valeurs change → STOP : soit régression du comptage calage,
soit dérive du seed/catalogue. AUCUN re-baseline sans validation explicite Eric.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import CylindreMagnetique, Devis, Machine, Matiere
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)
DEMO = 1

# === VALEURS SACRED FIGÉES (règle D1) ===
_TOTAL_SANS_CHANGEMENT: Decimal = Decimal("1125.22")  # 1 calage (lot 2 dédup)
_TOTAL_AVEC_CHANGEMENT: Decimal = Decimal("1390.72")  # 2 calages
_LAIZE_UTILE_MACHINE_SOURCE = Decimal("320.00")  # anti-drift fixture (Mark Andy 2200)


def _fks() -> tuple[int, int, int]:
    """(machine_id, cylindre_id, matiere_id) déterministes du tenant démo.
    Sélection machine PAR NOM (Mark Andy 2200), cohérente avec le tripwire P0b."""
    _onboard_if_needed()
    with SessionLocal() as db:
        machine = (
            db.query(Machine)
            .filter_by(entreprise_id=DEMO, nom="Mark Andy 2200", actif=True)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=DEMO, actif=True)
            .order_by(CylindreMagnetique.id)
            .first()
        )
        mat = (
            db.query(Matiere)
            .filter_by(entreprise_id=DEMO, actif=True)
            .order_by(Matiere.id)
            .first()
        )
        assert machine and cyl and mat, "seed/onboarding tenant démo incomplet"
        assert machine.laize_utile_mm == _LAIZE_UTILE_MACHINE_SOURCE, (
            f"DRIFT fixture : Mark Andy 2200 attendue laize_utile="
            f"{_LAIZE_UTILE_MACHINE_SOURCE}, obtenu {machine.laize_utile_mm}. "
            "Le sacred D1 serait figé sur un autre scénario — INVESTIGUER."
        )
        return machine.id, cyl.id, mat.id


def _lot(cyl_id: int, mach_id: int, mat_id: int, changement: bool = False) -> dict:
    return {
        "cylindre_id": cyl_id,
        "machine_id": mach_id,
        "nb_poses_dev": 2,
        "nb_poses_laize": 3,
        "sens_enroulement": 1,
        "quantite": 10_000,
        "matiere_id": mat_id,
        "changement_outil_cliche": changement,
    }


def _post_total(lots: list[dict]) -> Decimal:
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.entreprise_id == DEMO).delete()
        db.commit()
    payload = {
        "payload_input": {
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mode_calcul": "manuel",
            "machine_id": lots[0]["machine_id"],
        },
        "payload_output": {"mode": "manuel", "prix_vente_ht_eur": "0.00"},
        "statut": "brouillon",
        "quantite_totale": sum(lot["quantite"] for lot in lots),
        "lots": lots,
    }
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    po = r.json()["payload_output"]
    assert po.get("mode") == "multi-lots", (
        f"chiffrage multi-lots attendu, got {po.get('mode')!r} / "
        f"err={po.get('chiffrage_auto_erreur')!r}"
    )
    return Decimal(str(po["prix_vente_ht_eur"]))


def test_benchmark_sacred_d1_un_calage_sans_changement():
    """2 lots même montage, flags False → 1 calage → 1 125,22 € EXACT."""
    mach, cyl, mat = _fks()
    total = _post_total([_lot(cyl, mach, mat), _lot(cyl, mach, mat)])
    assert total == _TOTAL_SANS_CHANGEMENT, (
        f"REGRESSION SACRED D1 (1 calage) : attendu {_TOTAL_SANS_CHANGEMENT} €, "
        f"obtenu {total} €. AUCUN re-baseline sans validation Eric."
    )


def test_benchmark_sacred_d1_deux_calages_avec_changement():
    """2 lots, lot 2 changement_outil_cliche=True → 2 calages → 1 390,72 € EXACT."""
    mach, cyl, mat = _fks()
    total = _post_total(
        [_lot(cyl, mach, mat), _lot(cyl, mach, mat, changement=True)]
    )
    assert total == _TOTAL_AVEC_CHANGEMENT, (
        f"REGRESSION SACRED D1 (2 calages) : attendu {_TOTAL_AVEC_CHANGEMENT} €, "
        f"obtenu {total} €. AUCUN re-baseline sans validation Eric."
    )


def test_benchmark_sacred_d1_delta_egal_un_calage():
    """Garde de cohérence : le delta 2 calages − 1 calage = 1 calage × (1+marge)."""
    assert _TOTAL_AVEC_CHANGEMENT - _TOTAL_SANS_CHANGEMENT == Decimal("265.50")
