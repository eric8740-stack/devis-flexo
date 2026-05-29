"""Dump du payload_output pour comparer mode 'optim multi-lots' vs 'manuel mono'.

But : repondre a l'hypothese front <-> back :
  - le front DevisResultMultiLots.tsx:131 lit `details.postes`
  - DevisOutputMatching n'a pas `postes` au top-level
  -> si le moteur renvoie matching, le bloc Rapport + PlanificateurBobines
     sont masques.

Ce script reproduit en local les 2 chemins de creation et dumpe la structure
du payload_output stocke -- aucune ecriture ailleurs que la dev DB seedee.
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
            assert u is not None, "Seed admin manquant"
            return u

    app.dependency_overrides[get_current_user] = _get_demo_admin


def _purge_devis(entreprise_id: int = 1) -> None:
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.entreprise_id == entreprise_id).delete()
        db.commit()


def _print_structure(label: str, payload_output: dict[str, Any]) -> None:
    print(f"\n{'=' * 70}\n== {label}\n{'=' * 70}")
    print(f"[top-level keys]    : {sorted(payload_output.keys())}")
    print(f"[mode]              : {payload_output.get('mode')!r}")
    print(f"[chiffrage_erreur]  : {payload_output.get('chiffrage_auto_erreur')!r}")
    print(f"[ht_total]          : {payload_output.get('prix_vente_ht_eur')!r}")
    dpl = payload_output.get("details_par_lot")
    print(f"[details_par_lot]   : type={type(dpl).__name__}, "
          f"len={len(dpl) if isinstance(dpl, list) else 'n/a'}")
    if isinstance(dpl, list) and dpl:
        d0 = dpl[0]
        print(f"[dpl[0] keys]       : {sorted(d0.keys())}")
        details = d0.get("details") or {}
        print(f"[dpl[0].details]    : keys={sorted(details.keys())}")
        print(f"[dpl[0].details.mode]: {details.get('mode')!r}")
        postes = details.get("postes")
        candidats = details.get("candidats")
        print(f"[postes top-level]  : type={type(postes).__name__}, "
              f"len={len(postes) if isinstance(postes, list) else 'n/a'}")
        print(f"[candidats]         : type={type(candidats).__name__}, "
              f"len={len(candidats) if isinstance(candidats, list) else 'n/a'}")
        if isinstance(candidats, list) and candidats:
            print(f"[candidats[0] keys] : {sorted(candidats[0].keys())}")
            cp = candidats[0].get("postes")
            print(f"[candidats[0].postes]: type={type(cp).__name__}, "
                  f"len={len(cp) if isinstance(cp, list) else 'n/a'}")


def main() -> None:
    run_seed()
    _override_demo_admin()
    client = TestClient(app)

    # ── Identifiants reels du seed demo ─────────────────────────────────
    from app.models import CylindreMagnetique, MachineImprimerie, Matiere

    with SessionLocal() as db:
        # Onboarding declenche cylindre/machine_imp/matiere s'ils manquent.
        machine = db.query(MachineImprimerie).filter_by(
            entreprise_id=1, actif=True
        ).first()
        cyl = db.query(CylindreMagnetique).filter_by(
            entreprise_id=1, actif=True
        ).first()
        mat = db.query(Matiere).filter_by(entreprise_id=1, actif=True).first()
        if not (machine and cyl and mat):
            # Onboarding paresseux comme dans les tests.
            from tests.test_lot_production_model import _onboard_if_needed
            _onboard_if_needed()
            machine = db.query(MachineImprimerie).filter_by(
                entreprise_id=1, actif=True
            ).first()
            cyl = db.query(CylindreMagnetique).filter_by(
                entreprise_id=1, actif=True
            ).first()
            mat = db.query(Matiere).filter_by(
                entreprise_id=1, actif=True
            ).first()
        machine_id, cyl_id, mat_id = machine.id, cyl.id, mat.id
        print(f"[seed] machine_imp_id={machine_id} cyl_id={cyl_id} matiere_id={mat_id}")

    # ── Cas A : flux optim multi-lots (data.lots non vide) ─────────────
    _purge_devis()
    payload_optim = {
        "payload_input": {
            "machine_id": machine_id,
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mode_calcul": "manuel",
        },
        "payload_output": {
            "mode": "manuel",
            "prix_vente_ht_eur": "0.00",
        },
        "statut": "brouillon",
        "quantite_totale": 10000,
        "lots": [
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": 10000,
                "matiere_id": mat_id,
            },
        ],
    }
    r = client.post("/api/devis", json=payload_optim)
    print(f"\n[POST /api/devis (optim multi-lots)] status = {r.status_code}")
    if r.status_code != 201:
        print(f"  detail: {r.text[:500]}")
        return

    with SessionLocal() as db:
        d = db.query(Devis).filter_by(numero=r.json()["numero"]).first()
        po_optim = dict(d.payload_output or {})
    _print_structure("CAS A — devis multi-lots (workflow optim)", po_optim)

    # ── Dump complet d'un details_par_lot[0] pour copy-paste eventuel ──
    if isinstance(po_optim.get("details_par_lot"), list) and po_optim["details_par_lot"]:
        print("\n[CAS A] details_par_lot[0] (dump JSON):")
        print(json.dumps(po_optim["details_par_lot"][0], indent=2, default=str)[:3000])


if __name__ == "__main__":
    main()
