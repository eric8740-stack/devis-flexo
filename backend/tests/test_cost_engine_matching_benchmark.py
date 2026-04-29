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
