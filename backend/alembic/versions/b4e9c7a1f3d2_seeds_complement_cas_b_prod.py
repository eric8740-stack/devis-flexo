"""Cas B 2026-05-16 — convertir cylindres dents→mm + completer seeds tenant 1.

Audit prod via /api/admin/audit/db-seeds (16/05/2026) :
  - 5 cylindres avec developpe_mm = {72, 96, 104, 112, 144} (valeurs en
    DENTS — manquait la conversion ×3.175 vers mm réels).
  - 2 options seulement (pelliculage + vernis_selectif), 18 du catalogue
    master manquaient.
  - 0 matière.
  - Bareme effet_banane porte aussi developpe_mini_mm en dents (80, 96,
    104, 120, 160) — même bug.

Cette migration :
  1) UPDATE les cylindres existants : developpe_mm * 3.175 (garde-fou
     WHERE developpe_mm < 200 pour idempotence ceinture+bretelles).
  2) INSERT les 14 cylindres ICE manquants pour entreprise_id=1
     (en mm réels = dents × 3.175). WHERE NOT EXISTS pour ne pas dupliquer.
  3) INSERT les 18 options manquantes pour entreprise_id=1.
  4) INSERT 6 matières courantes pour entreprise_id=1.
  5) UPDATE bareme effet_banane existant pour entreprise_id=1 (réécrit
     bareme_data avec developpe_mini_mm en mm réels).

Toutes les opérations sont scopées entreprise_id=1 (Paysant & Fils). En
CI ou environnement vierge sans cette entreprise, la migration n'a rien
à faire (les WHERE skippent tout).

Revision ID: b4e9c7a1f3d2
Revises: a7c2d5e9f3b4
Create Date: 2026-05-16
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b4e9c7a1f3d2"
down_revision: Union[str, Sequence[str], None] = "a7c2d5e9f3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 14 cylindres ICE non encore seedés sur entreprise_id=1 (5 déjà présents :
# 72, 96, 104, 112, 144 en dents). Listés en dents pour lisibilité métier.
_CYLINDRES_ICE_A_INSERER_DENTS = [
    80, 82, 84, 86, 88, 90, 92, 98, 103, 116, 128, 132, 134, 136
]

# 18 options du catalogue master à ajouter (pelliculage + vernis_selectif
# déjà présents). Format : (code, libelle, categorie, description,
# ajoute_cliches, ajoute_couleurs, ajoute_outils_decoupe, groupes_couleurs_requis,
# modules_speciaux_requis, est_silhouette_auto, ajoute_temps_calage_min,
# coef_vitesse_impact, coef_gache_impact).
_OPTIONS_A_INSERER = [
    ("gaufrage", "Gaufrage / embossage", "Relief",
     "Création de relief par presse + outil dédié.",
     0, 0, 1, 0, ["gaufrage"], False, 20, 0.75, 1.12),
    ("dorure_chaud", "Dorure à chaud (hot foil)", "Finition",
     "Application feuille métallique par chaleur + pression.",
     1, 0, 0, 0, ["hot_stamping"], False, 25, 0.75, 1.15),
    ("dorure_froid", "Dorure à froid (cold foil)", "Finition",
     "Feuille métallique appliquée à froid via colle UV.",
     1, 0, 0, 0, ["cold_foil"], False, 15, 0.85, 1.10),
    ("back_print", "Impression sur colle (back-print)", "Impression",
     "Impression au verso du liner, visible à travers étiquette transparente.",
     1, 1, 0, 1, None, False, 12, 0.90, 1.05),
    ("impression_verso", "Impression verso complète", "Impression",
     "Impression CMJN verso du support (étiquettes transparentes).",
     0, 0, 0, 4, ["retournement_laize"], False, 20, 0.80, 1.10),
    ("numerotation", "Numérotation séquentielle", "Données variables",
     "Numéros uniques séquentiels (inkjet inline).",
     0, 0, 0, 0, ["inkjet"], False, 10, 0.90, 1.05),
    ("codes_variables", "Codes variables (QR, DataMatrix, EAN)", "Données variables",
     "Codes uniques par étiquette (inkjet UV inline).",
     0, 0, 0, 0, ["inkjet_uv"], False, 12, 0.88, 1.05),
    ("serialisation_pharma", "Sérialisation pharma (FMD)", "Réglementaire",
     "Sérialisation FMD/DSCSA avec validation BPF + traçabilité.",
     0, 0, 0, 0, ["inkjet_uv", "validation_bpf"], False, 15, 0.85, 1.08),
    ("predecoupe_perfo", "Pré-découpe / micro-perforation", "Découpe",
     "Outil de découpe ou perforation spécifique (silhouette).",
     0, 0, 1, 0, None, True, 15, 0.90, 1.05),
    ("decoupe_split_liner", "Découpe split-liner", "Découpe",
     "2e outil de découpe verso sous liner (machine 2 postes mini).",
     0, 0, 2, 0, None, True, 20, 0.80, 1.10),
    ("perforation_liner", "Perforation liner", "Découpe",
     "Outil verso perforant (machine 2 postes mini).",
     0, 0, 2, 0, None, False, 18, 0.85, 1.08),
    ("void_inviolable", "Étiquettes inviolables / VOID", "Sécurité",
     "Adhésif spécial qui laisse une marque 'VOID' au décollage.",
     0, 0, 0, 0, None, False, 8, 0.95, 1.05),
    ("hologramme", "Hologramme / anti-contrefaçon", "Sécurité",
     "Hot-stamping de paillette holographique anti-contrefaçon.",
     0, 0, 0, 0, ["hot_stamping"], False, 18, 0.80, 1.10),
    ("encre_invisible", "Encre invisible UV / thermochrome", "Encre spéciale",
     "Encre révélée par UV ou chaleur (sécurité, marketing).",
     1, 0, 0, 0, None, False, 10, 0.90, 1.05),
    ("serigraphie_inline", "Sérigraphie inline (opacité maxi)", "Impression",
     "Station sérigraphie en ligne (équipement rare).",
     0, 0, 0, 1, ["serigraphie"], False, 25, 0.70, 1.15),
    ("rfid_inline", "RFID inline", "Intelligent",
     "Incorporation de puces RFID en ligne.",
     0, 0, 0, 0, ["rfid"], False, 20, 0.80, 1.12),
    ("livret_booklet", "Étiquettes livret (booklet)", "Construction",
     "Étiquette dépliante via retournement laize + vernis spécial libérateur.",
     0, 0, 0, 2, ["retournement_laize", "vernis_liberateur"], False, 30, 0.70, 1.18),
    ("paravents_accordeon", "Pose en paravents / accordéon", "Conditionnement",
     "Pliage off-line en accordéon pour étiquettes en livret.",
     0, 0, 0, 0, ["pliage_offline"], False, 10, 0.95, 1.02),
]

# 6 matières par défaut demandées par Eric. Mapping vers slugs catalogue réel :
#   pe_blanc_opaque (80µ)        → PE_BLANC_60 (60µ, pas de 80µ dispo)
#   pp_transparent (50µ)         → BOPP_TRANSP_50 (BOPP = PP biorienté)
#   papier_semi_gloss (80g)      → PAP_COUCHE_BRILL_80
#   papier_thermique_top         → THERMIQUE_DIRECT_TOP
#   papier_velin_couche (70g)    → PAP_VELIN_70
#   bopp_argent_metallise (40µ)  → BOPP_METAL_50 (50µ, pas de 40µ dispo)
# Format : (code, libelle, categorie, sous_type, grammage_gm2, epaisseur_microns,
# adhesifs_compatibles, est_transparent, opacite_pct, certifications_sanitaires,
# certifications_env, notes_techniques)
_MATIERES_A_INSERER = [
    ("PE_BLANC_60", "PE blanc 60 microns",
     "film", "PE_blanc", None, 60, ["permanent"], False, 90.0, None, None,
     "Souple, idéal squeezable / bouteilles déformables"),
    ("BOPP_TRANSP_50", "BOPP transparent 50 microns",
     "film", "BOPP_transparent", None, 50,
     ["permanent", "contact_alimentaire"], True, 5.0,
     ["FDA", "EU_10_2011"], None, None),
    ("PAP_COUCHE_BRILL_80", "Papier couché brillant 80 g/m²",
     "papier", "couche_brillant", 80, None,
     ["permanent", "removable"], False, 95.0, None, ["FSC_mixte"], None),
    ("THERMIQUE_DIRECT_TOP", "Thermique direct Top — protégé",
     "thermique", "thermique_direct_top", 80, None,
     ["permanent", "removable"], False, 95.0, None, None,
     "Protégé contre solvants/abrasions — usage logistique"),
    ("PAP_VELIN_70", "Papier vélin non-couché 70 g/m²",
     "papier", "velin", 70, None, ["permanent"], False, 92.0, None,
     ["FSC_mixte"], None),
    ("BOPP_METAL_50", "BOPP métallisé 50 microns",
     "film", "BOPP_metallise", None, 50, ["permanent"], False, 100.0,
     None, None, None),
]

# Bareme effet_banane corrigé : developpe_mini_mm en mm réels (=dents × 3.175).
_BAREME_EFFET_BANANE_MM = [
    {"largeur_max_mm": 150, "developpe_mini_mm": 254.0},
    {"largeur_max_mm": 200, "developpe_mini_mm": 304.8},
    {"largeur_max_mm": 250, "developpe_mini_mm": 330.2},
    {"largeur_max_mm": 300, "developpe_mini_mm": 381.0},
    {"largeur_max_mm": 350, "developpe_mini_mm": 508.0},
    {"largeur_max_mm": 9999, "developpe_mini_mm": 508.0},
]

# Bareme effet_banane d'origine (en dents nommées mm) — pour downgrade
_BAREME_EFFET_BANANE_DENTS = [
    {"largeur_max_mm": 150, "developpe_mini_mm": 80},
    {"largeur_max_mm": 200, "developpe_mini_mm": 96},
    {"largeur_max_mm": 250, "developpe_mini_mm": 104},
    {"largeur_max_mm": 300, "developpe_mini_mm": 120},
    {"largeur_max_mm": 350, "developpe_mini_mm": 160},
    {"largeur_max_mm": 9999, "developpe_mini_mm": 160},
]


def _entreprise_exists(bind, entreprise_id: int) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM entreprise WHERE id = :eid"),
            {"eid": entreprise_id},
        ).first()
    )


def upgrade() -> None:
    bind = op.get_bind()

    # 1) UPDATE cylindres existants : dents → mm (garde-fou < 200)
    bind.execute(
        sa.text(
            "UPDATE cylindre_magnetique "
            "SET developpe_mm = developpe_mm * 3.175 "
            "WHERE developpe_mm < 200"
        )
    )

    # Si entreprise_id=1 n'existe pas (CI vierge), on s'arrête là.
    if not _entreprise_exists(bind, 1):
        return

    # 2) INSERT 14 cylindres ICE manquants pour entreprise_id=1
    for dents in _CYLINDRES_ICE_A_INSERER_DENTS:
        mm = round(dents * 3.175, 4)
        bind.execute(
            sa.text(
                "INSERT INTO cylindre_magnetique "
                "(entreprise_id, developpe_mm, nb_pc_10p, nb_pc_13p, "
                "nb_pc_2200, nb_pc_p5, actif) "
                "SELECT 1, :mm, 0, 0, 0, 0, true "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM cylindre_magnetique "
                "  WHERE entreprise_id = 1 AND developpe_mm = :mm"
                ")"
            ),
            {"mm": mm},
        )

    # 3) INSERT options manquantes
    for (code, lib, cat, desc, cli, coul, ods, gcr, modules, silhouette,
         tcal, cv, cg) in _OPTIONS_A_INSERER:
        bind.execute(
            sa.text(
                "INSERT INTO option_fabrication "
                "(entreprise_id, code, libelle, categorie, description, "
                "ajoute_cliches, ajoute_couleurs, ajoute_outils_decoupe, "
                "groupes_couleurs_requis, modules_speciaux_requis, "
                "est_silhouette_auto, ajoute_temps_calage_min, "
                "coef_vitesse_impact, coef_gache_impact, actif) "
                "SELECT 1, :code, :libelle, :cat, :desc, "
                ":cli, :coul, :ods, :gcr, :modules, :silhouette, :tcal, "
                ":cv, :cg, true "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM option_fabrication "
                "  WHERE entreprise_id = 1 AND code = :code"
                ")"
            ),
            {
                "code": code, "libelle": lib, "cat": cat, "desc": desc,
                "cli": cli, "coul": coul, "ods": ods, "gcr": gcr,
                "modules": json.dumps(modules) if modules is not None else None,
                "silhouette": silhouette, "tcal": tcal,
                "cv": cv, "cg": cg,
            },
        )

    # 4) INSERT matières
    for (code, lib, cat, sous_type, grm, eps, adh, transp, op_pct, cert_san,
         cert_env, notes) in _MATIERES_A_INSERER:
        bind.execute(
            sa.text(
                "INSERT INTO matiere "
                "(entreprise_id, code, libelle, categorie, sous_type, "
                "grammage_gm2, epaisseur_microns, adhesifs_compatibles, "
                "est_transparent, opacite_pct, certifications_sanitaires, "
                "certifications_env, notes_techniques, actif) "
                "SELECT 1, :code, :libelle, :cat, :sous_type, "
                ":grm, :eps, :adh, :transp, :op_pct, :cert_san, :cert_env, "
                ":notes, true "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM matiere "
                "  WHERE entreprise_id = 1 AND code = :code"
                ")"
            ),
            {
                "code": code, "libelle": lib, "cat": cat,
                "sous_type": sous_type, "grm": grm, "eps": eps,
                "adh": json.dumps(adh) if adh is not None else None,
                "transp": transp, "op_pct": op_pct,
                "cert_san": json.dumps(cert_san) if cert_san is not None else None,
                "cert_env": json.dumps(cert_env) if cert_env is not None else None,
                "notes": notes,
            },
        )

    # 5) UPDATE bareme effet_banane existant pour entreprise_id=1 (si présent)
    bind.execute(
        sa.text(
            "UPDATE bareme SET bareme_data = :data "
            "WHERE entreprise_id = 1 AND type = 'effet_banane'"
        ),
        {"data": json.dumps(_BAREME_EFFET_BANANE_MM)},
    )


def downgrade() -> None:
    bind = op.get_bind()

    if _entreprise_exists(bind, 1):
        # Reverse 5) : restaurer bareme effet_banane en dents
        bind.execute(
            sa.text(
                "UPDATE bareme SET bareme_data = :data "
                "WHERE entreprise_id = 1 AND type = 'effet_banane'"
            ),
            {"data": json.dumps(_BAREME_EFFET_BANANE_DENTS)},
        )

        # Reverse 4) : DELETE matières ajoutées
        for row in _MATIERES_A_INSERER:
            code = row[0]
            bind.execute(
                sa.text(
                    "DELETE FROM matiere "
                    "WHERE entreprise_id = 1 AND code = :code"
                ),
                {"code": code},
            )

        # Reverse 3) : DELETE options ajoutées
        for row in _OPTIONS_A_INSERER:
            code = row[0]
            bind.execute(
                sa.text(
                    "DELETE FROM option_fabrication "
                    "WHERE entreprise_id = 1 AND code = :code"
                ),
                {"code": code},
            )

        # Reverse 2) : DELETE cylindres ICE ajoutés
        for dents in _CYLINDRES_ICE_A_INSERER_DENTS:
            mm = round(dents * 3.175, 4)
            bind.execute(
                sa.text(
                    "DELETE FROM cylindre_magnetique "
                    "WHERE entreprise_id = 1 AND developpe_mm = :mm"
                ),
                {"mm": mm},
            )

    # Reverse 1) : diviser cylindres > 200 par 3.175. Garde-fou pour
    # ne pas re-traiter des cylindres déjà à des valeurs basses.
    bind.execute(
        sa.text(
            "UPDATE cylindre_magnetique "
            "SET developpe_mm = developpe_mm / 3.175 "
            "WHERE developpe_mm > 200"
        )
    )
