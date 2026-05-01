"""Benchmarks figés mode 'matching' (Sprint 7 Lot 7g).

Cas V7a-V7d vérifient la non-régression du moteur de coût v2 mode matching :
  V7a — V1a en mode matching → 3 candidats figés (HT identique à V1a manuel)
  V7b — Plaque 320 mm (banane Z_mini=160 > Z_MAX=144) → 422 explicite
  V7c — Plaque > laize - marge → 422 (filtre laize machine)
  V7d — Format extrême → 422 (intervalle hors plage 2.5-15)

V7a = preuve mathématique que les postes ne dépendent pas du choix de
cylindre dans le moteur actuel (HT = HT_manuel_V1a = 1449.09 €). Le prix
au mille varie en théorie selon nb_etiq_par_metre, mais dans le cas V1a
les 3 cylindres trouvés ont le même nb_etiq_par_metre=23 → prix_au_mille
identique 7.00 €/1000.

Génère cost_breakdown_matching.md pour audit / démo.
"""
from decimal import Decimal
from pathlib import Path

import pytest

from app.db import SessionLocal
from app.schemas.devis import DevisInput, PartenaireSTForfait
from app.services.cost_engine import MoteurDevis
from app.services.cost_engine.errors import CostEngineError

REPORT_PATH = Path(__file__).resolve().parent.parent / "cost_breakdown_matching.md"

# HT V1a SACRÉ — le moteur matching ne doit pas le modifier (postes
# indépendants du choix de cylindre dans la modélisation actuelle).
EXPECTED_HT_V1A = Decimal("1449.09")
EXPECTED_PRIX_MILLE_V7A = Decimal("7.00")


def _devis_v1a_matching() -> DevisInput:
    """V1a payload (cas médian) + mode_calcul='matching'.

    format 60×40 + nb_poses_largeur=3 → largeur_plaque = 60×3 = 180 mm
    (banane Z_mini=96 selon TABLE_EFFET_BANANE).
    """
    return DevisInput(
        complexe_id=31,
        laize_utile_mm=220,
        ml_total=3000,
        nb_couleurs_par_type={"process_cmj": 4, "pantone": 1},
        machine_id=1,
        mode_calcul="matching",
        forfaits_st=[
            PartenaireSTForfait(partenaire_st_id=1, montant_eur=Decimal("50.00"))
        ],
    )


# ---------------------------------------------------------------------------
# V7a — V1a en mode matching : 3 candidats figés
# ---------------------------------------------------------------------------


def test_v7a_v1a_matching_returns_3_candidats_with_HT_v1a_preserved():
    """HT identique pour les 3 candidats = HT V1a manuel = 1449.09 €."""
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_v1a_matching())
    assert out.mode == "matching"
    assert len(out.candidats) == 3
    for c in out.candidats:
        assert c.prix_vente_ht_eur == EXPECTED_HT_V1A, (
            f"Cylindre Z={c.z} : HT={c.prix_vente_ht_eur} ≠ V1a {EXPECTED_HT_V1A}"
        )


def test_v7a_v1a_matching_top_3_z_figes():
    """Top 3 cylindres figés Z=134, 121, 108 — tri intervalle croissant."""
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_v1a_matching())
    z_list = [c.z for c in out.candidats]
    assert z_list == [134, 121, 108], (
        f"Top 3 Z attendu [134, 121, 108], obtenu {z_list}. "
        "Régression matcher ou changement table effet banane ?"
    )


def test_v7a_v1a_matching_nb_etiq_par_tour_figes():
    """Couples (Z, nb_etiq_par_tour) figés : (134, 10), (121, 9), (108, 8)."""
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_v1a_matching())
    couples = [(c.z, c.nb_etiq_par_tour) for c in out.candidats]
    assert couples == [(134, 10), (121, 9), (108, 8)]


def test_v7a_v1a_matching_intervalles_dans_plage():
    """Intervalles dans [2.5, 15] mm + tri croissant."""
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_v1a_matching())
    intervalles = [c.intervalle_mm for c in out.candidats]
    assert intervalles == sorted(intervalles), "Tri intervalle croissant attendu"
    for iv in intervalles:
        assert Decimal("2.5") <= iv <= Decimal("15.0")


def test_v7a_v1a_matching_prix_au_mille_700():
    """Prix au mille V1a matching = 7.00 €/1000 (3 candidats avec
    nb_etiq_par_metre=23 → même prix au mille)."""
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_v1a_matching())
    for c in out.candidats:
        assert c.prix_au_mille_eur == EXPECTED_PRIX_MILLE_V7A
        assert c.nb_etiq_par_metre == 23


# ---------------------------------------------------------------------------
# V7b — Plaque 320 mm : banane Z_mini=160 > Z_MAX=144 → 422 explicite
# ---------------------------------------------------------------------------


def test_v7b_plaque_320_banane_zmini_160_returns_422():
    """format_h=40, largeur_plaque=320 mm.

    Banane lookup → Z_mini=160 (palier 350) > Z_MAX=144 → 0 candidat → 422.
    Note : 320 mm est aussi la limite admissible exacte (laize 330 - 2×5),
    donc le filtre laize passe et l'erreur vient bien du matcher (pas du
    filtre laize amont).
    """
    payload = _devis_v1a_matching().model_copy(
        update={
            "format_etiquette_largeur_mm": 80,
            "nb_poses_largeur": 4,  # 80 × 4 = 320 mm
        }
    )
    with SessionLocal() as db, pytest.raises(CostEngineError, match="Aucun cylindre"):
        MoteurDevis(db).calculer(payload)


# ---------------------------------------------------------------------------
# V7c — Plaque > laize - marge : filtre laize machine → 422
# ---------------------------------------------------------------------------


def test_v7c_plaque_excede_laize_machine_returns_422():
    """Mark Andy laize 330, marge 2×5=10, max admissible = 320.
    Plaque 360 > 320 → CostEngineError filtre laize."""
    payload = _devis_v1a_matching().model_copy(
        update={
            "format_etiquette_largeur_mm": 60,
            "nb_poses_largeur": 6,  # 60 × 6 = 360 mm
        }
    )
    with SessionLocal() as db, pytest.raises(CostEngineError, match="laize"):
        MoteurDevis(db).calculer(payload)


# ---------------------------------------------------------------------------
# V7d — Format extrême : intervalle hors plage [2.5, 15] mm → 422
# ---------------------------------------------------------------------------


def test_v7d_format_extreme_returns_422():
    """format_etiquette_hauteur_mm=600 → impossible (intervalle hors plage)."""
    payload = _devis_v1a_matching().model_copy(
        update={"format_etiquette_hauteur_mm": 600},
    )
    with SessionLocal() as db, pytest.raises(CostEngineError, match="Aucun cylindre"):
        MoteurDevis(db).calculer(payload)


# ---------------------------------------------------------------------------
# Génération du rapport markdown V7a (audit / démo)
# ---------------------------------------------------------------------------


def test_v7a_writes_matching_breakdown_md():
    """Génère cost_breakdown_matching.md — détail des 3 candidats V7a."""
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_v1a_matching())

    lines = [
        "# Cost breakdown matching — V7a (S7 Lot 7g)",
        "",
        "Cas V1a (médian) en **mode matching** : top 3 cylindres magnétiques",
        "compatibles avec le format 60×40, plaque 180 mm sur Mark Andy P5",
        "(laize 330, banane Z_mini=96).",
        "",
        "## Garde-fou métier",
        "",
        "**HT identique pour les 3 candidats = HT V1a manuel = 1449.09 €.**",
        "Les postes ne dépendent pas du choix de cylindre dans le moteur",
        "actuel — seul le `prix_au_mille` peut varier (selon",
        "`nb_etiq_par_metre`). Toute régression sur cet invariant doit être",
        "investiguée (introduction d'une dépendance cylindre dans un poste ?).",
        "",
        "## Top 3 candidats (tri intervalle croissant)",
        "",
        "| Rang | Z | nb_etiq/tour | Circonf. mm | Pas mm | Intervalle mm | Étiq/m | HT € | Prix/1000 € |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, c in enumerate(out.candidats, start=1):
        lines.append(
            f"| {i} | {c.z} | {c.nb_etiq_par_tour} | {c.circonference_mm} | "
            f"{c.pas_mm:.4f} | {c.intervalle_mm:.4f} | {c.nb_etiq_par_metre} | "
            f"{c.prix_vente_ht_eur} | {c.prix_au_mille_eur} |"
        )

    tete = out.candidats[0]
    lines += [
        "",
        "## Postes (communs aux 3 candidats)",
        "",
        f"- **Coût de revient** : {tete.cout_revient_eur} €",
        f"- **Marge appliquée** : {tete.pct_marge_appliquee * 100} %",
        f"- **Prix vente HT** : {tete.prix_vente_ht_eur} €",
        "",
        "| # | Libellé | Montant € |",
        "|---|---|---:|",
    ]
    for p in tete.postes:
        lines.append(f"| P{p.poste_numero} | {p.libelle} | {p.montant_eur} |")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    assert REPORT_PATH.exists()
    assert REPORT_PATH.stat().st_size > 0


# ---------------------------------------------------------------------------
# V8a-V8e — Hotfix bug prix_au_mille mode matching (01/05/2026)
#
# Tests qui auraient capté le bug d'oubli de nb_poses_developpement dans
# orchestrator._compute_matching (lignes 167-174). Avant ce hotfix, tous
# les cas figés Sprint 5/7 V2 avaient nb_poses_developpement=1 (default
# Pydantic), donc le bug était invisible. Le cas Eric ICE 60×100 mm
# 2 poses_l × 2 poses_d a déclenché la détection en prod.
#
# Vérifié manuellement avant commit : V8a-V8d ÉCHOUENT sur le code AVANT
# Hotfix-A (orchestrator.py sans le facteur nb_poses_developpement).
# V8e reste vert avec ou sans fix (poses_d=1 → × 1 neutre = garde-fou
# anti-régression du fix lui-même).
# ---------------------------------------------------------------------------


def test_v8a_v1a_matching_poses_d_2_divides_prix_mille_by_2():
    """V1a payload + nb_poses_developpement=2 → prix_au_mille ÷ 2 vs V7a.

    V7a (poses_d=1) → 7,00 €/1000. Avec poses_d=2, on imprime 2× plus
    d'étiquettes par mètre linéaire dans le sens développement →
    prix_au_mille divisé par 2 = 3,50 €/1000.

    Sans le fix, prix_au_mille resterait à 7,00 (× 1 implicite) → fail.
    """
    payload = _devis_v1a_matching().model_copy(
        update={"nb_poses_developpement": 2}
    )
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(payload)
    # Z + HT préservés (postes/cylindres indépendants de poses_d)
    assert [c.z for c in out.candidats] == [134, 121, 108]
    for c in out.candidats:
        assert c.prix_vente_ht_eur == EXPECTED_HT_V1A
        # 7.00 / 2 = 3.50 EXACT (V7a / 2)
        assert c.prix_au_mille_eur == Decimal("3.50"), (
            f"Cylindre Z={c.z} : prix_au_mille={c.prix_au_mille_eur} "
            f"≠ 3.50 attendu (V7a 7.00 / poses_d=2). Bug nb_poses_developpement ?"
        )


def test_v8b_cas_eric_ice_60x100_2x2_consistance_mode_agnostique():
    """Cas réel Eric ICE 60×100 mm, 2 poses_l × 2 poses_d, 30 000 m.

    Vérifie consistance mode-agnostique : prix_au_mille_matching[0] et
    prix_au_mille_manuel doivent être à ±10%% l'un de l'autre (le delta
    vient de l'écart pas_idéal manuel vs pas_cylindre matching).

    Sans le fix : ratio matching/manuel = ~2.146 (× nb_poses_developpement)
                  → assertion échoue.
    Avec le fix : ratio ~1.07 → assertion passe.
    """
    base = DevisInput(
        complexe_id=31,
        laize_utile_mm=220,
        ml_total=30000,
        nb_couleurs_par_type={"process_cmj": 4, "pantone": 1},
        machine_id=1,
        format_etiquette_largeur_mm=60,
        format_etiquette_hauteur_mm=100,
        nb_poses_largeur=2,
        nb_poses_developpement=2,
        forfaits_st=[
            PartenaireSTForfait(partenaire_st_id=1, montant_eur=Decimal("50.00"))
        ],
    )
    manuel = base.model_copy(
        update={"mode_calcul": "manuel", "intervalle_mm": Decimal("3.5")}
    )
    matching = base.model_copy(update={"mode_calcul": "matching"})

    with SessionLocal() as db:
        moteur = MoteurDevis(db)
        out_m = moteur.calculer(manuel)
        out_x = moteur.calculer(matching)

    # HT identique entre les 2 modes (postes ne dépendent pas du mode)
    assert out_m.prix_vente_ht_eur == out_x.candidats[0].prix_vente_ht_eur

    # Consistance prix_au_mille : matching ~ manuel à ±10%%
    ratio = out_x.candidats[0].prix_au_mille_eur / out_m.prix_au_mille_eur
    assert Decimal("0.9") <= ratio <= Decimal("1.1"), (
        f"Ratio matching/manuel = {ratio:.3f} hors [0.9, 1.1]. "
        f"manuel={out_m.prix_au_mille_eur} matching={out_x.candidats[0].prix_au_mille_eur}. "
        "Bug d'oubli de dimension de poses dans un des modes ?"
    )


def test_v8c_format_80x60_2_poses_l_3_poses_d_facteur_6_applique():
    """Format 80×60, 2 poses_l × 3 poses_d, mode matching.

    Vérifie que le facteur 6 (= 2 × 3) est bien appliqué : le prix_au_mille
    avec poses_d=3 doit être 1/3 de celui avec poses_d=1 (toutes choses
    égales par ailleurs).

    Sans le fix, les 2 prix seraient identiques (poses_d ignoré) → ratio=1
    au lieu de 1/3 → fail.
    """
    base = DevisInput(
        complexe_id=31,
        laize_utile_mm=220,
        ml_total=10000,
        nb_couleurs_par_type={"process_cmj": 4, "pantone": 1},
        machine_id=1,
        format_etiquette_largeur_mm=80,
        format_etiquette_hauteur_mm=60,
        nb_poses_largeur=2,
        mode_calcul="matching",
        forfaits_st=[],
    )
    poses_d_1 = base.model_copy(update={"nb_poses_developpement": 1})
    poses_d_3 = base.model_copy(update={"nb_poses_developpement": 3})

    with SessionLocal() as db:
        moteur = MoteurDevis(db)
        out_1 = moteur.calculer(poses_d_1)
        out_3 = moteur.calculer(poses_d_3)

    # HT identique (postes indépendants de poses_d)
    assert out_1.candidats[0].prix_vente_ht_eur == out_3.candidats[0].prix_vente_ht_eur
    # Mêmes cylindres (matcher indépendant de poses_d)
    assert [c.z for c in out_1.candidats] == [c.z for c in out_3.candidats]

    # prix_au_mille_3 = prix_au_mille_1 / 3 (à 1 cent près pour quantize)
    expected = (out_1.candidats[0].prix_au_mille_eur / Decimal(3)).quantize(
        Decimal("0.01")
    )
    assert out_3.candidats[0].prix_au_mille_eur == expected, (
        f"poses_d=1 → {out_1.candidats[0].prix_au_mille_eur}, "
        f"poses_d=3 → {out_3.candidats[0].prix_au_mille_eur}, "
        f"attendu {expected} (= poses_d_1 / 3). Facteur poses_d non appliqué ?"
    )


def test_v8d_coherence_mode_agnostique_50x80_3_2():
    """Anti-régression structurelle : payload générique 50×80, 3×2 poses,
    20 000 m. Le ratio prix_au_mille_matching / prix_au_mille_manuel doit
    rester proche de 1 (pas un facteur N), TOUT en mode confondu.

    Vise à capter tout futur bug similaire (oubli d'une dimension dans
    un des modes), pas seulement le bug actuel.
    """
    base = DevisInput(
        complexe_id=31,
        laize_utile_mm=220,
        ml_total=20000,
        nb_couleurs_par_type={"process_cmj": 4, "pantone": 1},
        machine_id=1,
        format_etiquette_largeur_mm=50,
        format_etiquette_hauteur_mm=80,
        nb_poses_largeur=3,
        nb_poses_developpement=2,
        forfaits_st=[],
    )
    manuel = base.model_copy(
        update={"mode_calcul": "manuel", "intervalle_mm": Decimal("3")}
    )
    matching = base.model_copy(update={"mode_calcul": "matching"})

    with SessionLocal() as db:
        moteur = MoteurDevis(db)
        out_m = moteur.calculer(manuel)
        out_x = moteur.calculer(matching)

    ratio = out_x.candidats[0].prix_au_mille_eur / out_m.prix_au_mille_eur
    assert Decimal("0.85") <= ratio <= Decimal("1.15"), (
        f"Ratio matching/manuel = {ratio:.3f} hors [0.85, 1.15] sur 50×80, "
        f"3×2 poses, 20000 m. manuel={out_m.prix_au_mille_eur} "
        f"matching={out_x.candidats[0].prix_au_mille_eur}. "
        "Soupçon de bug oubli dimension de poses dans un mode."
    )


def test_v8e_anti_regression_v7a_poses_d_1_reste_700():
    """Garde-fou anti-régression du fix : V7a (poses_d=1) doit rester EXACT
    à 7.00 €/1000. Le `× 1` du facteur poses_d est neutre, le hotfix ne
    doit donc rien changer pour ce cas figé Sprint 7 V2.

    Test redondant avec test_v7a_v1a_matching_prix_au_mille_700 mais
    explicité ici pour matérialiser le garde-fou hotfix dans le bloc V8.
    """
    with SessionLocal() as db:
        out = MoteurDevis(db).calculer(_devis_v1a_matching())
    for c in out.candidats:
        assert c.prix_au_mille_eur == EXPECTED_PRIX_MILLE_V7A, (
            f"REGRESSION HOTFIX : V7a prix_au_mille = {c.prix_au_mille_eur} "
            f"≠ {EXPECTED_PRIX_MILLE_V7A} EXACT figé Sprint 7 V2 !"
        )
