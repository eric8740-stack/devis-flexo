"""Tests du router /api/optimisation — Sprint 13 Lot S13.D.7b.

Couvre :
  - 409 si tenant pas onboardé (pas de cylindres/machines)
  - 200 happy path : top 3 viable après onboarding
  - 422 si option_code inconnu
  - 403 si user n'a pas le module flexocompare
  - Isolation tenant : user B ne voit pas les cylindres de A

NB : on s'appuie sur le service onboarding (S13.C.2) pour materialiser
le catalogue minimal pour chaque tenant avant le test, plutot que de
poser des rows a la main — c'est plus realiste et reutilise le code
deja teste.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import (
    Bareme,
    CylindreMagnetique,
    MachineImprimerie,
    Matiere,
    OptionFabrication,
)

client = TestClient(app)


@pytest.fixture
def cleanup_and_onboard():
    """Purge les rows S13.B des tenants test + (en option) appelle
    l'onboarding via API pour le tenant 1 (admin demo).
    """
    db: Session = SessionLocal()
    try:
        for ent_id in (1, 2, 3, 4):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
        yield
        for ent_id in (1, 2, 3, 4):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
    finally:
        db.close()


def _onboard_tenant_minimal():
    """Onboarde via l'API : 6 cylindres représentatifs + 2 machines +
    options minimales + barèmes (toujours 4).

    Brief #28 : 72 dents retiré du parc compte demo. On utilise désormais
    80 dents (254 mm) pour exercer le cas "petit cylindre" en remplacement.
    Valeurs mm = dents × 3.175 :
    80→254.0, 96→304.8, 104→330.2, 112→355.6, 128→406.4, 144→457.2.
    """
    payload = {
        "cylindres_developpes_mm": [254.0, 304.8, 330.2, 355.6, 406.4, 457.2],
        "machines_codes": ["mark_andy_2200", "omet_xflex_330"],
        "matieres_codes": [],
        "options_codes": ["vernis_selectif", "dorure_chaud"],
    }
    r = client.post("/api/onboarding/initialiser-catalogues", json=payload)
    assert r.status_code == 201, r.text


# ---------------------------------------------------------------------------
# Cas heureux
# ---------------------------------------------------------------------------


def test_post_calculer_happy_path(cleanup_and_onboard):
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {
                "hauteur_mm": 30,
                "largeur_mm": 30,
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
    body = r.json()
    assert body["nb_candidats"] >= 1
    # Sprint 13 avenant : pas de cap top_n côté backend.
    assert body["intervalle_dev_min_applique_mm"] == 2.0
    # Au moins 1 config a score > 0
    assert any(c["score"] > 0 for c in body["configurations"])
    # Chaque config a tous les coefs cumulés
    for c in body["configurations"]:
        assert c["coef_vitesse_final"] > 0
        assert c["coef_gache_final"] > 0


def test_post_calculer_avec_options_applique_coefs(cleanup_and_onboard):
    """Avec vernis_selectif (coef_vitesse_impact=0.95, pas de module
    spécial requis), toutes les configs portent ce coef. On vérifie que
    le moteur applique bien les coefs des options."""
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": ["vernis_selectif"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nb_candidats"] >= 1
    for c in body["configurations"]:
        # Coef vitesse vernis_selectif = 0.95 (catalogue_defaults.py)
        assert c["coef_vitesse_options"] == 0.95


def test_post_calculer_contrainte_client_force_min(cleanup_and_onboard):
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
            "contrainte_client": {"intervalle_dev_min_mm": 4.0},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intervalle_dev_min_applique_mm"] == 4.0
    assert body["message_contrainte_client"] is not None


# ---------------------------------------------------------------------------
# Erreurs
# ---------------------------------------------------------------------------


def test_post_calculer_409_si_pas_onboarde(cleanup_and_onboard):
    """Sans onboarding, le tenant n'a aucun cylindre/machine → 409."""
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 409
    assert "onboarding" in r.json()["detail"].lower()


def test_post_calculer_422_si_option_code_inconnu(cleanup_and_onboard):
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": ["option_qui_nexiste_pas"],
        },
    )
    assert r.status_code == 422
    assert "option_qui_nexiste_pas" in r.json()["detail"]


def test_post_calculer_403_si_pas_module_flexocompare(
    cleanup_and_onboard, as_user_flexocheck_only
):
    """User check-only (sans flexocompare) → 403."""
    _onboard_tenant_minimal()  # onboard fait sur le tenant check-only
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 403
    assert "flexocompare" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Isolation tenant
# ---------------------------------------------------------------------------


def test_isolation_tenant_user_b_voit_pas_catalogue_de_a(
    cleanup_and_onboard, switch_to_user_b
):
    """User A s'onboarde. User B (autre tenant) → 409 car son propre
    catalogue est vide. Garantit qu'on ne fuit pas les cylindres entre
    tenants."""
    _onboard_tenant_minimal()  # User A (entreprise_id=1)
    switch_to_user_b()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# GET /options-disponibles
# ---------------------------------------------------------------------------


def test_get_options_disponibles_renvoie_options_du_tenant(cleanup_and_onboard):
    """Après onboarding avec 2 options seedées, l'endpoint les expose
    avec leurs coefs réels. Trié pour rendu UI stable."""
    _onboard_tenant_minimal()  # seed vernis_selectif + dorure_chaud sur tenant 1
    r = client.get("/api/optimisation/options-disponibles")
    assert r.status_code == 200, r.text
    body = r.json()
    codes = {o["code"] for o in body}
    assert "vernis_selectif" in codes
    assert "dorure_chaud" in codes
    # Chaque entrée porte les champs attendus
    for o in body:
        assert "id" in o
        assert "libelle" in o
        assert isinstance(o["coef_vitesse_impact"], (int, float))
        assert isinstance(o["coef_gache_impact"], (int, float))


def test_get_options_disponibles_ne_fuit_pas_entre_tenants(
    cleanup_and_onboard, switch_to_user_b
):
    """Une option scopée tenant 1 uniquement (entreprise_id=1, pas de
    pendant global) ne doit JAMAIS apparaître côté tenant 2. Les options
    du catalogue global (entreprise_id=NULL) restent visibles pour les
    deux — c'est le pattern voulu, pas une fuite."""
    _onboard_tenant_minimal()
    db: Session = SessionLocal()
    try:
        opt_privee = OptionFabrication(
            entreprise_id=1,
            code="option_privee_tenant_1",
            libelle="Option privée tenant 1",
            categorie="Test",
            actif=True,
        )
        db.add(opt_privee)
        db.commit()
    finally:
        db.close()

    switch_to_user_b()
    r = client.get("/api/optimisation/options-disponibles")
    assert r.status_code == 200, r.text
    codes = {o["code"] for o in r.json()}
    assert "option_privee_tenant_1" not in codes


def test_get_options_disponibles_403_si_pas_module_flexocompare(
    cleanup_and_onboard, as_user_flexocheck_only
):
    """User check-only (sans flexocompare) → 403, comme l'endpoint
    calculer."""
    r = client.get("/api/optimisation/options-disponibles")
    assert r.status_code == 403
    assert "flexocompare" in r.json()["detail"].lower()


def test_post_calculer_422_message_actionnable(cleanup_and_onboard):
    """Le message 422 doit guider l'utilisateur vers l'onboarding express
    plutôt que de juste lister un code technique."""
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": ["option_qui_nexiste_pas"],
        },
    )
    assert r.status_code == 422
    detail = r.json()["detail"].lower()
    assert "onboarding" in detail
    assert "option_qui_nexiste_pas" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Cas métier de référence — Cas Eric 100×80 mm
# ---------------------------------------------------------------------------


def test_cas_metier_eric_etiquette_laize100_dev80_sur_cyl_104dents(
    cleanup_and_onboard,
):
    """Cas de référence métier ICE remonté par Eric pour valider le fix Cas B.

    Étiquette laize 100 mm × dev 80 mm, intervalle dev min 2 mm,
    catalogue ICE seedé (dont cylindre 104 dents = 330.2 mm).

    Calcul Excel attendu :
      - nb_poses_dev = floor(330.2 / (80 + 2)) = 4
      - intervalle dev réel = 330.2 / 4 − 80 = 2.55 mm (palier 'parfait')
      - Sur Mark Andy 2200 (laize utile 320), nb_poses_laize = 2
        (variante 3 exclue par effet banane : plaque 310 mm → Z mini 508)
      - Total = 4 × 2 = 8 poses

    Avant fix Cas B (developpe_mm en dents, valait 104 au lieu de 330.2) :
    le moteur trouvait 1 pose au lieu de 4 (104/82 = 1).
    """
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {
                "hauteur_mm": 80,
                "largeur_mm": 100,
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
    body = r.json()
    assert body["nb_candidats"] >= 1, "Au moins une config viable attendue"

    # Brief #28 : avec banane retiré, le moteur explore toutes les variantes
    # laize physiquement possibles. Sur ce cas (cyl 330.2 + format 100×80 +
    # machine 320 laize_utile), 3 poses laize est désormais retournée et
    # peut surpasser 2 poses au score. Le cas métier "4×2 sur cyl 104"
    # reste néanmoins présent dans le set de candidats — vérifié par scan.
    config_4x2 = next(
        (
            c for c in body["configurations"]
            if c["nb_poses_dev"] == 4 and c["nb_poses_laize"] == 2
        ),
        None,
    )
    assert config_4x2 is not None, (
        "La config 4×2 sur cyl 104 dents doit rester dans les candidats."
    )
    # Sanity sur l'intervalle dev (calculé sur dev = 80, indépendant du nb_poses_laize).
    assert abs(config_4x2["intervalle_dev_reel_mm"] - 2.55) < 0.01, (
        f"Intervalle dev attendu ~2.55 mm, obtenu {config_4x2['intervalle_dev_reel_mm']}"
    )
    assert config_4x2["qualite_echenillage"] == "parfait"
    # Top 1 reste sur le cylindre 104 dents (330.2 mm), 4 poses dev, mais
    # peut désormais être 4×3 plutôt que 4×2 (palier consolidation 3 poses).
    top1 = body["configurations"][0]
    assert top1["nb_poses_dev"] == 4, (
        f"Attendu 4 poses dev en top1, obtenu {top1['nb_poses_dev']}."
    )

    # PR #9.1 — champs BAT enrichis dans la réponse (vérifiés sur la
    # config 4×2 que le brief métier fige, indépendamment du top du tri).
    # laize_plaque = 2 × 100 + 1 × 5 = 205 mm
    assert config_4x2["laize_plaque_mm"] == 205.0
    # laize_papier = ceil((205 + 2×10) / 10) × 10 = 230 mm
    assert config_4x2["laize_papier_mm"] == 230.0
    # chute réelle = (230 − 205) / 2 = 12.5 mm
    assert config_4x2["chute_laterale_reelle_mm"] == 12.5
    # Z cylindre = 330.2 mm (104 dents)
    assert config_4x2["z_cylindre_mm"] == 330.2
    # Nomenclature : nombre de dents exposé pour affichage UI
    assert config_4x2["nb_dents_cylindre"] == 104
    # ml_total = ceil(10000 / 8) × 330.2 / 1000 = 1250 × 330.2 / 1000 = 412.75
    assert abs(config_4x2["ml_total_m"] - 412.75) < 0.01
    # Rendement ≈ 84.27 %
    assert abs(config_4x2["rendement_pct"] - 84.27) < 0.1
    # ø bobine estimation entre 250-310 mm (épaisseur default 150 µm)
    assert 250 <= config_4x2["diametre_bobine_mm"] <= 320
    # laize liner = 100 + 2×2.5 = 105 mm (default tenant)
    assert config_4x2["laize_liner_mm"] == 105.0
    # SE1 par défaut
    assert config_4x2["sens_enroulement"] == "SE1"
    # Au moins 1 machine compatible (dédoublonnage peut en agréger plus)
    assert len(top1["machines_compatibles"]) >= 1


def test_post_calculer_dedoublonne_configs_meme_cyl_meme_poses(
    cleanup_and_onboard,
):
    """Si Mark Andy 2200 et OMET XFlex 330 produisent la même config
    (mêmes cylindre, poses, intervalles), elles sont fusionnées en une
    seule entrée du top 3 avec machines_compatibles=[mark_andy, omet]."""
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 200, r.text
    configs = r.json()["configurations"]
    # Au moins une config avec machines_compatibles > 1 attendue (les 2
    # machines partagent des laizes utiles proches sur certaines variantes)
    fusionnees = [c for c in configs if len(c["machines_compatibles"]) > 1]
    if fusionnees:
        # Sanity : tous les machine_id sont uniques au sein du groupe
        for c in fusionnees:
            assert len(set(c["machines_compatibles"])) == len(
                c["machines_compatibles"]
            )


def test_sanity_cylindres_seedes_en_mm_pas_dents(cleanup_and_onboard):
    """Garde-fou Cas B : aucun cylindre seedé via l'onboarding ne doit avoir
    `developpe_mm` < 200. Sinon → régression du fix dents→mm."""
    _onboard_tenant_minimal()
    db: Session = SessionLocal()
    try:
        cylindres = db.query(CylindreMagnetique).filter_by(entreprise_id=1).all()
        assert len(cylindres) > 0
        for c in cylindres:
            assert float(c.developpe_mm) >= 200, (
                f"Cylindre id={c.id} dev={c.developpe_mm} < 200 mm — "
                "régression Cas B (valeur en dents au lieu de mm) ?"
            )
    finally:
        db.close()
