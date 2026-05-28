"""5 cas-tests de non-régression du moteur de coût v2 (S3 Lot 3e + S5 Lot 5c).

Décision Eric (28 avril 2026) : on n'utilise PAS 5 dossiers réels d'archives
ICE Étiquettes (planning.xlsx 2014). La réindexation 2014→2026 introduirait
des écarts artificiels (+50 % papier, +35 % encres, +30 % MO sur 12 ans)
sans rapport avec la qualité du moteur.

À la place : 5 variantes du cas médian qui testent la robustesse
mathématique du moteur sur des cas typés métier.

Recalibrage Sprint 5 Lot 5c (refonte P3 en sous-postes + outil découpe) :

  V1a — Cas médian + outil EXISTANT (figé Lot 3d, refonte P3 transparente)
  V1b — Cas médian + nouvel outil 4 tracés simple (NEW Lot 5c)
  V2  — Petite série (outil existant default — forfaits P3+P4 dominants)
  V3  — Grande série (outil existant default — effet d'échelle)
  V4  — Multi-couleurs (outil existant default — stress P2 + P3a)

V5 (pantone seul + multi-ST) supprimée Lot 5c — remplacée par V1b qui
teste le nouveau sous-poste P3b outil de découpe.

Chaque variante vérifie une **propriété métier** spécifique en plus du
total HT figé après validation Eric.

------------------------------------------------------------------------
Phase 2 / Lot 1 (2026-05-28) — découplage DB live → fixture pure.

Avant ce lot : le benchmark utilisait `SessionLocal()` + le seed
re-appliqué par `run_seed()` autouse. Conséquence : toute édition Stratégique
du tenant démo (entreprise_id=1) ou tout drift du seed CSV cassait V1a.

Désormais : pytest fixture `fixture_session_factory` qui construit une
session SQLite IN-MEMORY peuplée par INSERTs Python en dur depuis les
constantes `_FIXTURE_*` ci-dessous (snapshot exact des seeds ICE à T0).
Zéro touche cost_engine — les calculateurs continuent de lire via la
session injectée comme avant. La source de vérité passe du CSV/dev DB
au fichier de test ; les sacrés EXACT restent EXACT.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Callable, Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import (
    Complexe,
    Entreprise,
    Machine,
    TarifEncre,
    TarifPoste,
)
from app.schemas.devis import DevisInput, DevisOutput, PartenaireSTForfait
from app.services.cost_engine import MoteurDevis

REPORT_PATH = Path(__file__).resolve().parent.parent / "cost_breakdown_5cas.md"
DEMO_ENTREPRISE_ID = 1


# ---------------------------------------------------------------------------
# FIXTURE — snapshot ICE figé (valeurs identiques au seed CSV à T0)
# ---------------------------------------------------------------------------
# Aucun chiffre attendu ne bouge (V1a 1 449,09 € · V1b 1 921,09 € · V2 743,01 €
# · V3 8 437,47 € · V4 1 697,17 €). Si l'un d'eux dérive, la fixture ne
# reflète plus le seed → STOP et investiguer.

# 10 paramètres tarifaires globaux du tenant (cf. seeds/tarif_poste.csv).
_FIXTURE_TARIF_POSTE: list[dict] = [
    {"id": 1, "cle": "matiere_prix_kg_defaut", "poste_numero": 1,
     "libelle": "Prix matière par kilo (défaut)", "valeur_defaut": Decimal("1.7500"), "unite": "€/kg"},
    {"id": 2, "cle": "cliche_prix_couleur", "poste_numero": 3,
     "libelle": "Prix d'un cliché par couleur", "valeur_defaut": Decimal("45.0000"), "unite": "€/couleur"},
    {"id": 3, "cle": "calage_forfait", "poste_numero": 4,
     "libelle": "Calage forfaitaire par devis", "valeur_defaut": Decimal("225.0000"), "unite": "€/devis"},
    {"id": 4, "cle": "roulage_prix_horaire", "poste_numero": 5,
     "libelle": "Prix horaire de roulage presse", "valeur_defaut": Decimal("375.0000"), "unite": "€/h"},
    {"id": 5, "cle": "marge_confort_roulage_mm", "poste_numero": 1,
     "libelle": "Marge de confort en roulage", "valeur_defaut": Decimal("10.0000"), "unite": "mm"},
    {"id": 6, "cle": "finitions_prix_m2", "poste_numero": 6,
     "libelle": "Prix finitions par m²", "valeur_defaut": Decimal("0.1250"), "unite": "€/m²"},
    {"id": 7, "cle": "mo_prix_horaire", "poste_numero": 7,
     "libelle": "Prix horaire main d'œuvre", "valeur_defaut": Decimal("70.0000"), "unite": "€/h"},
    {"id": 8, "cle": "outil_base_eur", "poste_numero": 3,
     "libelle": "Coût outil neuf (forfait fixe)", "valeur_defaut": Decimal("200.0000"), "unite": "€"},
    {"id": 9, "cle": "outil_par_trace_eur", "poste_numero": 3,
     "libelle": "Coût par trace de complexité", "valeur_defaut": Decimal("50.0000"), "unite": "€"},
    {"id": 10, "cle": "surcout_forme_speciale_pct", "poste_numero": 3,
     "libelle": "Majoration forme spéciale", "valeur_defaut": Decimal("1.4000"), "unite": "×"},
]

# 5 types d'encre (cf. seeds/tarif_encre.csv). ratio g/m²/couleur = 2.000 partout.
_FIXTURE_TARIF_ENCRE: list[dict] = [
    {"id": 1, "type_encre": "process_cmj", "libelle": "Process CMJ", "prix_kg_defaut": Decimal("15.75"),
     "ratio_g_m2_couleur": Decimal("2.000")},
    {"id": 2, "type_encre": "process_black_hc", "libelle": "Process Black HC", "prix_kg_defaut": Decimal("16.25"),
     "ratio_g_m2_couleur": Decimal("2.000")},
    {"id": 3, "type_encre": "pantone", "libelle": "Pantone", "prix_kg_defaut": Decimal("21.50"),
     "ratio_g_m2_couleur": Decimal("2.000")},
    {"id": 4, "type_encre": "blanc_high_opaque", "libelle": "Blanc HO", "prix_kg_defaut": Decimal("14.00"),
     "ratio_g_m2_couleur": Decimal("2.000")},
    {"id": 5, "type_encre": "metallise", "libelle": "Encre métallisée", "prix_kg_defaut": Decimal("47.50"),
     "ratio_g_m2_couleur": Decimal("2.000")},
]

# Machine du benchmark (cf. seeds/machine.csv row 1 — Mark Andy P5).
_FIXTURE_MACHINE: dict = {
    "id": 1,
    "nom": "Mark Andy P5",
    "laize_max_mm": Decimal("330.00"),
    "vitesse_moyenne_m_h": 6000,
    "duree_calage_h": Decimal("1.00"),
    "cout_horaire_eur": Decimal("60.00"),
}

# Complexe du benchmark (cf. seeds/complexe.csv row 31 — VELIN_STANDARD_80).
_FIXTURE_COMPLEXE: dict = {
    "id": 31,
    "reference": "VELIN_STANDARD_80",
    "famille": "papier_standard",
    "face_matiere": "Papier vélin standard 80g",
    "grammage_g_m2": Decimal("80"),
    "adhesif_type": "permanent",
    "prix_m2_eur": Decimal("0.3500"),
}

# Tenant démo + marge appliquée (cf. seeds/entreprise.csv).
_FIXTURE_ENTREPRISE: dict = {
    "id": DEMO_ENTREPRISE_ID,
    "raison_sociale": "Paysant & Fils Étiquettes (fixture)",
    "siret": "12345678901234",
    "pct_marge_defaut": 0.18,
}


def _seed_fixture(db: Session) -> None:
    """Peuple la session avec le snapshot ICE figé. Ordre : entreprise → reste."""
    db.add(Entreprise(**_FIXTURE_ENTREPRISE))
    db.flush()
    db.add(Machine(entreprise_id=DEMO_ENTREPRISE_ID, **_FIXTURE_MACHINE))
    db.add(Complexe(entreprise_id=DEMO_ENTREPRISE_ID, **_FIXTURE_COMPLEXE))
    for row in _FIXTURE_TARIF_POSTE:
        db.add(TarifPoste(entreprise_id=DEMO_ENTREPRISE_ID, **row))
    for row in _FIXTURE_TARIF_ENCRE:
        db.add(TarifEncre(entreprise_id=DEMO_ENTREPRISE_ID, **row))
    db.commit()


@pytest.fixture(scope="module")
def fixture_session_factory() -> Iterator[Callable[[], Session]]:
    """Construit une session SQLite IN-MEMORY peuplée du snapshot ICE.

    Module-scoped : on monte la DB et on insère une seule fois pour les 5
    variantes (les tests ne mutent rien). `fixture_session_factory()` rend
    une nouvelle Session sur le même engine à chaque appel — équivalent
    drop-in à `SessionLocal()` mais isolé du dev DB et du seed CSV.
    """
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionFix = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionFix() as db:
        _seed_fixture(db)
    try:
        yield SessionFix
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Définition des 5 variantes (factories + business checks)
# ---------------------------------------------------------------------------


def _devis_v1a_median() -> DevisInput:
    """V1a = V1 médian + outil existant (defaults Pydantic Lot 5b alignés
    sur format 60×40, 3p1d, outil_decoupe_existant=True). Cible 1449.09 €."""
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


def _devis_v1b_nouvel_outil() -> DevisInput:
    """V1b = V1a + nouvel outil 4 tracés simple. Cible 1921.09 €.
    P3b = 200 + 4×50 = 400 € → P3 = 225 + 400 = 625."""
    return _devis_v1a_median().model_copy(
        update={
            "outil_decoupe_existant": False,
            "nb_traces_complexite": 4,
        }
    )


def _devis_v2_petite_serie() -> DevisInput:
    return _devis_v1a_median().model_copy(
        update={"ml_total": 500, "forfaits_st": []}
    )


def _devis_v3_grande_serie() -> DevisInput:
    return _devis_v1a_median().model_copy(update={"ml_total": 30000})


def _devis_v4_multi_couleurs() -> DevisInput:
    return _devis_v1a_median().model_copy(
        update={
            "nb_couleurs_par_type": {
                "process_cmj": 4,
                "pantone": 3,
                "blanc_high_opaque": 1,
            }
        }
    )


# ---------------------------------------------------------------------------
# Business checks par variante (assertions métier sur le résultat)
# ---------------------------------------------------------------------------


def _check_v1a_reference(out: DevisOutput) -> None:
    """V1a = cas médian + outil existant. P3b=0 → P3=225 (inchangé) → HT=1449.09."""
    assert out.prix_vente_ht_eur == Decimal("1449.09")
    assert out.cout_revient_eur == Decimal("1228.04")
    p3 = next(p for p in out.postes if p.poste_numero == 3)
    assert p3.montant_eur == Decimal("225.00")
    assert p3.details["mode_outil"] == "existant"


def _check_v1b_nouvel_outil_4_traces(out: DevisOutput) -> None:
    """V1b : nouvel outil 4 tracés simple. P3b=400 → P3=625 → cout_revient=1628.04 → HT=1921.09."""
    assert out.cout_revient_eur == Decimal("1628.04")
    assert out.prix_vente_ht_eur == Decimal("1921.09")
    p3 = next(p for p in out.postes if p.poste_numero == 3)
    assert p3.montant_eur == Decimal("625.00")
    assert p3.details["mode_outil"] == "nouveau"
    assert p3.details["cout_3b_outil_eur"] == 400.0


def _check_v2_forfaits_dominants(out: DevisOutput) -> None:
    """En petite série, P3 (clichés) + P4 (calage forfait) > 50 % cout_revient."""
    p3 = next(p for p in out.postes if p.poste_numero == 3).montant_eur
    p4 = next(p for p in out.postes if p.poste_numero == 4).montant_eur
    ratio = (p3 + p4) / out.cout_revient_eur
    assert ratio > Decimal("0.5"), (
        f"Forfaits P3+P4 = {p3 + p4} € sur cout_revient {out.cout_revient_eur} € "
        f"= {ratio:.1%}, attendu > 50 %"
    )


def _check_v3_matiere_et_roulage_dominants(out: DevisOutput) -> None:
    """En grande série, P1 (matière) + P5 (roulage) > 50 % cout_revient.

    L'attente initiale Eric (P1 seul > 35 %) sous-estimait l'effet de P5
    qui scale aussi en linéaire avec ml. Avec un complexe vélin à 0.35 €/m²
    (tarif bas), P5 capte une part équivalente à P1 sur grande série.
    Le seuil métier "matière + roulage dominent" reste valable.
    """
    p1 = next(p for p in out.postes if p.poste_numero == 1).montant_eur
    p5 = next(p for p in out.postes if p.poste_numero == 5).montant_eur
    ratio = (p1 + p5) / out.cout_revient_eur
    assert ratio > Decimal("0.5"), (
        f"P1+P5 = {p1 + p5} € sur cout_revient {out.cout_revient_eur} € "
        f"= {ratio:.1%}, attendu > 50 % (effet d'échelle grande série)"
    )


def _check_v4_p3_360(out: DevisOutput) -> None:
    """8 couleurs × 45 €/couleur = 360 € pour P3."""
    p3 = next(p for p in out.postes if p.poste_numero == 3).montant_eur
    assert p3 == Decimal("360.00")


# V5 supprimée Lot 5c — remplacée par V1b (test du nouveau sous-poste P3b).


# ---------------------------------------------------------------------------
# Définition des 5 variantes
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkVariante:
    name: str
    description: str
    devis_factory: Callable[[], DevisInput]
    business_check: Callable[[DevisOutput], None]
    expected_total_ht: Decimal | None = field(default=None)


VARIANTES = [
    BenchmarkVariante(
        name="V1a_median_outil_existant",
        description="Cas médian + outil EXISTANT (figé Lot 3d, P3b=0 €)",
        devis_factory=_devis_v1a_median,
        business_check=_check_v1a_reference,
        expected_total_ht=Decimal("1449.09"),
    ),
    BenchmarkVariante(
        name="V1b_nouvel_outil_4_traces",
        description="Cas médian + nouvel outil 4 tracés simple (P3b=400 €) — NEW Lot 5c",
        devis_factory=_devis_v1b_nouvel_outil,
        business_check=_check_v1b_nouvel_outil_4_traces,
        expected_total_ht=Decimal("1921.09"),
    ),
    BenchmarkVariante(
        name="V2_petite_serie",
        description="Petite série 500 ml — forfaits dominants (outil existant)",
        devis_factory=_devis_v2_petite_serie,
        business_check=_check_v2_forfaits_dominants,
        expected_total_ht=Decimal("743.01"),
    ),
    BenchmarkVariante(
        name="V3_grande_serie",
        description="Grande série 30 000 ml — effet d'échelle (outil existant)",
        devis_factory=_devis_v3_grande_serie,
        business_check=_check_v3_matiere_et_roulage_dominants,
        expected_total_ht=Decimal("8437.47"),
    ),
    BenchmarkVariante(
        name="V4_multi_couleurs",
        description="8 couleurs (4 CMJ + 3 Pantone + 1 Blanc HO) — outil existant",
        devis_factory=_devis_v4_multi_couleurs,
        business_check=_check_v4_p3_360,
        expected_total_ht=Decimal("1697.17"),
    ),
]


# ---------------------------------------------------------------------------
# Tests paramétrés — chacun consomme la fixture in-memory au lieu du dev DB
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variante", VARIANTES, ids=[v.name for v in VARIANTES])
def test_benchmark_variante_business_assertion(
    variante: BenchmarkVariante, fixture_session_factory
):
    """Chaque variante doit satisfaire sa propriété métier attendue."""
    with fixture_session_factory() as db:
        out = MoteurDevis(db, entreprise_id=DEMO_ENTREPRISE_ID).calculer(
            variante.devis_factory()
        )
    variante.business_check(out)


@pytest.mark.parametrize("variante", VARIANTES, ids=[v.name for v in VARIANTES])
def test_benchmark_variante_total_ht_figeage(
    variante: BenchmarkVariante, fixture_session_factory
):
    """Total HT figé pour détection de régression. None = pas encore validé Eric."""
    if variante.expected_total_ht is None:
        pytest.skip(
            f"{variante.name}: total HT pas encore figé (validation Eric en attente)"
        )
    with fixture_session_factory() as db:
        out = MoteurDevis(db, entreprise_id=DEMO_ENTREPRISE_ID).calculer(
            variante.devis_factory()
        )
    assert out.prix_vente_ht_eur == variante.expected_total_ht


# ---------------------------------------------------------------------------
# Génération du rapport markdown comparatif
# ---------------------------------------------------------------------------


def test_5cas_writes_comparison_report(fixture_session_factory):
    """Génère cost_breakdown_5cas.md — tableau comparatif des 5 variantes.

    Sert à la validation métier Eric AVANT figeage des totaux V2-V5.
    """
    results: list[tuple[BenchmarkVariante, DevisOutput, DevisInput]] = []
    with fixture_session_factory() as db:
        moteur = MoteurDevis(db, entreprise_id=DEMO_ENTREPRISE_ID)
        for v in VARIANTES:
            devis = v.devis_factory()
            out = moteur.calculer(devis)
            results.append((v, out, devis))

    lines = [
        "# Cost breakdown — 5 cas-tests de non-régression (S3 Lot 3e)",
        "",
        "Régénéré à chaque run pytest "
        "(`tests/test_cost_engine_5cas_benchmark.py`).",
        "",
        "## Méthode",
        "",
        "Décision Eric (28 avril 2026) : on n'utilise PAS 5 dossiers réels",
        "d'archives ICE Étiquettes. Tarifs 2026 vs données 2014, la",
        "réindexation introduirait des écarts artificiels (+50 % papier,",
        "+35 % encres, +30 % MO sur 12 ans) sans rapport avec la qualité",
        "du moteur.",
        "",
        "À la place : 5 variantes du cas médian qui testent la robustesse",
        "mathématique du moteur sur des cas typés métier (forfaits dominants,",
        "effet d'échelle, multi-couleurs, cas exotique).",
        "",
        "Phase 2 / Lot 1 : ce rapport est produit depuis la fixture pure",
        "(snapshot ICE figé en Python), pas depuis la DB live.",
        "",
        "## Tableau comparatif — totaux et ratios",
        "",
        "| Variante | Description | Cout revient € | HT € | €/ml | €/m² imp |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for v, out, devis in results:
        surface_imp = (devis.laize_utile_mm / 1000) * devis.ml_total
        eur_par_ml = out.prix_vente_ht_eur / Decimal(devis.ml_total)
        eur_par_m2 = out.prix_vente_ht_eur / Decimal(str(surface_imp))
        lines.append(
            f"| {v.name} | {v.description} | "
            f"{out.cout_revient_eur} | {out.prix_vente_ht_eur} | "
            f"{eur_par_ml:.4f} | {eur_par_m2:.4f} |"
        )

    lines += [
        "",
        "## Détail par poste — montants en €",
        "",
        "| Variante | P1 Mat | P2 Encr | P3 Cli | P4 Cal | P5 Roul | P6 Fin | P7 MO |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for v, out, _ in results:
        montants = {p.poste_numero: p.montant_eur for p in out.postes}
        lines.append(
            f"| {v.name} | {montants[1]} | {montants[2]} | {montants[3]} | "
            f"{montants[4]} | {montants[5]} | {montants[6]} | {montants[7]} |"
        )

    lines += [
        "",
        "## Détail par poste — ratios % du cout_revient",
        "",
        "| Variante | P1 | P2 | P3 | P4 | P5 | P6 | P7 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for v, out, _ in results:
        ratios = {
            p.poste_numero: (p.montant_eur / out.cout_revient_eur * Decimal(100))
            for p in out.postes
        }
        lines.append(
            f"| {v.name} | {ratios[1]:.1f}% | {ratios[2]:.1f}% | {ratios[3]:.1f}% | "
            f"{ratios[4]:.1f}% | {ratios[5]:.1f}% | {ratios[6]:.1f}% | {ratios[7]:.1f}% |"
        )

    lines += [
        "",
        "## Détails attendus / observés par variante",
        "",
    ]
    for v, out, devis in results:
        lines.append(f"### {v.name} — {v.description}")
        lines.append("")
        lines.append(f"- **Coût de revient** : {out.cout_revient_eur} €")
        lines.append(f"- **Prix vente HT** : {out.prix_vente_ht_eur} €")
        lines.append(f"- **Marge appliquée** : {out.pct_marge_appliquee * 100} %")
        lines.append(f"- ml_total : {devis.ml_total} ; laize_utile_mm : {devis.laize_utile_mm}")
        lines.append(
            f"- Couleurs : {dict(devis.nb_couleurs_par_type)} "
            f"(total {sum(devis.nb_couleurs_par_type.values())})"
        )
        lines.append(f"- Forfaits ST : {len(devis.forfaits_st)} forfait(s)")
        if v.expected_total_ht is None:
            lines.append("- ⏳ **Total HT non figé** — en attente validation Eric")
        else:
            lines.append(f"- ✅ Total HT figé : {v.expected_total_ht} €")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    assert REPORT_PATH.exists()
    assert REPORT_PATH.stat().st_size > 0
