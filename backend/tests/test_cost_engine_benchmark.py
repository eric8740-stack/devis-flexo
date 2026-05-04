"""Cas-test benchmark — devis médian construit sur les seeds existants.

Ce fichier sert de référence vivante du moteur de coût v2 :
- Reproduit un devis "réaliste médian" calibré sur la production réelle
- Génère un rapport Markdown lisible (`backend/cost_breakdown.md`)
  pour vérifier la cohérence métier en démo
- Fige le total HT attendu pour détecter toute régression du moteur

Cas-test médian calibré sur statistiques de production réelle (croisement
Eric, 28 avril 2026, 1 301 dossiers analysés) :
- Matière représentative ~25 % de la production réelle (papier vélin
  standard 80g) ; le COUCHE_BRILLANT_80 initial ne couvrait que 0.2 %.
- Machine Mark Andy P5 — la plus utilisée du parc.
- Tirage 3 000 ml — proche de la médiane sectorielle (3 348 ml).

Total HT figé (1449.09 €) validé par Eric le 28 avril 2026 sur le
rapport cost_breakdown.md généré. Si une modif du moteur fait bouger
ce nombre, c'est volontaire et il faut ajuster ici.

Choix des paramètres du cas médian :
- Complexe id=31 (VELIN_STANDARD_80, papier 80g/m², 0.35 €/m²)
- Machine id=1 (Mark Andy P5, vitesse 6000 m/h, calage 1.0 h)
- Tirage 3000 ml × laize utile 220 mm = 660 m² imprimés
- 5 couleurs (4 CMJ + 1 Pantone), forfait ST 50 € (Pelliculage Express)
- Marge 18 % (entreprise.pct_marge_defaut, persona PRD "Compétitif")
"""
from decimal import Decimal
from pathlib import Path

from app.db import SessionLocal
from app.schemas.devis import DevisInput, PartenaireSTForfait
from app.services.cost_engine import MoteurDevis

REPORT_PATH = Path(__file__).resolve().parent.parent / "cost_breakdown.md"

EXPECTED_TOTAL_HT = Decimal("1449.09")
EXPECTED_COUT_REVIENT = Decimal("1228.04")
EXPECTED_PCT_MARGE = Decimal("0.18")


def _devis_median() -> DevisInput:
    return DevisInput(
        complexe_id=31,
        laize_utile_mm=220,
        ml_total=3000,
        nb_couleurs_par_type={"process_cmj": 4, "pantone": 1},
        machine_id=1,
        forfaits_st=[
            PartenaireSTForfait(partenaire_st_id=1, montant_eur=Decimal("50.00"))
        ],
    )


def test_benchmark_devis_median_total_HT():
    """Total HT figé sur le cas médian. Régression = à investiguer."""
    with SessionLocal() as db:
        out = MoteurDevis(db, entreprise_id=1).calculer(_devis_median())
    assert out.cout_revient_eur == EXPECTED_COUT_REVIENT
    assert out.pct_marge_appliquee == EXPECTED_PCT_MARGE
    assert out.prix_vente_ht_eur == EXPECTED_TOTAL_HT


def test_benchmark_writes_cost_breakdown_md():
    """Génère un rapport Markdown lisible pour audit / démo."""
    with SessionLocal() as db:
        out = MoteurDevis(db, entreprise_id=1).calculer(_devis_median())

    lines = [
        "# Cost breakdown — devis médian de référence (S3 Lot 3d)",
        "",
        "Cas-test reproductible construit sur les seeds existants.",
        "Régénéré à chaque run pytest (`tests/test_cost_engine_benchmark.py`).",
        "",
        "## Méthode de calibrage",
        "",
        "Cas-test médian calibré sur statistiques de production réelle :",
        "1 301 dossiers analysés, matière représentative de ~25 % des",
        "dossiers (papier vélin standard), machine Mark Andy P5",
        "(la plus utilisée), tirage 3 000 ml (proche de la médiane",
        "sectorielle 3 348 ml).",
        "",
        "## Paramètres d'entrée",
        "",
        "| Paramètre | Valeur |",
        "|---|---|",
        "| Complexe | id=31 VELIN_STANDARD_80 (papier 80 g/m², 0.35 €/m²) |",
        "| Machine | id=1 Mark Andy P5 (6000 m/h, calage 1.0 h) |",
        "| Laize utile | 220 mm |",
        "| Tirage | 3000 ml |",
        "| Couleurs | 4 process_cmj + 1 pantone (5 total) |",
        "| Forfait ST | Pelliculage Express id=1 — 50 € |",
        "| Marge | 18 % (entreprise.pct_marge_defaut, persona PRD) |",
        "",
        "## Détail par poste",
        "",
        "| # | Libellé | Montant € |",
        "|---|---|---:|",
    ]
    for p in out.postes:
        lines.append(f"| P{p.poste_numero} | {p.libelle} | {p.montant_eur} |")

    lines += [
        f"| | **Coût de revient** | **{out.cout_revient_eur}** |",
        f"| | Marge appliquée | {out.pct_marge_appliquee * 100} % |",
        f"| | **Prix vente HT** | **{out.prix_vente_ht_eur}** |",
        "",
        "## Détails techniques par poste (audit)",
        "",
    ]
    for p in out.postes:
        lines.append(f"### P{p.poste_numero} — {p.libelle} ({p.montant_eur} €)")
        lines.append("")
        for k, v in p.details.items():
            lines.append(f"- `{k}` : {v}")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    assert REPORT_PATH.exists()
    assert REPORT_PATH.stat().st_size > 0
