"""Tests HTTP du router /api/tarif-poste (Sprint 9 v2 Lot 9c)."""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_tarifs_grouped_returns_6_postes_10_parametres():
    """6 postes seedés (1, 3, 4, 5, 6, 7), 10 paramètres au total."""
    response = client.get("/api/tarif-poste")
    assert response.status_code == 200
    data = response.json()
    postes = data["postes"]
    assert len(postes) == 6
    poste_numeros = [p["poste_numero"] for p in postes]
    assert poste_numeros == [1, 3, 4, 5, 6, 7]
    total_params = sum(len(p["parametres"]) for p in postes)
    assert total_params == 10
    # Le poste 3 doit contenir 4 paramètres (cliche + 3 outillage)
    poste_3 = next(p for p in postes if p["poste_numero"] == 3)
    assert len(poste_3["parametres"]) == 4
    assert poste_3["libelle_poste"] == "Outillage / Clichés"
    cles_p3 = [p["cle"] for p in poste_3["parametres"]]
    assert "cliche_prix_couleur" in cles_p3
    assert "outil_base_eur" in cles_p3
    assert "outil_par_trace_eur" in cles_p3
    assert "surcout_forme_speciale_pct" in cles_p3


def test_list_tarifs_grouped_intra_poste_sorted_by_ordre_affichage():
    response = client.get("/api/tarif-poste")
    poste_3 = next(
        p for p in response.json()["postes"] if p["poste_numero"] == 3
    )
    ordres = [p["ordre_affichage"] for p in poste_3["parametres"]]
    assert ordres == sorted(ordres)


def test_get_tarif_by_cle_existing_returns_200():
    response = client.get("/api/tarif-poste/cliche_prix_couleur")
    assert response.status_code == 200
    data = response.json()
    assert data["cle"] == "cliche_prix_couleur"
    assert float(data["valeur_defaut"]) == 45.0
    assert data["poste_numero"] == 3
    assert data["unite"] == "€/couleur"


def test_get_tarif_by_cle_missing_returns_404():
    response = client.get("/api/tarif-poste/cle_inexistante_xyz")
    assert response.status_code == 404


def test_put_tarif_modifies_valeur_within_bounds():
    response = client.put(
        "/api/tarif-poste/cliche_prix_couleur",
        json={"valeur_defaut": "50.00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["valeur_defaut"]) == 50.0


def test_put_tarif_below_min_returns_422():
    """cliche_prix_couleur a valeur_min=30 → mettre 10 doit échouer."""
    response = client.put(
        "/api/tarif-poste/cliche_prix_couleur",
        json={"valeur_defaut": "10.00"},
    )
    assert response.status_code == 422
    assert "valeur_min" in response.json()["detail"]


def test_put_tarif_above_max_returns_422():
    """cliche_prix_couleur a valeur_max=100 (mini-sprint bornes 04/05/2026)
    → mettre 150 doit échouer."""
    response = client.put(
        "/api/tarif-poste/cliche_prix_couleur",
        json={"valeur_defaut": "150.00"},
    )
    assert response.status_code == 422
    assert "valeur_max" in response.json()["detail"]


def test_put_tarif_at_widened_max_passes():
    """Bornes élargies (mini-sprint 04/05) : cliche_prix_couleur à 90 €
    (au-dessus de l'ancien max=60) doit passer 200."""
    response = client.put(
        "/api/tarif-poste/cliche_prix_couleur",
        json={"valeur_defaut": "90.00"},
    )
    assert response.status_code == 200
    assert float(response.json()["valeur_defaut"]) == 90.0


def test_put_tarif_missing_cle_returns_404():
    response = client.put(
        "/api/tarif-poste/cle_inexistante_xyz",
        json={"valeur_defaut": "12.34"},
    )
    assert response.status_code == 404


def test_put_tarif_extra_field_returns_422():
    """Le body PUT est strict (extra='forbid') — pas de champ accessoire."""
    response = client.put(
        "/api/tarif-poste/cliche_prix_couleur",
        json={"valeur_defaut": "50.00", "cle": "tentative_renommage"},
    )
    assert response.status_code == 422


def test_post_reset_poste_3_restores_seed_values():
    """Modifier outil_base_eur puis reset poste 3 → 200 € EXACT."""
    # Modifier
    r = client.put(
        "/api/tarif-poste/outil_base_eur", json={"valeur_defaut": "350.00"}
    )
    assert r.status_code == 200
    assert float(r.json()["valeur_defaut"]) == 350.0
    # Reset
    r = client.post("/api/tarif-poste/reset/3")
    assert r.status_code == 200
    body = r.json()
    assert body["poste_numero"] == 3
    assert body["n_reset"] == 4  # cliche + 3 outillage
    # Vérifier la valeur restaurée
    r = client.get("/api/tarif-poste/outil_base_eur")
    assert float(r.json()["valeur_defaut"]) == 200.0


def test_post_reset_invalid_poste_returns_422():
    """Path constraint ge=1 le=7."""
    response = client.post("/api/tarif-poste/reset/0")
    assert response.status_code == 422
    response = client.post("/api/tarif-poste/reset/8")
    assert response.status_code == 422


_PAYLOAD_V1B = {
    "complexe_id": 31,
    "laize_utile_mm": 220,
    "ml_total": 3000,
    "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
    "machine_id": 1,
    "outil_decoupe_existant": False,
    "nb_traces_complexite": 4,
    "forme_speciale": False,
    "forfaits_st": [{"partenaire_st_id": 1, "montant_eur": "50.00"}],
}


def test_put_tarif_outil_base_eur_no_longer_affects_engine_v1b_lot4a():
    """Phase 2 Lot 4a — TarifPoste.outil_base_eur est DÉPRÉCIÉE.

    Le moteur ne lit plus cette table pour P3 ; il lit `ConfigCouts.
    outil_base_eur`. Donc un PUT sur l'API TarifPoste n'a plus d'effet sur
    le résultat du calcul — V1b reste à 1 921,09 € malgré la modification.

    (Ancien contrat S9 v2 : V1b passait à 1 980,09 € après PUT 200→250.
    On documente ici la rupture volontaire du contrat avec la dépréciation.)
    """
    # PUT TarifPoste 200 → 250 (legacy, désormais sans effet moteur)
    r = client.put(
        "/api/tarif-poste/outil_base_eur", json={"valeur_defaut": "250.00"}
    )
    assert r.status_code == 200
    # V1b inchangé : le moteur lit ConfigCouts (200 € seedé démo)
    r = client.post("/api/cost/calculer", json=_PAYLOAD_V1B)
    assert r.status_code == 200
    prix_ht = Decimal(str(r.json()["prix_vente_ht_eur"]))
    assert prix_ht == Decimal("1921.09"), (
        f"V1b devrait rester EXACT à 1921.09 (TarifPoste déprécié), "
        f"obtenu {prix_ht}"
    )


def test_put_strategique_couts_outil_base_affects_engine_v1b_lot4a():
    """Phase 2 Lot 4a — contrat moderne : `PUT /api/strategique/couts` change
    V1b. Équivalent fonctionnel de l'ancien `PUT /api/tarif-poste/outil_base_eur`,
    avec la nouvelle source de vérité ConfigCouts."""
    r = client.put(
        "/api/strategique/couts", json={"outil_base_eur": 250.00}
    )
    assert r.status_code == 200, r.text
    assert float(r.json()["outil_base_eur"]) == 250.0
    # V1b reflète la nouvelle valeur ConfigCouts.
    r = client.post("/api/cost/calculer", json=_PAYLOAD_V1B)
    assert r.status_code == 200
    prix_ht = Decimal(str(r.json()["prix_vente_ht_eur"]))
    # Δ outil_base = +50 → Δ cout_revient = +50 → Δ prix_HT = +50 × 1.18
    # = +59 → cible 1 980,09 €.
    assert prix_ht == Decimal("1980.09")
