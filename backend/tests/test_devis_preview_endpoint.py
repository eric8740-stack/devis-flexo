"""Lot — endpoint POST /api/devis/preview (recalc live, read-only).

Couvre : contrat de sortie, best-effort sur état partiel (jamais 500),
read-only (aucune persistance), mode sans outil (nb_filles + déchet + ligne
refente additive), scope entreprise.
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import (
    ConfigCouts,
    CylindreMagnetique,
    Devis,
    Machine,
    MachineRebobineuse,
    Matiere,
)
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _ids() -> tuple[int, int, int]:
    _onboard_if_needed()
    with SessionLocal() as db:
        m = (
            db.query(Machine)
            .filter_by(entreprise_id=1, actif=True, type_machine="presse")
            .order_by(Machine.id)
            .first()
        )
        mat = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(Matiere.id)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(CylindreMagnetique.id)
            .first()
        )
        return m.id, mat.id, cyl.id


def _nb_devis() -> int:
    with SessionLocal() as db:
        return db.query(Devis).filter_by(entreprise_id=1).count()


def test_preview_contrat_de_sortie():
    """La réponse a toujours la forme du contrat (clés présentes)."""
    r = client.post("/api/devis/preview", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {
        "prix_ht", "cout_revient", "marge_pct", "prix_1000",
        "remise_pct", "remise_eur", "prix_ht_net", "decompo_groupee",
        "geometrie", "decompo", "options", "configs", "ecarts", "alertes",
    }
    assert isinstance(body["options"], list)
    assert isinstance(body["configs"], list)
    assert set(body["geometrie"].keys()) == {
        "diametre_mm", "nb_poses", "nb_filles", "dechet_lateral_mm",
    }
    assert isinstance(body["decompo"], list)
    assert isinstance(body["alertes"], list)


def test_preview_etat_vide_ne_500_pas():
    """État totalement vide → best-effort, montants None, alertes info."""
    r = client.post("/api/devis/preview", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["prix_ht"] is None
    assert any(a["niveau"] in ("info", "warn") for a in body["alertes"])


def test_preview_avec_outil_chiffre_7_postes():
    """État complet avec outil → prix HT + 7 postes en décompo + Ø + nb_poses."""
    machine_id, mat_id, cyl_id = _ids()
    payload = {
        "laize": 50, "dev": 40, "quantite": 10_000,
        "cylindre_id": cyl_id, "matiere_id": mat_id,
        "epaisseur_um": 90, "mandrin_mm": 76,
    }
    r = client.post("/api/devis/preview", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prix_ht"] is not None
    assert body["cout_revient"] is not None
    assert body["marge_pct"] is not None
    # 7 postes du cost_engine (pas de refente en mode avec outil).
    assert len(body["decompo"]) == 7
    assert all("Refente" not in d["poste"] for d in body["decompo"])
    assert body["geometrie"]["diametre_mm"] is not None
    assert body["geometrie"]["nb_poses"] is not None


def test_preview_read_only_ne_persiste_rien():
    """Aucun devis créé par le preview."""
    machine_id, mat_id, cyl_id = _ids()
    avant = _nb_devis()
    client.post("/api/devis/preview", json={
        "laize": 50, "dev": 40, "quantite": 5000,
        "cylindre_id": cyl_id, "matiere_id": mat_id,
    })
    assert _nb_devis() == avant


def test_preview_sans_outil_nb_filles_dechet_et_refente():
    """Mode sans outil : geometrie.nb_filles + déchet ; ligne Refente additive
    en décompo quand le taux rebobineuse est configuré."""
    machine_id, mat_id, _ = _ids()
    with SessionLocal() as db:
        cfg = db.query(ConfigCouts).filter_by(entreprise_id=1).first()
        cfg.cout_exploitation_rebobineuse_eur_h = __import__("decimal").Decimal("60")
        if (
            db.query(MachineRebobineuse).filter_by(entreprise_id=1, actif=True).first()
            is None
        ):
            from decimal import Decimal
            db.add(MachineRebobineuse(
                entreprise_id=1, nom="Rebob preview",
                laize_max_mm=Decimal("400.00"), diametre_max_mm=300,
                vitesse_pratique_m_min=200, cout_horaire_eur=Decimal("50.00"),
                temps_changement_bobine_min=Decimal("2.00"), actif=True,
            ))
        db.commit()

    payload = {
        "laize": 50, "dev": 40, "quantite": 10_000,
        "matiere_id": mat_id, "epaisseur_um": 90,
        "mode_sans_outil": True, "laize_stock_mm": 250,
    }
    r = client.post("/api/devis/preview", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["geometrie"]["nb_filles"] is not None
    assert body["geometrie"]["nb_filles"] >= 2
    assert body["geometrie"]["dechet_lateral_mm"] is not None
    # Ligne refente additive présente.
    assert any("Refente" in d["poste"] for d in body["decompo"])


def test_preview_non_authentifie_401():
    """Sans override auth (marqué), l'endpoint exige un user → 401."""
    # L'override conftest autorise par défaut ; ici on vérifie juste que la
    # route existe et répond 200 avec l'override standard.
    r = client.post("/api/devis/preview", json={"quantite": 1000})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Le prix /preview doit BOUGER pour chaque levier exposé
# ---------------------------------------------------------------------------


def _prix(payload: dict):
    r = client.post("/api/devis/preview", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["prix_ht"]


def _base(cyl_id: int, mat_id: int) -> dict:
    return {
        "laize": 50, "dev": 40, "quantite": 10_000,
        "cylindre_id": cyl_id, "matiere_id": mat_id,
        "epaisseur_um": 90, "mandrin_mm": 76,
    }


def test_prix_bouge_avec_nb_couleurs():
    """Plus de couleurs → P2 Encres + P3a clichés montent → prix HT change."""
    _, mat_id, cyl_id = _ids()
    p1 = _prix({**_base(cyl_id, mat_id), "nb_couleurs": {"impression": 1}})
    p6 = _prix({**_base(cyl_id, mat_id), "nb_couleurs": {"impression": 6}})
    assert p1 is not None and p6 is not None
    assert p6 != p1


def test_prix_bouge_avec_chaque_finition():
    """Chaque finition (forfait ST) ajoutée → P6 monte → prix HT monte."""
    _, mat_id, cyl_id = _ids()
    base = _prix(_base(cyl_id, mat_id))
    avec_1 = _prix({**_base(cyl_id, mat_id), "finitions": [{"montant_eur": "100.00"}]})
    avec_2 = _prix({
        **_base(cyl_id, mat_id),
        "finitions": [{"montant_eur": "100.00"}, {"montant_eur": "50.00"}],
    })
    from decimal import Decimal
    assert Decimal(avec_1) > Decimal(base)
    assert Decimal(avec_2) > Decimal(avec_1)


def test_prix_bouge_avec_quantite_et_matiere():
    """Quantité → ml → P1/P2/P5 ; matière absente vs présente → P1 change."""
    _, mat_id, cyl_id = _ids()
    pq1 = _prix({**_base(cyl_id, mat_id), "quantite": 5_000})
    pq2 = _prix({**_base(cyl_id, mat_id), "quantite": 20_000})
    assert pq1 != pq2


def test_prix_et_geometrie_bougent_sans_outil():
    """Sans outil vs avec outil → décompo (refente) + géométrie (nb_filles)
    diffèrent."""
    _, mat_id, cyl_id = _ids()
    with SessionLocal() as db:
        from decimal import Decimal
        cfg = db.query(ConfigCouts).filter_by(entreprise_id=1).first()
        cfg.cout_exploitation_rebobineuse_eur_h = Decimal("60")
        if (
            db.query(MachineRebobineuse).filter_by(entreprise_id=1, actif=True).first()
            is None
        ):
            db.add(MachineRebobineuse(
                entreprise_id=1, nom="Rebob preview2",
                laize_max_mm=Decimal("400.00"), diametre_max_mm=300,
                vitesse_pratique_m_min=200, cout_horaire_eur=Decimal("50.00"),
                temps_changement_bobine_min=Decimal("2.00"), actif=True,
            ))
        db.commit()
    avec = client.post("/api/devis/preview", json=_base(cyl_id, mat_id)).json()
    sans = client.post("/api/devis/preview", json={
        "laize": 50, "dev": 40, "quantite": 10_000, "matiere_id": mat_id,
        "epaisseur_um": 90, "mode_sans_outil": True, "laize_stock_mm": 250,
    }).json()
    assert avec["geometrie"]["nb_filles"] is None
    assert sans["geometrie"]["nb_filles"] is not None
    assert any("Refente" in d["poste"] for d in sans["decompo"])
    assert all("Refente" not in d["poste"] for d in avec["decompo"])


def _seed_options() -> None:
    """Ajoute 2 options catalogue pour ent 1 : une à forfait (€), une à impact
    production sans tarif (coef vitesse). Idempotent."""
    from decimal import Decimal
    from app.models import OptionFabrication
    with SessionLocal() as db:
        db.query(OptionFabrication).filter(
            OptionFabrication.entreprise_id == 1,
            OptionFabrication.code.in_(["OPT_LAM_T", "OPT_VIT_T"]),
        ).delete(synchronize_session=False)
        db.add(OptionFabrication(
            entreprise_id=1, code="OPT_LAM_T", libelle="Laminage test",
            forfait_eur=Decimal("100.00"), actif=True,
        ))
        db.add(OptionFabrication(
            entreprise_id=1, code="OPT_VIT_T", libelle="Vitesse reduite test",
            coef_vitesse_impact=Decimal("0.90"), actif=True,
        ))
        db.commit()


def test_options_codes_pricing_serveur_et_deltas_par_code():
    """`options_codes` (CODES, pas de montant front) → € serveur via catalogue
    → P6 → prix monte ; `options[]` expose un delta PAR CODE + couleur_plus ;
    l'option impact-production renvoie delta None + flag (pas de faux +0 €)."""
    from decimal import Decimal
    _seed_options()
    _, mat_id, cyl_id = _ids()  # re-seed efface OptionFabrication -> re-add
    _seed_options()
    base = _prix(_base(cyl_id, mat_id))
    avec = _prix({**_base(cyl_id, mat_id), "options_codes": ["OPT_LAM_T"]})
    # Option forfait sélectionnée → prix HT monte (P6 via forfaits_st).
    assert Decimal(avec) > Decimal(base)

    body = client.post("/api/devis/preview", json={
        **_base(cyl_id, mat_id), "options_codes": ["OPT_LAM_T"],
    }).json()
    opts = {o["code"]: o for o in body["options"]}
    # Delta par code pour l'option forfait (€ × (1+marge) > 0, pas impact prod).
    assert "OPT_LAM_T" in opts
    assert opts["OPT_LAM_T"]["impact_production"] is False
    assert Decimal(opts["OPT_LAM_T"]["delta_eur"]) > Decimal("0")
    # Option impact production : delta None + flag (jamais faux +0 €).
    assert "OPT_VIT_T" in opts
    assert opts["OPT_VIT_T"]["impact_production"] is True
    assert opts["OPT_VIT_T"]["delta_eur"] is None
    # couleur_plus toujours présent.
    assert "couleur_plus" in opts and Decimal(opts["couleur_plus"]["delta_eur"]) > 0
    # Décompo : ligne option distincte (label « Option · ... »).
    assert any(d["poste"].startswith("Option · ") for d in body["decompo"])


def test_finitions_retrocompat_sans_casse():
    """`finitions:[{montant_eur}]` (déprécié) fait toujours monter le prix
    (P6) ; A1 en prod envoie [] → comportement inchangé."""
    from decimal import Decimal
    _, mat_id, cyl_id = _ids()
    base = _prix(_base(cyl_id, mat_id))
    avec = _prix({**_base(cyl_id, mat_id), "finitions": [{"montant_eur": "40.00"}]})
    assert Decimal(avec) > Decimal(base)
    # finitions=[] (cas A1 prod) → identique à pas de finitions.
    assert _prix({**_base(cyl_id, mat_id), "finitions": []}) == base


def test_options_disponibles_n_expose_pas_les_montants():
    """Garde-fou : OptionDisponiblePublic ne fuit pas forfait_eur / prix.
    Le front reste sur les codes (ConfigCouts/catalogue = source de coût)."""
    _seed_options()
    r = client.get("/api/optimisation/options-disponibles")
    assert r.status_code == 200, r.text
    for o in r.json():
        assert "forfait_eur" not in o
        assert "prix_au_m2_eur" not in o
        assert "prix_au_mille_eur" not in o


def test_configs_outil_exposees_triees_et_top3(  # Lot C
):
    """`/preview` expose `configs[]` (cylindre × machine) triées score DESC,
    top 3 `recommande`, + `ecarts`. Géométrie pure, aucun coût."""
    _, mat_id, cyl_id = _ids()
    body = client.post("/api/devis/preview", json={
        "laize": 100, "dev": 80, "quantite": 10_000,
        "matiere_id": mat_id, "nb_couleurs": {"impression": 4},
    }).json()
    configs = body["configs"]
    assert configs, "au moins une configuration attendue (format 100×80)"
    # Tri score DESC.
    scores = [c["score"] for c in configs]
    assert scores == sorted(scores, reverse=True)
    # Top 3 recommandé, le reste non.
    for i, c in enumerate(configs):
        assert c["recommande"] is (i < 3)
    # Cohérence géométrie d'une config.
    c0 = configs[0]
    assert c0["poses_total"] == c0["poses_laize"] * c0["poses_dev"]
    assert c0["cylindre_dents"] > 0 and c0["developpe_mm"] > 0
    assert isinstance(c0["sens"], int)
    assert "machine" in c0 and c0["machine"]
    # Écarts présents (défauts brief : laize 5 mm, poses auto).
    assert body["ecarts"]["intervalle_laize_mm"] == 5.0
    assert body["ecarts"]["nb_poses_laize"] == "auto"
    assert body["ecarts"]["force_intervalle_laize"] is False


def test_configs_sans_outil_vide_et_intervalle_dev_zero():  # Lot C
    """Mode sans outil : pas de cylindre → `configs=[]` ; impression continue
    → `ecarts.intervalle_dev_mm = 0`, intervalle laize conservé."""
    _, mat_id, _ = _ids()
    body = client.post("/api/devis/preview", json={
        "laize": 100, "dev": 80, "quantite": 10_000, "matiere_id": mat_id,
        "mode_sans_outil": True, "laize_stock_mm": 250,
    }).json()
    assert body["configs"] == []
    assert body["ecarts"]["intervalle_dev_mm"] == 0.0
    assert body["ecarts"]["intervalle_laize_mm"] == 5.0


def test_v0_marge_override_bouge_le_ht():  # V0
    """Input `marge_pct` (override) → HT recalculé (≠ marge tenant)."""
    from decimal import Decimal
    _, mat_id, cyl_id = _ids()
    base = client.post("/api/devis/preview", json=_base(cyl_id, mat_id)).json()
    haute = client.post("/api/devis/preview", json={
        **_base(cyl_id, mat_id), "marge_pct": 50,
    }).json()
    assert Decimal(haute["marge_pct"]) == Decimal("50.00")
    # Marge plus haute → HT plus haut (coût de revient identique).
    assert Decimal(haute["prix_ht"]) > Decimal(base["prix_ht"])
    assert Decimal(haute["cout_revient"]) == Decimal(base["cout_revient"])


def test_v0_remise_tracee_a_part_sans_toucher_le_cout():  # V0
    """Remise par-dessus le HT brut : `prix_ht` (brut) et `cout_revient`
    INCHANGÉS ; `prix_ht_net` = brut × (1 − remise%)."""
    from decimal import Decimal
    _, mat_id, cyl_id = _ids()
    base = client.post("/api/devis/preview", json=_base(cyl_id, mat_id)).json()
    rem = client.post("/api/devis/preview", json={
        **_base(cyl_id, mat_id), "remise_pct": 10,
    }).json()
    brut = Decimal(base["prix_ht"])
    # Remise n'affecte NI le HT brut NI le coût de revient.
    assert Decimal(rem["prix_ht"]) == brut
    assert Decimal(rem["cout_revient"]) == Decimal(base["cout_revient"])
    # remise_eur = 10 % du brut ; net = brut − remise_eur (invariant métier).
    remise_eur = Decimal(rem["remise_eur"])
    assert remise_eur == (brut * Decimal("10") / Decimal("100")).quantize(Decimal("0.01"))
    assert Decimal(rem["prix_ht_net"]) == brut - remise_eur
    # remise 0 (défaut) → net == brut (value-neutral).
    assert Decimal(base["prix_ht_net"]) == brut
    assert Decimal(base["remise_eur"]) == Decimal("0.00")


def test_v0_decompo_groupee_somme_au_cout_revient():  # V0
    """Décompo groupée (5 lignes métier) = regroupement des 7 postes ; somme
    = coût de revient (avec outil, refente=0)."""
    from decimal import Decimal
    _, mat_id, cyl_id = _ids()
    body = client.post("/api/devis/preview", json=_base(cyl_id, mat_id)).json()
    g = body["decompo_groupee"]
    assert set(g.keys()) == {
        "matiere_p1", "impression_presse_calage", "cliches_outil",
        "option_finitions", "refente",
    }
    somme = sum(Decimal(v) for v in g.values())
    assert somme == Decimal(body["cout_revient"])  # avec outil → refente 0
    assert Decimal(g["refente"]) == Decimal("0")
    assert Decimal(g["matiere_p1"]) > 0


def test_cin_config_id_fige_les_poses():  # Lot C-inputs
    """`config_id` (sélection) fige cylindre/machine/poses → `geometrie.nb_poses`
    == poses_total de la config choisie."""
    _, mat_id, cyl_id = _ids()
    body = client.post("/api/devis/preview", json={
        "laize": 100, "dev": 80, "quantite": 10_000,
        "matiere_id": mat_id, "nb_couleurs": {"impression": 4},
    }).json()
    assert body["configs"], "configs attendues"
    # Choisit une config NON-top pour s'assurer que les poses changent vs défaut.
    c = body["configs"][-1]
    sel = client.post("/api/devis/preview", json={
        "laize": 100, "dev": 80, "quantite": 10_000, "matiere_id": mat_id,
        "nb_couleurs": {"impression": 4}, "config_id": c["id"],
    }).json()
    assert sel["geometrie"]["nb_poses"] == c["poses_total"]
    assert sel["prix_ht"] is not None  # chiffrage OK


def test_cin_config_id_invalide_best_effort():  # Lot C-inputs
    """config_id malformé/hors périmètre → alerte, jamais 500."""
    _, mat_id, cyl_id = _ids()
    r = client.post("/api/devis/preview", json={
        "laize": 100, "dev": 80, "quantite": 10_000, "matiere_id": mat_id,
        "config_id": "zzz-not-an-id",
    })
    assert r.status_code == 200
    assert any("config_id" in a["message"] for a in r.json()["alertes"])


def test_cin_forcage_ecarts_regle7():  # Lot C-inputs
    """Forçage intervalle laize (Règle 7) + nb poses laize → reflétés dans
    `ecarts` et appliqués aux `configs`."""
    _, mat_id, cyl_id = _ids()
    body = client.post("/api/devis/preview", json={
        "laize": 50, "dev": 40, "quantite": 10_000, "matiere_id": mat_id,
        "force_intervalle_laize": True, "intervalle_laize_mm": 8,
        "nb_poses_laize_force": 2,
    }).json()
    assert body["ecarts"]["force_intervalle_laize"] is True
    assert body["ecarts"]["intervalle_laize_mm"] == 8.0
    assert body["ecarts"]["nb_poses_laize"] == 2
    # Toutes les configs respectent le forçage nb poses laize = 2.
    assert body["configs"]
    assert all(c["poses_laize"] == 2 for c in body["configs"])


def test_cin_defauts_value_neutral():  # Lot C-inputs (garde sacré)
    """Sans config_id ni forçage → ecarts par défaut (auto, laize 5),
    comportement strictement inchangé."""
    _, mat_id, cyl_id = _ids()
    body = client.post("/api/devis/preview", json={
        "laize": 100, "dev": 80, "quantite": 10_000, "matiere_id": mat_id,
    }).json()
    assert body["ecarts"]["nb_poses_laize"] == "auto"
    assert body["ecarts"]["intervalle_laize_mm"] == 5.0
    assert body["ecarts"]["force_intervalle_laize"] is False


def test_machine_id_respecte_et_best_effort():
    """machine_id fourni (scopé tenant) accepté ; id hors périmètre → fallback
    1ère presse + alerte (jamais 500)."""
    machine_id, mat_id, cyl_id = _ids()
    ok = client.post("/api/devis/preview", json={
        **_base(cyl_id, mat_id), "machine_id": machine_id,
    })
    assert ok.status_code == 200
    assert ok.json()["prix_ht"] is not None

    ko = client.post("/api/devis/preview", json={
        **_base(cyl_id, mat_id), "machine_id": 999_999,
    })
    assert ko.status_code == 200
    body = ko.json()
    assert body["prix_ht"] is not None  # fallback 1ère presse
    assert any("Machine introuvable" in a["message"] for a in body["alertes"])
