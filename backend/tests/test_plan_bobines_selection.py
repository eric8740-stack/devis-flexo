"""Tests — persistance du choix planificateur de bobines (finition).

Couvre :
- merge partiel de `payload_input` : autres clés (sens, couleurs, options)
  strictement préservées après écriture de `plan_bobines` ;
- restauration après reload (le GET expose le sous-objet sérialisé) ;
- forçage IMPOSE : refusé sans motif (422), accepté avec motif et
  `force_diametre=True` + `motif_forcage` persistés.

Pas de cost_engine ici — pure persistance JSONB.
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from tests.test_lot_production_model import _get_fk_ids, _onboard_if_needed


_client = TestClient(app)


def _creer_devis_mini_avec_payload_input() -> int:
    """Crée un devis minimal multi-lots et renvoie son id.

    On y injecte un `payload_input` riche pour vérifier que les autres
    clés survivent au merge ciblé du planificateur.
    """
    _onboard_if_needed()
    with SessionLocal() as db:
        cyl_id, mach_id, mat_id = _get_fk_ids(db)

    payload_input_riche = {
        "machine_id": mach_id,
        "format_etiquette_largeur_mm": 100,
        "format_etiquette_hauteur_mm": 80,
        "mode_calcul": "manuel",
        "source": "test_plan_bobines",
        "nb_lots": 1,
        "mandrin_mm": 76,
        "options_codes_etape4": ["vernis_selectif"],
        "sens_enroulement": 7,
        "nb_couleurs": {"impression": 4, "pantone": 0, "blanc": 0, "vernis": 0},
    }
    r = _client.post(
        "/api/devis",
        json={
            "payload_input": payload_input_riche,
            "payload_output": {
                "mode": "multi-lots",
                "prix_vente_ht_eur": "1000.00",
                "cout_revient_eur": "800.00",
            },
            "statut": "brouillon",
            "quantite_totale": 10_000,
            "lots": [
                {
                    "cylindre_id": cyl_id,
                    "machine_id": mach_id,
                    "nb_poses_dev": 2,
                    "nb_poses_laize": 3,
                    "sens_enroulement": 7,
                    "quantite": 10_000,
                    "matiere_id": mat_id,
                },
            ],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Merge partiel : autres clés payload_input préservées
# ---------------------------------------------------------------------------


def test_put_plan_bobines_preserve_autres_cles_payload_input():
    """Critique : écriture de plan_bobines ne perd PAS sens, couleurs, options."""
    devis_id = _creer_devis_mini_avec_payload_input()

    r = _client.put(
        f"/api/devis/{devis_id}/plan-bobines",
        json={
            "scenario": "B",
            "nb_bobine": 1667,
            "nb_bobines_total": 6,
            "politique_reliquat": "equilibrees",
        },
    )
    assert r.status_code == 200, r.text

    # Rechargement : le GET expose payload_input complet — toutes les clés
    # originales doivent être là, plus le nouveau plan_bobines.
    devis = _client.get(f"/api/devis/{devis_id}").json()
    pi = devis["payload_input"]
    assert pi["sens_enroulement"] == 7
    assert pi["nb_couleurs"] == {
        "impression": 4,
        "pantone": 0,
        "blanc": 0,
        "vernis": 0,
    }
    assert pi["options_codes_etape4"] == ["vernis_selectif"]
    assert pi["mandrin_mm"] == 76
    # Et la nouvelle clé est bien là.
    assert pi["plan_bobines"]["scenario"] == "B"
    assert pi["plan_bobines"]["nb_bobines_total"] == 6


def test_put_plan_bobines_remplace_selection_existante():
    """Re-PUT écrase l'ancienne sélection (pas d'accumulation)."""
    devis_id = _creer_devis_mini_avec_payload_input()
    _client.put(
        f"/api/devis/{devis_id}/plan-bobines",
        json={
            "scenario": "A",
            "nb_bobine": 2239,
            "nb_bobines_total": 6,
            "politique_reliquat": "pleines_plus_reliquat",
        },
    )
    _client.put(
        f"/api/devis/{devis_id}/plan-bobines",
        json={
            "scenario": "C_sup",
            "nb_bobine": 1667,
            "nb_bobines_total": 6,
            "politique_reliquat": "tomber_juste",
            "q_ajustee": 10_002,
        },
    )
    devis = _client.get(f"/api/devis/{devis_id}").json()
    pb = devis["payload_input"]["plan_bobines"]
    assert pb["scenario"] == "C_sup"
    assert pb["q_ajustee"] == 10_002


# ---------------------------------------------------------------------------
# Forçage IMPOSE : motif obligatoire si force_diametre=True
# ---------------------------------------------------------------------------


def test_forcage_impose_sans_motif_rejete_422():
    """`force_diametre=True` + motif vide → 422 Pydantic (traçabilité)."""
    devis_id = _creer_devis_mini_avec_payload_input()
    r = _client.put(
        f"/api/devis/{devis_id}/plan-bobines",
        json={
            "scenario": "IMPOSE",
            "nb_bobine": 3000,
            "nb_bobines_total": 6,
            "politique_reliquat": "pleines_plus_reliquat",
            "force_diametre": True,
            "motif_forcage": "",
        },
    )
    assert r.status_code == 422
    assert "motif" in r.text.lower()


def test_forcage_impose_avec_motif_persistance_ok():
    """`force_diametre=True` + motif rempli → 200 et persistance correcte."""
    devis_id = _creer_devis_mini_avec_payload_input()
    r = _client.put(
        f"/api/devis/{devis_id}/plan-bobines",
        json={
            "scenario": "IMPOSE",
            "nb_bobine": 3000,
            "nb_bobines_total": 6,
            "politique_reliquat": "pleines_plus_reliquat",
            "force_diametre": True,
            "motif_forcage": "Client accepte plusieurs sous-bobines en sortie atelier",
        },
    )
    assert r.status_code == 200, r.text
    devis = _client.get(f"/api/devis/{devis_id}").json()
    pb = devis["payload_input"]["plan_bobines"]
    assert pb["force_diametre"] is True
    assert "client" in pb["motif_forcage"].lower()


def test_sans_forcage_motif_optionnel():
    """force_diametre False / non fourni → motif non requis."""
    devis_id = _creer_devis_mini_avec_payload_input()
    r = _client.put(
        f"/api/devis/{devis_id}/plan-bobines",
        json={
            "scenario": "B",
            "nb_bobine": 1667,
            "nb_bobines_total": 6,
            "politique_reliquat": "equilibrees",
        },
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Scope tenant
# ---------------------------------------------------------------------------


def test_put_plan_bobines_404_si_devis_inexistant():
    r = _client.put(
        "/api/devis/999999/plan-bobines",
        json={
            "scenario": "A",
            "nb_bobine": 100,
            "nb_bobines_total": 6,
            "politique_reliquat": "pleines_plus_reliquat",
        },
    )
    assert r.status_code == 404
