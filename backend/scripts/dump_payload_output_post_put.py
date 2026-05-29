"""Repro deterministe : la modification (PUT /api/devis/{id}) ecrase-t-elle
les `postes` du payload_output remplis a la creation ?

Scenario :
  1. POST /api/devis multi-lots -> postes top-level OK
  2. PUT /api/devis/{id} avec :
     - cas B1 : `lots` seuls (pas de payload_output) -> attendu OK
     - cas B2 : `lots` + payload_output (placeholder front) -> SUSPECT
     - cas B3 : `lots` + payload_input + payload_output minimal -> SUSPECT
     - cas B4 : pas de `lots`, juste reduction_pct -> attendu OK (pas de recalcul)
  3. Compare la structure de payload_output avant et apres chaque PUT.

NE TOUCHE PAS la dev DB autrement que via le seed + les CRUD officiels.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.dependencies import get_current_user
from app.main import app
from app.models import Devis, User
from scripts.seed import run_seed

DEMO_ADMIN_EMAIL = "admin@devis-flexo.fr"


def _override_demo_admin() -> None:
    def _get_demo_admin() -> User:
        with SessionLocal() as db:
            u = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first()
            assert u is not None
            return u
    app.dependency_overrides[get_current_user] = _get_demo_admin


def _purge_devis() -> None:
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()


def _structure(po: dict[str, Any]) -> dict[str, Any]:
    """Resume structurel du payload_output, focus sur les cles que lit le front."""
    dpl = po.get("details_par_lot")
    res = {
        "top_keys": sorted(po.keys()),
        "mode": po.get("mode"),
        "chiffrage_auto_erreur": po.get("chiffrage_auto_erreur"),
        "prix_vente_ht_eur": po.get("prix_vente_ht_eur"),
        "dpl_type": type(dpl).__name__,
        "dpl_len": (len(dpl) if isinstance(dpl, list) else None),
    }
    if isinstance(dpl, list) and dpl:
        d0 = dpl[0]
        details = d0.get("details") or {}
        postes = details.get("postes")
        candidats = details.get("candidats")
        res.update({
            "lot0_keys": sorted(d0.keys()),
            "lot0_details_keys": sorted(details.keys()),
            "lot0_details_mode": details.get("mode"),
            "postes_top_type": type(postes).__name__,
            "postes_top_len": (len(postes) if isinstance(postes, list) else None),
            "candidats_type": type(candidats).__name__,
            "candidats_len": (len(candidats) if isinstance(candidats, list) else None),
        })
    return res


def _diff(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Diff cle a cle entre 2 dicts plats."""
    lines = []
    keys = sorted(set(before) | set(after))
    for k in keys:
        b, a = before.get(k, "<absent>"), after.get(k, "<absent>")
        if b != a:
            lines.append(f"  {k:30s}: {b!r:<25s} -> {a!r}")
    return "\n".join(lines) or "  (identique)"


def main() -> None:
    run_seed()
    _override_demo_admin()
    client = TestClient(app)

    from app.models import CylindreMagnetique, MachineImprimerie, Matiere

    # Onboarding paresseux (comme dans les tests).
    from tests.test_lot_production_model import _onboard_if_needed
    _onboard_if_needed()

    with SessionLocal() as db:
        machine = db.query(MachineImprimerie).filter_by(
            entreprise_id=1, actif=True
        ).first()
        cyl = db.query(CylindreMagnetique).filter_by(
            entreprise_id=1, actif=True
        ).first()
        mat = db.query(Matiere).filter_by(entreprise_id=1, actif=True).first()
        machine_id, cyl_id, mat_id = machine.id, cyl.id, mat.id

    payload_input = {
        "machine_id": machine_id,
        "format_etiquette_largeur_mm": 100,
        "format_etiquette_hauteur_mm": 80,
        "mode_calcul": "manuel",
    }
    payload_output_placeholder = {
        "mode": "manuel",
        "prix_vente_ht_eur": "0.00",
    }
    base_lot = {
        "cylindre_id": cyl_id,
        "machine_id": machine_id,
        "nb_poses_dev": 2,
        "nb_poses_laize": 3,
        "sens_enroulement": 1,
        "quantite": 10000,
        "matiere_id": mat_id,
    }
    payload_create = {
        "payload_input": payload_input,
        "payload_output": payload_output_placeholder,
        "statut": "brouillon",
        "quantite_totale": 10000,
        "lots": [base_lot],
    }

    def run_case(label: str, put_body: dict[str, Any]) -> None:
        _purge_devis()
        # Step 1 : creation
        r = client.post("/api/devis", json=payload_create)
        assert r.status_code == 201, r.text
        numero = r.json()["numero"]
        with SessionLocal() as db:
            d = db.query(Devis).filter_by(numero=numero).first()
            po_before = dict(d.payload_output or {})
            devis_id = d.id
        struct_before = _structure(po_before)

        # Step 2 : modification
        r = client.put(f"/api/devis/{devis_id}", json=put_body)
        print(f"\n{'=' * 78}\n== {label}\n   PUT body keys: {sorted(put_body.keys())}\n"
              f"   HTTP {r.status_code}\n{'=' * 78}")
        if r.status_code >= 400:
            print(f"  detail: {r.text[:300]}")
            return
        with SessionLocal() as db:
            d = db.query(Devis).filter_by(id=devis_id).first()
            po_after = dict(d.payload_output or {})
        struct_after = _structure(po_after)

        print("\n[DIFF structure payload_output (avant -> apres)]")
        print(_diff(struct_before, struct_after))

    # ── Cas B1 : PUT avec lots seuls (pas de payload_output) ───────────
    run_case(
        "B1 — PUT avec lots seuls (sans payload_output dans body)",
        {"quantite_totale": 10000, "lots": [base_lot]},
    )

    # ── Cas B2 : PUT avec lots + payload_output placeholder ────────────
    run_case(
        "B2 — PUT avec lots + payload_output placeholder (suspect : front renvoie le PO original)",
        {
            "quantite_totale": 10000,
            "lots": [base_lot],
            "payload_output": payload_output_placeholder,
        },
    )

    # ── Cas B3 : PUT avec lots + payload_input + payload_output ────────
    run_case(
        "B3 — PUT avec lots + payload_input + payload_output (front renvoie tout)",
        {
            "quantite_totale": 10000,
            "lots": [base_lot],
            "payload_input": payload_input,
            "payload_output": payload_output_placeholder,
        },
    )

    # ── Cas B4 : PUT sans lots, juste reduction_pct ────────────────────
    run_case(
        "B4 — PUT reduction_pct seul (pas de recalcul)",
        {"reduction_pct": 10},
    )


if __name__ == "__main__":
    main()
