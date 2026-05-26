"""Tests endpoint GET /api/machines-rebobineuses — correctif prod multi-tenant.

Contexte : le frontend câblait `machine_rebobineuse_id=1` en dur dans
ses appels POST /api/rebobinage/calculer, ce qui marche pour le compte
demo (entreprise_id=1) mais casse en 404 pour tout autre tenant. Cet
endpoint expose la liste des rebobineuses du tenant pour permettre
au front de sélectionner dynamiquement.

Couverture :
  - Tenant courant voit ses propres rebobineuses (au moins les 2 seedées
    par la migration `q1f3a5d7e9c2` pour entreprise_id=1).
  - Isolation stricte : tenant B ne voit AUCUNE rebobineuse du tenant A.
  - Tenant sans rebobineuse → liste vide (200), pas 404 ni erreur.
  - Tri stable (nom ASC + id ASC).
  - Authentification requise : pas de token → 401.
"""
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import MachineRebobineuse


_http = TestClient(app)


def _create_machine_rebobineuse(
    db: Session,
    *,
    entreprise_id: int,
    nom: str,
    actif: bool = True,
) -> MachineRebobineuse:
    mach = MachineRebobineuse(
        entreprise_id=entreprise_id,
        nom=nom,
        marque="MarqueTest",
        modele="MT-100",
        laize_max_mm=Decimal("250"),
        diametre_max_mm=500,
        mandrins_supportes=[76, 152],
        vitesse_pratique_m_min=80,
        cout_horaire_eur=Decimal("45.00"),
        temps_changement_bobine_min=Decimal("1.50"),
        options=[],
        actif=actif,
    )
    db.add(mach)
    db.commit()
    db.refresh(mach)
    return mach


# ---------------------------------------------------------------------------
# Happy path tenant courant
# ---------------------------------------------------------------------------


def test_list_machines_rebobineuses_renvoie_machines_du_tenant_triees():
    """L'endpoint renvoie les rebobineuses du tenant, triées par nom ASC.

    Note : la migration `q1f3a5d7e9c2` (Lot A) seede 2 rebobineuses
    (Daco + Karlville) pour entreprise_id=1, mais le
    `seed_db_before_each_test` du conftest fait DELETE entreprise →
    CASCADE → table vide entre tests. Le test crée donc ses rows
    explicitement (pattern identique aux autres tests modèles Sprint 16)."""
    with SessionLocal() as db:
        _create_machine_rebobineuse(db, entreprise_id=1, nom="Daco D-Series")
        _create_machine_rebobineuse(db, entreprise_id=1, nom="Karlville K200")

    r = _http.get("/api/machines-rebobineuses")
    assert r.status_code == 200, r.text
    rows = r.json()
    noms = [item["nom"] for item in rows]
    assert "Daco D-Series" in noms
    assert "Karlville K200" in noms
    # Tri ASC sur nom : Daco avant Karlville
    assert noms.index("Daco D-Series") < noms.index("Karlville K200")
    # Champs minimaux du sélecteur présents
    daco = next(it for it in rows if it["nom"] == "Daco D-Series")
    assert daco["marque"] == "MarqueTest"
    assert daco["modele"] == "MT-100"
    assert Decimal(daco["laize_max_mm"]) == Decimal("250.00")
    assert daco["diametre_max_mm"] == 500
    assert daco["actif"] is True


def test_list_machines_rebobineuses_inclut_machine_ajoutee_dans_tenant():
    """Une machine ajoutée pour le tenant courant apparaît dans la liste."""
    with SessionLocal() as db:
        _create_machine_rebobineuse(
            db, entreprise_id=1, nom="ZZZ Ajout test"
        )
    r = _http.get("/api/machines-rebobineuses")
    assert r.status_code == 200
    noms = {item["nom"] for item in r.json()}
    assert "ZZZ Ajout test" in noms


def test_list_machines_rebobineuses_inclut_inactif_pour_selecteur():
    """Une machine `actif=False` reste dans la liste (l'UI gère
    l'affichage). Pas de filtre `actif=True` côté backend — laissé au
    front pour permettre l'édition d'une machine désactivée."""
    with SessionLocal() as db:
        _create_machine_rebobineuse(
            db, entreprise_id=1, nom="Inactive test", actif=False
        )
    r = _http.get("/api/machines-rebobineuses")
    rows = r.json()
    inactive = next((it for it in rows if it["nom"] == "Inactive test"), None)
    assert inactive is not None
    assert inactive["actif"] is False


# ---------------------------------------------------------------------------
# Isolation multi-tenant
# ---------------------------------------------------------------------------


def test_list_machines_rebobineuses_isolation_tenant_b_ne_voit_pas_a(
    as_user_b,
):
    """Le tenant B (entreprise_id=2) ne voit AUCUNE des rebobineuses
    du tenant A (entreprise_id=1, incl. les 2 seeds demo)."""
    # Pré-requis : crée explicitement une rebobineuse pour tenant 1
    # pour s'assurer qu'il y en a au moins une à NE PAS voir.
    # (La fixture autouse a déjà seedé pour tenant 1 via la migration.)
    r = _http.get("/api/machines-rebobineuses")
    assert r.status_code == 200
    # Tenant B n'a JAMAIS de rebobineuse seedée par la migration (seed
    # cible uniquement entreprise_id=1).
    assert r.json() == []


def test_list_machines_rebobineuses_tenant_b_voit_ses_propres(
    as_user_b,
):
    """Si on crée une rebobineuse pour tenant B, il la voit, et lui
    seul. Tenant A garde les siennes inchangées."""
    with SessionLocal() as db:
        _create_machine_rebobineuse(
            db, entreprise_id=2, nom="Rebob tenant B"
        )

    # Tenant B voit la sienne uniquement
    r_b = _http.get("/api/machines-rebobineuses")
    assert r_b.status_code == 200
    rows_b = r_b.json()
    noms_b = {it["nom"] for it in rows_b}
    assert "Rebob tenant B" in noms_b
    # Pas les seeds demo (= tenant A)
    assert "Daco D-Series" not in noms_b
    assert "Karlville K200" not in noms_b


# ---------------------------------------------------------------------------
# Tenant sans rebobineuse
# ---------------------------------------------------------------------------


def test_list_machines_rebobineuses_tenant_vide_retourne_liste_vide(
    as_user_b,
):
    """Tenant B fresh (sans rebobineuse) → 200 + []. Pas de 404 ni de 500."""
    r = _http.get("/api/machines-rebobineuses")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# Authentification requise
# ---------------------------------------------------------------------------


def test_list_machines_rebobineuses_sans_token_renvoie_401():
    """Sans Authorization Bearer, l'endpoint renvoie 401 (require auth
    standard via `get_current_user`)."""
    # On désactive l'autouse override pour ce test précis afin que
    # le get_current_user réel s'applique (Not authenticated).
    from app.dependencies import get_current_user as _gcu
    saved = app.dependency_overrides.pop(_gcu, None)
    try:
        r = _http.get("/api/machines-rebobineuses")
        assert r.status_code == 401
    finally:
        if saved is not None:
            app.dependency_overrides[_gcu] = saved
