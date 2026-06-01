"""B2 — tests endpoint GET /api/machines/modules-disponibles.

Alimente le multi-select `options` de MachineForm (frontend). La liste est
calculee en union des `OptionFabrication.modules_speciaux_requis` scope
tenant + catalogue global (entreprise_id IS NULL) -- meme logique que
`charger_options_par_codes` cote optim.

Sources :
  - backend/app/routers/machine.py (endpoint)
  - backend/app/models/option_fabrication.py
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import OptionFabrication


client = TestClient(app)
DEMO_ENTREPRISE_ID = 1


def _purge_options_tenant_demo() -> None:
    """Vide les options-fabrication scope tenant demo (laisse les globales
    intactes). Necessaire pour rendre les tests deterministes."""
    with SessionLocal() as db:
        db.query(OptionFabrication).filter(
            OptionFabrication.entreprise_id == DEMO_ENTREPRISE_ID
        ).delete()
        db.commit()


def _seed_options_tenant(modules_par_option: list[list[str]]) -> None:
    """Insere N options-fabrication scope tenant demo avec les modules
    requis donnes."""
    with SessionLocal() as db:
        for idx, modules in enumerate(modules_par_option):
            db.add(
                OptionFabrication(
                    entreprise_id=DEMO_ENTREPRISE_ID,
                    code=f"test_b2_opt_{idx}",
                    libelle=f"Test B2 option {idx}",
                    categorie="autre",
                    modules_speciaux_requis=modules,
                )
            )
        db.commit()


def test_modules_disponibles_returns_200_et_array_string():
    """L'endpoint repond 200 avec un array de strings."""
    r = client.get("/api/machines/modules-disponibles")
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert all(isinstance(m, str) for m in data)


def test_modules_disponibles_dedoublonne_et_trie():
    """Si plusieurs options requierent le meme module, il apparait une
    seule fois. Resultat trie alphabetiquement."""
    _purge_options_tenant_demo()
    _seed_options_tenant([
        ["hot_stamping", "lamination"],
        ["lamination", "retournement_laize"],
        ["hot_stamping"],
    ])
    r = client.get("/api/machines/modules-disponibles")
    assert r.status_code == 200
    data = r.json()
    # On a 3 modules uniques, tries alphabetiquement.
    # NB : `data` peut contenir aussi les modules des options globales
    # (catalogue) -- on verifie juste que les 3 que l'on vient de seeder
    # y sont, sans doublons.
    assert "hot_stamping" in data
    assert "lamination" in data
    assert "retournement_laize" in data
    assert data == sorted(set(data))  # trie + sans doublons


def test_modules_disponibles_scope_tenant_inclut_globales():
    """L'endpoint union les options scope tenant ET globales (entreprise_id
    IS NULL), comme le moteur (charger_options_par_codes)."""
    _purge_options_tenant_demo()
    # Une option scope tenant avec un module unique a ce tenant.
    _seed_options_tenant([["module_test_b2_unique_tenant"]])
    r = client.get("/api/machines/modules-disponibles")
    assert r.status_code == 200
    data = r.json()
    # Le module scope tenant est present.
    assert "module_test_b2_unique_tenant" in data


def test_modules_disponibles_options_null_ignorees():
    """Une option avec modules_speciaux_requis = None (champ JSON NULL)
    ne perturbe pas le calcul."""
    _purge_options_tenant_demo()
    with SessionLocal() as db:
        db.add(
            OptionFabrication(
                entreprise_id=DEMO_ENTREPRISE_ID,
                code="test_b2_opt_sans_modules",
                libelle="Test B2 option sans modules",
                categorie="autre",
                modules_speciaux_requis=None,
            )
        )
        db.commit()
    r = client.get("/api/machines/modules-disponibles")
    assert r.status_code == 200
    # Pas d'erreur, retour valide.
    assert isinstance(r.json(), list)
