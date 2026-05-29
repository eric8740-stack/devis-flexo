"""Fix regression rapport+plan disparaissent apres modification d'un devis.

Cause : update_devis (PUT /api/devis/{id}) appelait `_chiffrer_devis_multilots`
qui enrichissait payload_output (mode='multi-lots', details_par_lot[].details.
postes[7]), puis la boucle `for field, value in fields.items(): setattr(...)`
reappliquait le `payload_output` placeholder du body (envoye par le front du
flux optim etape 4 : `{mode: 'manuel', prix_vente_ht_eur: coutBrut, ...}`),
ecrasant les postes top-level. Cote front :
[DevisResultMultiLots.tsx:131-132] masquait l'integralite du bloc Rapport
de fabrication + PlanificateurBobines (rendu DANS le meme bloc).

Fix : pop conditionnel `payload_output` + `payload_input` du fields APRES
le recalcul `_chiffrer_devis_multilots` (option D : seulement quand lots
fournis -- DevisSaveBar mono-config legacy garde son contrat actuel).

Sources :
  - backend/scripts/dump_payload_output_post_put.py (repro 4 cas)
  - frontend/src/app/optimisation/_components/OptimisationChiffrage.tsx
    (envoie payload_output placeholder dans le PUT)
  - frontend/src/components/DevisSaveBar.tsx (mono-config legacy SANS lots,
    envoie payload_output = result moteur complet -- contrat preserve)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal
from app.main import app
from app.models import Devis
from tests.test_lot_production_model import _onboard_if_needed


client = TestClient(app)
DEMO_ENTREPRISE_ID = 1


def _fks_tenant_demo() -> tuple[int, int, int]:
    _onboard_if_needed()
    from app.models import CylindreMagnetique, MachineImprimerie, Matiere

    with SessionLocal() as db:
        machine = db.query(MachineImprimerie).filter_by(
            entreprise_id=DEMO_ENTREPRISE_ID, actif=True
        ).first()
        cyl = db.query(CylindreMagnetique).filter_by(
            entreprise_id=DEMO_ENTREPRISE_ID, actif=True
        ).first()
        mat = db.query(Matiere).filter_by(
            entreprise_id=DEMO_ENTREPRISE_ID, actif=True
        ).first()
        assert machine and cyl and mat, "seed demo incomplet"
        return machine.id, cyl.id, mat.id


def _payload_optim_lot(machine_id: int, cyl_id: int, mat_id: int) -> dict:
    return {
        "cylindre_id": cyl_id,
        "machine_id": machine_id,
        "nb_poses_dev": 2,
        "nb_poses_laize": 3,
        "sens_enroulement": 1,
        "quantite": 10000,
        "matiere_id": mat_id,
    }


def _payload_create_multilots(machine_id: int, cyl_id: int, mat_id: int) -> dict:
    return {
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
        "lots": [_payload_optim_lot(machine_id, cyl_id, mat_id)],
    }


def _purge_devis() -> None:
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.entreprise_id == DEMO_ENTREPRISE_ID).delete()
        db.commit()


def _get_po_struct(devis_id: int) -> dict[str, Any]:
    """Retourne le payload_output stocke."""
    with SessionLocal() as db:
        d = db.get(Devis, devis_id)
        assert d is not None
        return dict(d.payload_output or {})


def _assert_postes_present(po: dict[str, Any], where: str) -> None:
    """Assert que payload_output.details_par_lot[0].details.postes est un array
    de 7 PosteResult -- condition front pour afficher Rapport + Plan."""
    dpl = po.get("details_par_lot")
    assert isinstance(dpl, list) and len(dpl) >= 1, (
        f"[{where}] details_par_lot manquant ou vide : {po!r}"
    )
    details = dpl[0].get("details") or {}
    postes = details.get("postes")
    assert isinstance(postes, list), (
        f"[{where}] details.postes n'est pas un array : got {type(postes).__name__}"
    )
    assert len(postes) == 7, (
        f"[{where}] details.postes attendu len=7 (les 7 postes du moteur), got len={len(postes)}"
    )


def _create_multilots_devis() -> tuple[int, dict[str, Any]]:
    """POST /api/devis multi-lots. Retourne (devis_id, payload_output stocke)."""
    _purge_devis()
    machine_id, cyl_id, mat_id = _fks_tenant_demo()
    r = client.post(
        "/api/devis", json=_payload_create_multilots(machine_id, cyl_id, mat_id)
    )
    assert r.status_code == 201, r.text
    devis_id = r.json()["id"]
    po_create = _get_po_struct(devis_id)
    _assert_postes_present(po_create, "create")
    return devis_id, po_create


# ─────────────────────────────────────────────────────────────────────────────
# Cas B1 — PUT lots seuls (pas de payload_output dans body)
# ─────────────────────────────────────────────────────────────────────────────


def test_put_lots_seuls_preserve_postes():
    """PUT avec `lots` seuls (le body ne pose pas payload_output) : le serveur
    recalcule, postes restent un array de 7."""
    devis_id, po_create = _create_multilots_devis()
    machine_id, cyl_id, mat_id = _fks_tenant_demo()

    r = client.put(
        f"/api/devis/{devis_id}",
        json={
            "quantite_totale": 10000,
            "lots": [_payload_optim_lot(machine_id, cyl_id, mat_id)],
        },
    )
    assert r.status_code == 200, r.text
    po_after = _get_po_struct(devis_id)
    _assert_postes_present(po_after, "B1")
    # mode multi-lots preserve
    assert po_after.get("mode") == "multi-lots"


# ─────────────────────────────────────────────────────────────────────────────
# Cas B2 / B3 — PUT lots + payload_output (placeholder front optim)
#               Le fix doit IGNORER le placeholder et garder le recalcul.
# ─────────────────────────────────────────────────────────────────────────────


def test_put_lots_plus_payload_output_placeholder_preserve_postes():
    """Regression historique reproduite (B2 du script) : le PUT du flux optim
    etape 4 envoie un payload_output placeholder. Apres le fix, ce placeholder
    NE doit PAS ecraser le payload_output recalcule par l'aggregator."""
    devis_id, po_create = _create_multilots_devis()
    machine_id, cyl_id, mat_id = _fks_tenant_demo()

    r = client.put(
        f"/api/devis/{devis_id}",
        json={
            "quantite_totale": 10000,
            "lots": [_payload_optim_lot(machine_id, cyl_id, mat_id)],
            # Placeholder envoye par OptimisationChiffrage.tsx (mode='manuel',
            # prix=coutBrut preview, champs custom UI). Avant le fix : ecrasait
            # le mode='multi-lots' + details_par_lot enrichi -> rapport+plan
            # masques cote front.
            "payload_output": {
                "mode": "manuel",
                "prix_vente_ht_eur": "0.00",
                "cout_brut_ht_eur": "704.07",
                "cout_net_ht_eur": "704.07",
                "reduction_pct": "0",
                "nb_lots": 1,
            },
        },
    )
    assert r.status_code == 200, r.text
    po_after = _get_po_struct(devis_id)
    _assert_postes_present(po_after, "B2")
    # Cle d'audit : le payload_output stocke est celui du serveur, pas le
    # placeholder du body.
    assert po_after.get("mode") == "multi-lots", (
        f"Mode attendu 'multi-lots' (serveur), got {po_after.get('mode')!r}. "
        "Le payload_output du body a ecrase le recalcul."
    )
    # Le prix doit etre celui du recalcul, pas le '0.00' placeholder.
    prix = po_after.get("prix_vente_ht_eur")
    assert prix not in (None, "0.00", "0"), (
        f"prix_vente_ht_eur attendu != 0 (recalcul), got {prix!r}"
    )


def test_put_lots_plus_payload_input_et_output_preserve_postes():
    """B3 du script : le front envoie payload_input + payload_output + lots.
    Le fix pop les deux apres recalcul -> postes preserves."""
    devis_id, po_create = _create_multilots_devis()
    machine_id, cyl_id, mat_id = _fks_tenant_demo()

    r = client.put(
        f"/api/devis/{devis_id}",
        json={
            "quantite_totale": 10000,
            "lots": [_payload_optim_lot(machine_id, cyl_id, mat_id)],
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
        },
    )
    assert r.status_code == 200, r.text
    po_after = _get_po_struct(devis_id)
    _assert_postes_present(po_after, "B3")
    assert po_after.get("mode") == "multi-lots"


# ─────────────────────────────────────────────────────────────────────────────
# Cas B4 — PUT sans lots (reduction_pct seul) : aucun recalcul, payload_output
#          de creation preserve.
# ─────────────────────────────────────────────────────────────────────────────


def test_put_reduction_pct_seul_preserve_postes():
    """PUT sans `lots` n'invoque PAS le recalcul aggregator -> payload_output
    de creation reste intact (postes top-level deja la)."""
    devis_id, po_create = _create_multilots_devis()

    r = client.put(f"/api/devis/{devis_id}", json={"reduction_pct": 10})
    assert r.status_code == 200, r.text
    po_after = _get_po_struct(devis_id)
    _assert_postes_present(po_after, "B4")


# ─────────────────────────────────────────────────────────────────────────────
# Mono-config legacy (DevisSaveBar) : SANS lots, le client pose le payload_output
# = result moteur complet -> doit etre stocke tel quel (contrat preserve).
# ─────────────────────────────────────────────────────────────────────────────


def test_put_sans_lots_payload_output_du_client_est_conserve_legacy():
    """Cas DevisSaveBar mono-config : PUT sans `lots` mais avec payload_output
    custom (ex. result du moteur sprint 5 mono-cylindre). Comportement legacy
    preserve : le serveur n'a pas de recalcul a faire, le payload_output du
    body est stocke tel quel.
    """
    devis_id, _po_create = _create_multilots_devis()
    custom_po = {
        "mode": "manuel",
        "prix_vente_ht_eur": "1234.56",
        "champ_custom_legacy": "valeur-arbitraire-mono-config",
        "postes": [{"poste_numero": i, "libelle": f"Poste {i}",
                    "montant_eur": "0.00", "details": {}} for i in range(1, 8)],
    }
    r = client.put(
        f"/api/devis/{devis_id}",
        json={
            "payload_input": {
                "machine_id": 1,
                "format_etiquette_largeur_mm": 100,
                "format_etiquette_hauteur_mm": 80,
                "mode_calcul": "manuel",
            },
            "payload_output": custom_po,
        },
    )
    assert r.status_code == 200, r.text
    po_after = _get_po_struct(devis_id)
    # Mono-config legacy : pop conditionnel ne s'active pas (lots_in is None),
    # le payload_output du body est applique tel quel.
    assert po_after.get("prix_vente_ht_eur") == "1234.56", (
        f"Legacy mono-config : prix_vente_ht_eur du body attendu, "
        f"got {po_after.get('prix_vente_ht_eur')!r}"
    )
    assert po_after.get("champ_custom_legacy") == "valeur-arbitraire-mono-config"


# ─────────────────────────────────────────────────────────────────────────────
# Garde-fou explicite : un payload_output forge dans le body est IGNORE
# quand lots fournis (le serveur impose le sien).
# ─────────────────────────────────────────────────────────────────────────────


def test_put_lots_avec_payload_output_forge_est_ignore():
    """Quand lots est fourni, le serveur recalcule via aggregator et un
    payload_output forge dans le body (mode 'matching', prix factice) est
    IGNORE -- le serveur impose son recalcul."""
    devis_id, _ = _create_multilots_devis()
    machine_id, cyl_id, mat_id = _fks_tenant_demo()

    forge = {
        "mode": "matching",  # serait masque cote front car pas de postes top-level
        "prix_vente_ht_eur": "999999.99",
        "candidats": [{"z": 100, "nb_etiq_par_tour": 8, "postes": []}],
    }
    r = client.put(
        f"/api/devis/{devis_id}",
        json={
            "quantite_totale": 10000,
            "lots": [_payload_optim_lot(machine_id, cyl_id, mat_id)],
            "payload_output": forge,
        },
    )
    assert r.status_code == 200, r.text
    po_after = _get_po_struct(devis_id)
    # Le forge a ete IGNORE : on a bien le recalcul aggregator.
    _assert_postes_present(po_after, "forge")
    assert po_after.get("mode") == "multi-lots"
    prix = po_after.get("prix_vente_ht_eur")
    assert prix not in (None, "999999.99", "0.00"), (
        f"prix_vente_ht_eur attendu = recalcul aggregator, got {prix!r} "
        "(le forge du body a survecu -> fix casse)."
    )
