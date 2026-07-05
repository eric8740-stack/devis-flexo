"""Audit 05/07/2026 — flux optimisation→devis : fallback nb_couleurs.

Le front optim (OptimisationChiffrage) pose les compteurs couleurs dans
`payload_input.nb_couleurs` SANS renseigner le champ racine `nb_couleurs`
du POST /api/devis ni du POST /api/devis/preview-couts. Avant le fix, ces
deux chemins ne lisaient que le champ racine → P2 Encres = 0 € (devis
sous-évalué ~25 % dans la repro, prix qui « sautait » à la première
réédition car le PUT, lui, relit payload_input depuis le fix E1).

Couvre :
  - POST : couleurs dans payload_input seul → même prix qu'avec le champ
    racine équivalent, et prix > payload sans couleurs.
  - POST : priorité au champ racine quand les deux sont présents.
  - preview-couts : couleurs dans payload_input seul → brut identique au
    champ racine équivalent.
  - Sans couleurs nulle part : P2 = 0 conservé (comportement Sprint 16).
"""

from decimal import Decimal

from app.db import SessionLocal
from fastapi.testclient import TestClient

from app.main import app
from app.models import Devis
from tests.test_creation_devis_calcule_prix_aggregate import (
    _payload_devis_1_lot,
)
from tests.test_nb_couleurs_propagation_sprint16 import (
    _assurer_grammage_premier_complexe,
)

client = TestClient(app)

COULEURS = {"impression": 4, "pantone": 1, "blanc": 0, "vernis": 0}


def _reset_devis() -> None:
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()


def _ht_post(payload: dict) -> Decimal:
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert "chiffrage_auto_erreur" not in body["payload_output"], body[
        "payload_output"
    ]
    return Decimal(body["ht_total_eur"])


def test_post_couleurs_dans_payload_input_seul_chiffre_encres():
    """Shape exacte du front optim : nb_couleurs dans payload_input,
    champ racine absent → même prix que le champ racine équivalent."""
    _reset_devis()
    _assurer_grammage_premier_complexe()

    # Référence : couleurs au champ racine (chemin Sprint 16, déjà correct).
    payload_racine = _payload_devis_1_lot()
    payload_racine["nb_couleurs"] = dict(COULEURS)
    ht_racine = _ht_post(payload_racine)

    # Shape front optim : couleurs uniquement dans payload_input.
    payload_optim = _payload_devis_1_lot()
    payload_optim["payload_input"]["nb_couleurs"] = dict(COULEURS)
    ht_optim = _ht_post(payload_optim)

    # Sans couleurs nulle part (comportement antérieur conservé).
    ht_sans = _ht_post(_payload_devis_1_lot())

    assert ht_optim == ht_racine, (
        f"payload_input.nb_couleurs ignoré au POST : {ht_optim} != {ht_racine}"
    )
    assert ht_optim > ht_sans, (
        "P2 Encres non chiffré depuis payload_input.nb_couleurs "
        f"({ht_optim} <= {ht_sans})"
    )


def test_post_champ_racine_prioritaire_sur_payload_input():
    """Les deux présents → le champ racine (body) gagne, comme au PUT."""
    _reset_devis()
    _assurer_grammage_premier_complexe()

    payload_reference = _payload_devis_1_lot()
    payload_reference["nb_couleurs"] = {
        "impression": 2,
        "pantone": 0,
        "blanc": 0,
        "vernis": 0,
    }
    ht_reference = _ht_post(payload_reference)

    payload_conflit = _payload_devis_1_lot()
    payload_conflit["nb_couleurs"] = {
        "impression": 2,
        "pantone": 0,
        "blanc": 0,
        "vernis": 0,
    }
    payload_conflit["payload_input"]["nb_couleurs"] = {
        "impression": 6,
        "pantone": 3,
        "blanc": 1,
        "vernis": 0,
    }
    ht_conflit = _ht_post(payload_conflit)

    assert ht_conflit == ht_reference, (
        "Le champ racine doit rester prioritaire sur payload_input "
        f"({ht_conflit} != {ht_reference})"
    )


def _brut_preview(payload: dict) -> Decimal:
    r = client.post("/api/devis/preview-couts", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chiffrage_auto_erreur"] is None, body
    assert body["cout_brut_ht_eur"] is not None, body
    return Decimal(str(body["cout_brut_ht_eur"]))


def test_preview_couts_couleurs_dans_payload_input_seul():
    """Preview live du flux optim : couleurs dans payload_input seul →
    brut identique au champ racine équivalent."""
    _reset_devis()
    _assurer_grammage_premier_complexe()

    base = _payload_devis_1_lot()
    preview_racine = {
        "payload_input": dict(base["payload_input"]),
        "lots": base["lots"],
        "nb_couleurs": dict(COULEURS),
    }
    brut_racine = _brut_preview(preview_racine)

    payload_input_optim = dict(base["payload_input"])
    payload_input_optim["nb_couleurs"] = dict(COULEURS)
    preview_optim = {
        "payload_input": payload_input_optim,
        "lots": base["lots"],
    }
    brut_optim = _brut_preview(preview_optim)

    preview_sans = {
        "payload_input": dict(base["payload_input"]),
        "lots": base["lots"],
    }
    brut_sans = _brut_preview(preview_sans)

    assert brut_optim == brut_racine, (
        f"preview-couts ignore payload_input.nb_couleurs : "
        f"{brut_optim} != {brut_racine}"
    )
    assert brut_optim > brut_sans
