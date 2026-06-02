"""Tests des catalogues defaults Sprint 13 Lot S13.C.1.

Vérifie que :
  - Les comptages sont conformes au brief (19 cyl, 3 machines, 30 matières,
    20 options, 4 barèmes).
  - Les `code` sont uniques au sein de chaque catalogue (clé fonctionnelle UI).
  - Les barèmes utilisent des `type` autorisés par BAREME_TYPES (sinon
    l'insert dans la table `bareme` échouera côté tenant).
  - Les structures sont JSON-serializable (l'API les expose en JSON et
    SQLAlchemy les persiste dans des colonnes JSON).
  - Les helpers `get_*_by_code` retournent bien l'élément ou None.
"""
import json

from app.data.catalogue_defaults import (
    BAREMES_DEFAULT,
    CYLINDRES_STANDARD_DENTS,
    CYLINDRES_STANDARD_MM,
    DENTS_TO_MM_FACTOR,
    MACHINES_DEFAULT,
    MATIERES_DEFAULT,
    OPTIONS_FABRICATION_DEFAULT,
    get_bareme_by_code,
    get_machine_by_code,
    get_matiere_by_code,
    get_option_by_code,
)
from app.models.bareme import BAREME_TYPES


def test_cylindres_count_and_range():
    """19 cylindres ICE, nomenclature dents puis dérivés mm.

    Cas B du 2026-05-16 : la liste historique s'appelait `CYLINDRES_STANDARD_MM`
    mais portait en réalité des nombres de dents. Le seed prod en a hérité
    (5 cylindres avec dev=72/96/104/112/144 au lieu de mm réels). On
    sépare maintenant explicitement les deux représentations.
    """
    # Brief #28 : parc compte demo = 21 cylindres (80..187 dents).
    # 72 retiré (hors parc), 90/103 désactivés via migration data
    # `e8a1c2d5f6b9` côté prod ; ici on teste les défauts en mémoire.
    assert len(CYLINDRES_STANDARD_DENTS) == 21
    assert min(CYLINDRES_STANDARD_DENTS) == 80
    assert max(CYLINDRES_STANDARD_DENTS) == 187
    assert len(set(CYLINDRES_STANDARD_DENTS)) == 21

    # mm : dérivés des dents (×3.175), source de vérité pour la BDD et le moteur.
    assert len(CYLINDRES_STANDARD_MM) == 21
    # Sanity : aucun n'est en deçà de 200 mm (sinon retour Cas B).
    assert all(c > 200 for c in CYLINDRES_STANDARD_MM)
    # Conversion stable : valeur reconstructible depuis les dents.
    for dents, mm in zip(CYLINDRES_STANDARD_DENTS, CYLINDRES_STANDARD_MM):
        assert mm == float(dents * DENTS_TO_MM_FACTOR)


def test_machines_unique_codes_and_required_fields():
    assert len(MACHINES_DEFAULT) == 3
    codes = [m["code"] for m in MACHINES_DEFAULT]
    assert len(set(codes)) == 3, f"Codes machine doivent être uniques : {codes}"
    expected_codes = {"mark_andy_2200", "omet_xflex_330", "nilpeter_fa_22"}
    assert set(codes) == expected_codes
    # Champs NOT NULL côté model Machine
    for m in MACHINES_DEFAULT:
        assert m["nom"]
        assert m["laize_totale_mm"] > 0
        assert m["laize_utile_mm"] > 0
        assert m["vitesse_pratique_m_min"] > 0
        assert m["laize_utile_mm"] <= m["laize_totale_mm"]


def test_matieres_count_unique_codes():
    assert len(MATIERES_DEFAULT) == 30
    codes = [m["code"] for m in MATIERES_DEFAULT]
    assert len(set(codes)) == 30, "Codes matière doivent être uniques"
    # Au moins une matière transparente (déclencheur règle spot détection)
    transparents = [m for m in MATIERES_DEFAULT if m.get("est_transparent")]
    assert len(transparents) >= 3, (
        f"Au moins 3 matières transparentes attendues, {len(transparents)} trouvées"
    )


def test_matieres_categories_couvrent_marche():
    categories = {m["categorie"] for m in MATIERES_DEFAULT}
    expected = {"papier", "film", "thermique", "synthetique", "special"}
    assert categories == expected, (
        f"Catégories incomplètes : trouvées={categories}, attendues={expected}"
    )


def test_options_count_unique_codes_and_coefs():
    assert len(OPTIONS_FABRICATION_DEFAULT) == 20
    codes = [o["code"] for o in OPTIONS_FABRICATION_DEFAULT]
    assert len(set(codes)) == 20, "Codes option doivent être uniques"
    # Vérif quelques coefs critiques du CdC (table lignes 1101-1115)
    dorure = get_option_by_code("dorure_chaud")
    assert dorure is not None
    assert dorure["coef_vitesse_impact"] == 0.75
    assert dorure["coef_gache_impact"] == 1.15
    assert dorure["ajoute_temps_calage_min"] == 25
    livret = get_option_by_code("livret_booklet")
    assert livret is not None
    assert livret["coef_vitesse_impact"] == 0.70
    # Modules spéciaux requis bien renseignés là où c'est attendu
    assert "retournement_laize" in livret["modules_speciaux_requis"]


def test_baremes_types_alignes_avec_modele():
    """Les `type` des barèmes default doivent appartenir à BAREME_TYPES
    (sinon l'insert dans la table `bareme` échouera côté tenant)."""
    assert len(BAREMES_DEFAULT) == 4
    codes = [b["code"] for b in BAREMES_DEFAULT]
    assert len(set(codes)) == 4
    for b in BAREMES_DEFAULT:
        assert b["type"] in BAREME_TYPES, (
            f"Barème '{b['code']}' a type='{b['type']}' "
            f"non reconnu (BAREME_TYPES = {sorted(BAREME_TYPES)})"
        )
        assert b["bareme_data"], (
            f"Barème '{b['code']}' a un bareme_data vide"
        )


def test_bareme_echenillage_palier_5mm_alignement_cdc():
    """Le palier 5mm doit avoir coef_vitesse=0.70 et score=50
    (CdC ligne 520 — barème ICE standard).
    """
    bareme = get_bareme_by_code("echenillage_ice")
    assert bareme is not None
    palier_5 = next(
        p for p in bareme["bareme_data"] if p["intervalle_max_mm"] == 5
    )
    assert palier_5["qualite"] == "complique"
    assert palier_5["coef_vitesse"] == 0.70
    assert palier_5["coef_gache"] == 1.08
    assert palier_5["score"] == 50


def test_bareme_effet_banane_saut_non_lineaire_300_350():
    """Le saut Z=381 → Z=508 entre paliers 250-300 et 300-350 reflète
    un seuil physique de rigidité (CdC ligne 575 — non extrapolable).
    Valeurs en mm réels après fix Cas B (anciennement 120 et 160 dents).
    """
    bareme = get_bareme_by_code("effet_banane_ice")
    assert bareme is not None
    palier_300 = next(
        p for p in bareme["bareme_data"] if p["largeur_max_mm"] == 300
    )
    palier_350 = next(
        p for p in bareme["bareme_data"] if p["largeur_max_mm"] == 350
    )
    assert palier_300["developpe_mini_mm"] == 381.0
    assert palier_350["developpe_mini_mm"] == 508.0


def test_all_data_is_json_serializable():
    """L'endpoint expose les catalogues en JSON ; les colonnes SQLAlchemy
    JSON les persistent telles quelles. Doit donc passer json.dumps sans
    exception (pas de Decimal, pas de datetime, pas de set...).
    """
    payload = {
        "cylindres": CYLINDRES_STANDARD_MM,
        "machines": MACHINES_DEFAULT,
        "matieres": MATIERES_DEFAULT,
        "options": OPTIONS_FABRICATION_DEFAULT,
        "baremes": BAREMES_DEFAULT,
    }
    # ensure_ascii=False pour ne pas masquer un caractère Unicode cassé
    serialized = json.dumps(payload, ensure_ascii=False)
    assert len(serialized) > 1000  # sanity : un payload de 5 catalogues n'est pas vide
    # Round-trip — vérifie qu'on récupère bien les mêmes longueurs
    reloaded = json.loads(serialized)
    assert len(reloaded["cylindres"]) == 21  # Brief #28 : parc 21 cyls
    assert len(reloaded["machines"]) == 3
    assert len(reloaded["matieres"]) == 30
    assert len(reloaded["options"]) == 20
    assert len(reloaded["baremes"]) == 4


def test_helpers_get_by_code():
    assert get_machine_by_code("mark_andy_2200")["marque"] == "Mark Andy"
    assert get_machine_by_code("inexistante") is None
    assert get_matiere_by_code("BOPP_TRANSP_50")["est_transparent"] is True
    assert get_matiere_by_code("xxx") is None
    assert get_option_by_code("dorure_chaud")["categorie"] == "Finition"
    assert get_option_by_code("xxx") is None
    assert get_bareme_by_code("echenillage_ice")["type"] == "echenillage"
    assert get_bareme_by_code("xxx") is None
