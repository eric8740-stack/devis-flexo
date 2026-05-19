"""Tests suppression filtre effet banane (Brief #28 commit 2).

Couvre :
  - Les petits cylindres (≤ 80 dents) apparaissent désormais dans les
    candidats (auparavant exclus par le filtre dur effet banane).
  - Les petits cylindres acceptent les variantes multi-poses laize
    (le cas qui bloquait avant le brief).
  - Aucune pénalité de score n'est appliquée pour petit cylindre — le
    score reflète uniquement la qualité d'optimisation matière/intervalles.
  - Le champ `petit_cylindre: bool` est exposé dans la réponse pour
    permettre le badge UI informationnel.
"""
from fastapi.testclient import TestClient

from app.main import app
from tests.test_optimisation_router import (
    _onboard_tenant_minimal,
    cleanup_and_onboard,  # noqa: F401
)

client = TestClient(app)


def _post_optim_format(largeur: int, hauteur: int) -> dict:
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {
                "hauteur_mm": hauteur,
                "largeur_mm": largeur,
                "rayon_angles_mm": 2.0,
                "forme_courbe": False,
            },
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_petits_cylindres_apparaissent_dans_candidats(cleanup_and_onboard):  # noqa: ARG001
    """Cyl 80 dents (254 mm) + plaque large (laize 200) : auparavant exclu
    par effet banane (Z mini > 254). Désormais : présent avec badge."""
    _onboard_tenant_minimal()
    body = _post_optim_format(largeur=200, hauteur=50)
    petits = [c for c in body["configurations"] if c["petit_cylindre"]]
    assert len(petits) >= 1, (
        "Le moteur doit désormais retourner au moins 1 candidat petit cyl."
    )


def test_petits_cylindres_multi_poses_laize_proposes(cleanup_and_onboard):  # noqa: ARG001
    """Avec un petit cyl, les multi-poses laize (variante > 1) sont désormais
    proposées si elles tiennent dans laize_utile (plus de filtre banane).

    Cas : format 30×30, laize_utile 320, cyl 80 dents (254 mm) :
    variante_max = floor((320 + 2) / 32) = 10 poses laize possibles.
    Avant brief : exclu d'office. Après : présent et exploré."""
    _onboard_tenant_minimal()
    body = _post_optim_format(largeur=30, hauteur=30)
    petits = [c for c in body["configurations"] if c["petit_cylindre"]]
    assert len(petits) >= 1, "Cyl petit doit apparaître pour ce cas."
    # Au moins une variante avec nb_poses_laize >= 2 (multi-poses) sur petit
    # cyl. Auparavant impossible (banane bloquait).
    multi_poses = [p for p in petits if p["nb_poses_laize"] >= 2]
    assert len(multi_poses) >= 1, (
        f"Aucune variante multi-poses laize sur petit cyl. "
        f"Vérifier que le filtre banane est bien retiré. "
        f"Configs petits: {[(p['nb_poses_laize'], p['z_cylindre_mm']) for p in petits]}"
    )


def test_aucune_penalite_score_pour_petit_cylindre(cleanup_and_onboard):  # noqa: ARG001
    """À conditions équivalentes (mêmes intervalles, mêmes poses), un petit
    cyl ne reçoit pas de score "minoré". Le score reflète uniquement la
    qualité d'optimisation matière/intervalles — pas la taille du cyl.

    On vérifie ici plus simplement que les petits cyls avec score > 0
    existent (s'il y avait une pénalité, beaucoup auraient score = 0)."""
    _onboard_tenant_minimal()
    body = _post_optim_format(largeur=30, hauteur=30)
    petits = [c for c in body["configurations"] if c["petit_cylindre"]]
    assert len(petits) >= 1
    # Au moins un petit cyl avec score significatif (>0) → pas de pénalité.
    assert any(p["score"] > 0 for p in petits)


def test_champ_petit_cylindre_renvoye_dans_reponse(cleanup_and_onboard):  # noqa: ARG001
    """Tous les candidats portent le champ `petit_cylindre: bool`.
    True si nb_dents ≤ 80 (developpe_mm ≤ 254), False sinon."""
    _onboard_tenant_minimal()
    body = _post_optim_format(largeur=30, hauteur=30)
    for c in body["configurations"]:
        assert "petit_cylindre" in c
        assert isinstance(c["petit_cylindre"], bool)
        # Cohérence : True ssi developpe_mm ≤ 254.
        assert c["petit_cylindre"] == (c["z_cylindre_mm"] <= 254.0)
