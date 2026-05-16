"""Catalogues defaults pour l'onboarding express Sprint 13 Lot S13.C.

Données seed importées dans le tenant à l'onboarding. Le user décoche
ce qu'il n'a pas, ajuste 2-3 paramètres clés, valide. L'objectif : sortir
de l'onboarding en moins de 10 min avec un catalogue exploitable.

Source des valeurs (sauf indication contraire) : CdC Sprint 13 + 28 ans
d'expertise ICE Étiquettes (Eric Paysant). Les coefficients vitesse/gâche
et les barèmes sont des DEFAULTS à ajuster par l'imprimerie (voir
CdC § "Valeurs defaults catalogue de base — à ajuster par chaque imprimerie").

Conventions :
  - `code` : identifiant interne (UI sélectionne par `code`, jamais par index).
  - `developpe_mm` : floats simples (la conversion Decimal se fait à l'insert
    pour éviter de mêler types et JSON serialization).
  - Aucun champ `entreprise_id` ici — il est injecté à l'onboarding selon
    le tenant connecté.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

# ============================================================================
# 1. CYLINDRES MAGNÉTIQUES — 19 standards ICE (CdC ligne 948)
# ============================================================================
# Parc ICE Étiquettes (Eric, 28 ans). Couvre 72 → 144 dents (≈ 229 → 457 mm
# développé physique) pour étiquettes standard.
# `nb_pc_*` (poses de chaque format PC) = 0 par défaut : l'imprimerie
# saisit son inventaire après. Le développé seul suffit au moteur
# d'optimisation pour scorer.
# Nomenclature ICE : les imprimeurs désignent un cylindre par son **nombre
# de dents** (pas son développé physique). La conversion vers le développé
# circonférentiel utilise un pas de 3.175 mm/dent (standard flexo).
#
# Les valeurs ci-dessous (72, 80, ..., 144) sont des DENTS. Le moteur
# d'optimisation, lui, travaille en mm (Z = circonférence physique du
# cylindre). On expose donc deux constantes :
#   - CYLINDRES_STANDARD_DENTS : nomenclature métier (source de vérité)
#   - CYLINDRES_STANDARD_MM     : valeurs converties pour la BDD et le moteur
#
# Cas réel 100×80 mm : avec cyl 104 dents = 330.2 mm, dev étiquette = 80,
# intervalle = 2 mm → N = floor(330.2 / 82) = 4 poses dev, intervalle
# réel = 330.2/4 − 80 = 2.55 mm (cohérent avec l'Excel métier d'Eric).
DENTS_TO_MM_FACTOR: Decimal = Decimal("3.175")

CYLINDRES_STANDARD_DENTS: list[int] = [
    72, 80, 82, 84, 86, 88, 90, 92, 96, 98,
    103, 104, 112, 116, 128, 132, 134, 136, 144,
]

# Développés physiques en mm, dérivés des dents. Source de vérité pour la
# BDD (colonne `cylindre_magnetique.developpe_mm`) et le moteur.
CYLINDRES_STANDARD_MM: list[float] = [
    float(Decimal(str(d)) * DENTS_TO_MM_FACTOR) for d in CYLINDRES_STANDARD_DENTS
]


# ============================================================================
# 2. MACHINES TYPES — 3 références marché (Mark Andy 2200, OMET XFlex 330,
#                                          Nilpeter FA-22)
# ============================================================================
# Specs constructeur indicatives. La VITESSE PRATIQUE
# (`vitesse_pratique_m_min`) reste SAISIE MANUELLEMENT par l'imprimerie
# car elle varie de 30 à 80+ m/min selon machine/atelier/matière. On
# pré-remplit une valeur réaliste "milieu de fourchette" qu'on attend
# de l'imprimeur qu'il ajuste à sa pratique.
MACHINES_DEFAULT: list[dict[str, Any]] = [
    {
        "code": "mark_andy_2200",
        "nom": "Mark Andy 2200",
        "marque": "Mark Andy",
        "modele": "2200",
        "repere_court": "2200",
        "laize_totale_mm": 330.0,
        "laize_utile_mm": 320.0,
        "nb_groupes_couleurs": 8,
        "nb_postes_decoupe": 1,
        "vitesse_nominale_constructeur_m_min": 250,
        "vitesse_pratique_m_min": 70,  # default à ajuster
        "cout_horaire_eur": 70.00,
        "options": ["UV", "vernis_general"],
        "type_encre_supportee": ["UV", "eau"],
        "notes": "Presse 8 groupes UV polyvalente — valeur marché. "
        "Pratique typique 60-80 m/min selon matière.",
    },
    {
        "code": "omet_xflex_330",
        "nom": "OMET XFlex 330",
        "marque": "OMET",
        "modele": "XFlex 330",
        "repere_court": "XFlex 330",
        "laize_totale_mm": 340.0,
        "laize_utile_mm": 330.0,
        "nb_groupes_couleurs": 10,
        "nb_postes_decoupe": 2,
        "vitesse_nominale_constructeur_m_min": 200,
        "vitesse_pratique_m_min": 80,
        "cout_horaire_eur": 95.00,
        "options": ["UV", "dorure_froid", "lamination", "retournement_laize"],
        "type_encre_supportee": ["UV", "eau"],
        "notes": "Presse 10 groupes avec 2 stations découpe + module "
        "retournement laize (livret/split-back possibles).",
    },
    {
        "code": "nilpeter_fa_22",
        "nom": "Nilpeter FA-22",
        "marque": "Nilpeter",
        "modele": "FA-22",
        "repere_court": "FA-22",
        "laize_totale_mm": 340.0,
        "laize_utile_mm": 330.0,
        "nb_groupes_couleurs": 8,
        "nb_postes_decoupe": 2,
        "vitesse_nominale_constructeur_m_min": 200,
        "vitesse_pratique_m_min": 75,
        "cout_horaire_eur": 90.00,
        "options": ["UV", "hot_stamping", "serigraphie"],
        "type_encre_supportee": ["UV", "eau", "solvant"],
        "notes": "Presse modulaire 8 groupes avec hot stamping + station "
        "sérigraphie inline disponible.",
    },
]


# ============================================================================
# 3. MATIÈRES — 30 matières courantes du marché flexo étiquettes
# ============================================================================
# Catégories : papier, film, thermique, synthetique, special.
# `est_transparent=True` déclenche automatiquement la règle "spot
# détection verso obligatoire" dans le moteur d'optimisation.
# `certifications_sanitaires` : ["FDA", "EU_10_2011", "BPF"]
# `certifications_env` : ["FSC_mixte", "PEFC", "ecolabel_eu"]
MATIERES_DEFAULT: list[dict[str, Any]] = [
    # --- Papiers couchés (5) ---
    {"code": "PAP_COUCHE_BRILL_80", "libelle": "Papier couché brillant 80 g/m²",
     "categorie": "papier", "sous_type": "couche_brillant", "grammage_gm2": 80,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["permanent", "removable"],
     "certifications_env": ["FSC_mixte"]},
    {"code": "PAP_COUCHE_BRILL_90", "libelle": "Papier couché brillant 90 g/m²",
     "categorie": "papier", "sous_type": "couche_brillant", "grammage_gm2": 90,
     "opacite_pct": 96.0, "adhesifs_compatibles": ["permanent", "removable"],
     "certifications_env": ["FSC_mixte"]},
    {"code": "PAP_COUCHE_BRILL_100", "libelle": "Papier couché brillant 100 g/m²",
     "categorie": "papier", "sous_type": "couche_brillant", "grammage_gm2": 100,
     "opacite_pct": 97.0, "adhesifs_compatibles": ["permanent"],
     "certifications_env": ["FSC_mixte", "PEFC"]},
    {"code": "PAP_COUCHE_MAT_80", "libelle": "Papier couché mat 80 g/m²",
     "categorie": "papier", "sous_type": "couche_mat", "grammage_gm2": 80,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["permanent", "removable"],
     "certifications_env": ["FSC_mixte"]},
    {"code": "PAP_COUCHE_MAT_90", "libelle": "Papier couché mat 90 g/m²",
     "categorie": "papier", "sous_type": "couche_mat", "grammage_gm2": 90,
     "opacite_pct": 96.0, "adhesifs_compatibles": ["permanent", "removable"],
     "certifications_env": ["FSC_mixte"]},

    # --- Papiers vélin/non-couchés (3) ---
    {"code": "PAP_VELIN_70", "libelle": "Papier vélin non-couché 70 g/m²",
     "categorie": "papier", "sous_type": "velin", "grammage_gm2": 70,
     "opacite_pct": 92.0, "adhesifs_compatibles": ["permanent"],
     "certifications_env": ["FSC_mixte"]},
    {"code": "PAP_VELIN_80", "libelle": "Papier vélin non-couché 80 g/m²",
     "categorie": "papier", "sous_type": "velin", "grammage_gm2": 80,
     "opacite_pct": 93.0, "adhesifs_compatibles": ["permanent"],
     "certifications_env": ["FSC_mixte", "PEFC"]},
    {"code": "PAP_KRAFT_90", "libelle": "Papier kraft brun 90 g/m²",
     "categorie": "papier", "sous_type": "kraft", "grammage_gm2": 90,
     "opacite_pct": 100.0, "adhesifs_compatibles": ["permanent"],
     "certifications_env": ["FSC_mixte", "PEFC"]},

    # --- BOPP (films polypropylène biorienté) (5) ---
    {"code": "BOPP_BLANC_50", "libelle": "BOPP blanc 50 microns",
     "categorie": "film", "sous_type": "BOPP_blanc", "epaisseur_microns": 50,
     "opacite_pct": 90.0, "adhesifs_compatibles": ["permanent", "contact_alimentaire"],
     "certifications_sanitaires": ["FDA", "EU_10_2011"]},
    {"code": "BOPP_BLANC_60", "libelle": "BOPP blanc 60 microns",
     "categorie": "film", "sous_type": "BOPP_blanc", "epaisseur_microns": 60,
     "opacite_pct": 92.0, "adhesifs_compatibles": ["permanent", "contact_alimentaire"],
     "certifications_sanitaires": ["FDA", "EU_10_2011"]},
    {"code": "BOPP_TRANSP_50", "libelle": "BOPP transparent 50 microns",
     "categorie": "film", "sous_type": "BOPP_transparent", "epaisseur_microns": 50,
     "est_transparent": True, "opacite_pct": 5.0,
     "adhesifs_compatibles": ["permanent", "contact_alimentaire"],
     "certifications_sanitaires": ["FDA", "EU_10_2011"]},
    {"code": "BOPP_TRANSP_60", "libelle": "BOPP transparent 60 microns",
     "categorie": "film", "sous_type": "BOPP_transparent", "epaisseur_microns": 60,
     "est_transparent": True, "opacite_pct": 5.0,
     "adhesifs_compatibles": ["permanent", "contact_alimentaire"],
     "certifications_sanitaires": ["FDA", "EU_10_2011"]},
    {"code": "BOPP_METAL_50", "libelle": "BOPP métallisé 50 microns",
     "categorie": "film", "sous_type": "BOPP_metallise", "epaisseur_microns": 50,
     "opacite_pct": 100.0, "adhesifs_compatibles": ["permanent"]},

    # --- PET (films polyester) (3) ---
    {"code": "PET_CLAIR_25", "libelle": "PET clair 25 microns",
     "categorie": "film", "sous_type": "PET_clair", "epaisseur_microns": 25,
     "est_transparent": True, "opacite_pct": 4.0,
     "adhesifs_compatibles": ["permanent", "haute_temperature"]},
    {"code": "PET_CLAIR_50", "libelle": "PET clair 50 microns",
     "categorie": "film", "sous_type": "PET_clair", "epaisseur_microns": 50,
     "est_transparent": True, "opacite_pct": 4.0,
     "adhesifs_compatibles": ["permanent", "haute_temperature"]},
    {"code": "PET_BLANC_50", "libelle": "PET blanc 50 microns",
     "categorie": "film", "sous_type": "PET_blanc", "epaisseur_microns": 50,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["permanent", "haute_temperature"]},

    # --- PE (polyéthylène) (2) ---
    {"code": "PE_BLANC_60", "libelle": "PE blanc 60 microns",
     "categorie": "film", "sous_type": "PE_blanc", "epaisseur_microns": 60,
     "opacite_pct": 90.0, "adhesifs_compatibles": ["permanent"],
     "notes_techniques": "Souple, idéal squeezable / bouteilles déformables"},
    {"code": "PE_TRANSP_50", "libelle": "PE transparent 50 microns",
     "categorie": "film", "sous_type": "PE_transparent", "epaisseur_microns": 50,
     "est_transparent": True, "opacite_pct": 8.0,
     "adhesifs_compatibles": ["permanent"]},

    # --- Thermique direct & ribbon (3) ---
    {"code": "THERMIQUE_DIRECT_TOP", "libelle": "Thermique direct Top — protégé",
     "categorie": "thermique", "sous_type": "thermique_direct_top", "grammage_gm2": 80,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["permanent", "removable"],
     "notes_techniques": "Protégé contre solvants/abrasions — usage logistique"},
    {"code": "THERMIQUE_DIRECT_ECO", "libelle": "Thermique direct éco",
     "categorie": "thermique", "sous_type": "thermique_direct_eco", "grammage_gm2": 75,
     "opacite_pct": 94.0, "adhesifs_compatibles": ["permanent"]},
    {"code": "THERMIQUE_TRANSFERT_PAP",
     "libelle": "Thermique transfert papier (vellum)",
     "categorie": "thermique", "sous_type": "thermique_transfert", "grammage_gm2": 80,
     "opacite_pct": 94.0, "adhesifs_compatibles": ["permanent"]},

    # --- Synthétiques (3) ---
    {"code": "POLYART_75", "libelle": "Polyart synthétique 75 microns",
     "categorie": "synthetique", "sous_type": "polyolefine", "epaisseur_microns": 75,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["permanent"],
     "notes_techniques": "Résistant déchirure/eau — extérieur, chantier"},
    {"code": "TYVEK_75", "libelle": "Tyvek (HDPE flashspun) 75 microns",
     "categorie": "synthetique", "sous_type": "tyvek", "epaisseur_microns": 75,
     "opacite_pct": 98.0, "adhesifs_compatibles": ["permanent"]},
    {"code": "PVC_VINYLE_80", "libelle": "PVC vinyle 80 microns",
     "categorie": "synthetique", "sous_type": "PVC_vinyle", "epaisseur_microns": 80,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["permanent", "removable"]},

    # --- Spéciaux (6) ---
    {"code": "ALU_VINYLE_50", "libelle": "Aluminium vinyle 50 microns",
     "categorie": "special", "sous_type": "alu_vinyle", "epaisseur_microns": 50,
     "opacite_pct": 100.0, "adhesifs_compatibles": ["permanent", "haute_temperature"]},
    {"code": "VOID_BLANC_50", "libelle": "VOID inviolable blanc 50 microns",
     "categorie": "special", "sous_type": "VOID", "epaisseur_microns": 50,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["void_inviolable"],
     "notes_techniques": "Étiquettes sécurité — laisse marque 'VOID' au décollage"},
    {"code": "FREEZER_BLANC_70",
     "libelle": "Étiquette grand froid (freezer) 70 microns",
     "categorie": "special", "sous_type": "freezer", "epaisseur_microns": 70,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["grand_froid"],
     "notes_techniques": "Adhésif tient jusqu'à -40°C"},
    {"code": "STRUCTURE_SECU",
     "libelle": "Étiquette structure sécurité (hologramme prêt)",
     "categorie": "special", "sous_type": "securite", "epaisseur_microns": 60,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["permanent"]},
    {"code": "WASHABLE_75", "libelle": "Étiquette lavable 75 microns",
     "categorie": "special", "sous_type": "washable", "epaisseur_microns": 75,
     "opacite_pct": 95.0, "adhesifs_compatibles": ["washable"],
     "notes_techniques": "Décolle proprement à l'eau chaude/lessive"},
    {"code": "WINE_COTTON_90", "libelle": "Étiquette vin coton/lin 90 g/m²",
     "categorie": "special", "sous_type": "vin_coton", "grammage_gm2": 90,
     "opacite_pct": 96.0, "adhesifs_compatibles": ["humide", "wet_strength"],
     "certifications_env": ["FSC_mixte"],
     "notes_techniques": "Tient à l'immersion seau à glace"},
]


# ============================================================================
# 4. OPTIONS DE FABRICATION — 20 options standard (CdC table lignes 1034-1053)
# ============================================================================
# Coefficients vitesse/gâche + temps calage suppl. issus du tableau CdC
# "Valeurs defaults catalogue de base" (lignes 1101-1115) là où il existe.
# Sinon : valeurs raisonnables alignées sur la même logique.
OPTIONS_FABRICATION_DEFAULT: list[dict[str, Any]] = [
    {"code": "vernis_selectif", "libelle": "Vernis sélectif",
     "categorie": "Impression",
     "description": "Vernis localisé pour effets brillance/mat. +1 cliché, +1 couleur.",
     "ajoute_cliches": 1, "ajoute_couleurs": 1, "groupes_couleurs_requis": 1,
     "ajoute_temps_calage_min": 10, "coef_vitesse_impact": 0.95,
     "coef_gache_impact": 1.03},
    {"code": "pelliculage", "libelle": "Pelliculage / lamination",
     "categorie": "Finition",
     "description": "Film de protection laminé sur l'impression.",
     "modules_speciaux_requis": ["lamination"],
     "ajoute_temps_calage_min": 12, "coef_vitesse_impact": 0.90,
     "coef_gache_impact": 1.05},
    {"code": "gaufrage", "libelle": "Gaufrage / embossage",
     "categorie": "Relief",
     "description": "Création de relief par presse + outil dédié.",
     "ajoute_outils_decoupe": 1,
     "modules_speciaux_requis": ["gaufrage"],
     "ajoute_temps_calage_min": 20, "coef_vitesse_impact": 0.75,
     "coef_gache_impact": 1.12},
    {"code": "dorure_chaud", "libelle": "Dorure à chaud (hot foil)",
     "categorie": "Finition",
     "description": "Application feuille métallique par chaleur + pression.",
     "ajoute_cliches": 1,
     "modules_speciaux_requis": ["hot_stamping"],
     "ajoute_temps_calage_min": 25, "coef_vitesse_impact": 0.75,
     "coef_gache_impact": 1.15},
    {"code": "dorure_froid", "libelle": "Dorure à froid (cold foil)",
     "categorie": "Finition",
     "description": "Feuille métallique appliquée à froid via colle UV.",
     "ajoute_cliches": 1,
     "modules_speciaux_requis": ["cold_foil"],
     "ajoute_temps_calage_min": 15, "coef_vitesse_impact": 0.85,
     "coef_gache_impact": 1.10},
    {"code": "back_print", "libelle": "Impression sur colle (back-print)",
     "categorie": "Impression",
     "description": "Impression au verso du liner, visible à travers étiquette transparente.",
     "ajoute_cliches": 1, "ajoute_couleurs": 1, "groupes_couleurs_requis": 1,
     "ajoute_temps_calage_min": 12, "coef_vitesse_impact": 0.90,
     "coef_gache_impact": 1.05},
    {"code": "impression_verso", "libelle": "Impression verso complète",
     "categorie": "Impression",
     "description": "Impression CMJN verso du support (étiquettes transparentes).",
     "groupes_couleurs_requis": 4,
     "modules_speciaux_requis": ["retournement_laize"],
     "ajoute_temps_calage_min": 20, "coef_vitesse_impact": 0.80,
     "coef_gache_impact": 1.10},
    {"code": "numerotation", "libelle": "Numérotation séquentielle",
     "categorie": "Données variables",
     "description": "Numéros uniques séquentiels (inkjet inline).",
     "modules_speciaux_requis": ["inkjet"],
     "ajoute_temps_calage_min": 10, "coef_vitesse_impact": 0.90,
     "coef_gache_impact": 1.05},
    {"code": "codes_variables",
     "libelle": "Codes variables (QR, DataMatrix, EAN)",
     "categorie": "Données variables",
     "description": "Codes uniques par étiquette (inkjet UV inline).",
     "modules_speciaux_requis": ["inkjet_uv"],
     "ajoute_temps_calage_min": 12, "coef_vitesse_impact": 0.88,
     "coef_gache_impact": 1.05},
    {"code": "serialisation_pharma", "libelle": "Sérialisation pharma (FMD)",
     "categorie": "Réglementaire",
     "description": "Sérialisation FMD/DSCSA avec validation BPF + traçabilité.",
     "modules_speciaux_requis": ["inkjet_uv", "validation_bpf"],
     "ajoute_temps_calage_min": 15, "coef_vitesse_impact": 0.85,
     "coef_gache_impact": 1.08},
    {"code": "predecoupe_perfo", "libelle": "Pré-découpe / micro-perforation",
     "categorie": "Découpe",
     "description": "Outil de découpe ou perforation spécifique (silhouette).",
     "ajoute_outils_decoupe": 1, "est_silhouette_auto": True,
     "ajoute_temps_calage_min": 15, "coef_vitesse_impact": 0.90,
     "coef_gache_impact": 1.05},
    {"code": "decoupe_split_liner", "libelle": "Découpe split-liner",
     "categorie": "Découpe",
     "description": "2e outil de découpe verso sous liner (machine 2 postes mini).",
     "ajoute_outils_decoupe": 2, "est_silhouette_auto": True,
     "ajoute_temps_calage_min": 20, "coef_vitesse_impact": 0.80,
     "coef_gache_impact": 1.10},
    {"code": "perforation_liner", "libelle": "Perforation liner",
     "categorie": "Découpe",
     "description": "Outil verso perforant (machine 2 postes mini).",
     "ajoute_outils_decoupe": 2,
     "ajoute_temps_calage_min": 18, "coef_vitesse_impact": 0.85,
     "coef_gache_impact": 1.08},
    {"code": "void_inviolable",
     "libelle": "Étiquettes inviolables / VOID",
     "categorie": "Sécurité",
     "description": "Adhésif spécial qui laisse une marque 'VOID' au décollage.",
     "ajoute_temps_calage_min": 8, "coef_vitesse_impact": 0.95,
     "coef_gache_impact": 1.05},
    {"code": "hologramme", "libelle": "Hologramme / anti-contrefaçon",
     "categorie": "Sécurité",
     "description": "Hot-stamping de paillette holographique anti-contrefaçon.",
     "modules_speciaux_requis": ["hot_stamping"],
     "ajoute_temps_calage_min": 18, "coef_vitesse_impact": 0.80,
     "coef_gache_impact": 1.10},
    {"code": "encre_invisible",
     "libelle": "Encre invisible UV / thermochrome",
     "categorie": "Encre spéciale",
     "description": "Encre révélée par UV ou chaleur (sécurité, marketing).",
     "ajoute_cliches": 1,
     "ajoute_temps_calage_min": 10, "coef_vitesse_impact": 0.90,
     "coef_gache_impact": 1.05},
    {"code": "serigraphie_inline",
     "libelle": "Sérigraphie inline (opacité maxi)",
     "categorie": "Impression",
     "description": "Station sérigraphie en ligne (équipement rare).",
     "groupes_couleurs_requis": 1,
     "modules_speciaux_requis": ["serigraphie"],
     "ajoute_temps_calage_min": 25, "coef_vitesse_impact": 0.70,
     "coef_gache_impact": 1.15},
    {"code": "rfid_inline", "libelle": "RFID inline",
     "categorie": "Intelligent",
     "description": "Incorporation de puces RFID en ligne.",
     "modules_speciaux_requis": ["rfid"],
     "ajoute_temps_calage_min": 20, "coef_vitesse_impact": 0.80,
     "coef_gache_impact": 1.12},
    {"code": "livret_booklet", "libelle": "Étiquettes livret (booklet)",
     "categorie": "Construction",
     "description": "Étiquette dépliante via retournement laize + vernis spécial libérateur.",
     "groupes_couleurs_requis": 2,
     "modules_speciaux_requis": ["retournement_laize", "vernis_liberateur"],
     "ajoute_temps_calage_min": 30, "coef_vitesse_impact": 0.70,
     "coef_gache_impact": 1.18},
    {"code": "paravents_accordeon",
     "libelle": "Pose en paravents / accordéon",
     "categorie": "Conditionnement",
     "description": "Pliage off-line en accordéon pour étiquettes en livret.",
     "modules_speciaux_requis": ["pliage_offline"],
     "ajoute_temps_calage_min": 10, "coef_vitesse_impact": 0.95,
     "coef_gache_impact": 1.02},
]


# ============================================================================
# 5. BARÈMES — 4 barèmes ICE par défaut (CdC § règles métier)
# ============================================================================
# Ces 4 barèmes sont dupliqués pour chaque tenant à l'onboarding (FK
# entreprise_id NOT NULL). L'imprimerie peut ensuite ajuster les paliers
# selon ses machines (récentes vs anciennes).
BAREMES_DEFAULT: list[dict[str, Any]] = [
    {
        "code": "echenillage_ice",
        "type": "echenillage",
        "nom": "Échenillage ICE standard",
        "bareme_data": [
            {"intervalle_max_mm": 2, "qualite": "parfait",
             "coef_vitesse": 1.00, "coef_gache": 1.00, "score": 100},
            {"intervalle_max_mm": 3, "qualite": "parfait",
             "coef_vitesse": 1.00, "coef_gache": 1.00, "score": 100},
            {"intervalle_max_mm": 4, "qualite": "bien",
             "coef_vitesse": 1.00, "coef_gache": 1.00, "score": 85},
            {"intervalle_max_mm": 5, "qualite": "complique",
             "coef_vitesse": 0.70, "coef_gache": 1.08, "score": 50},
            {"intervalle_max_mm": 6, "qualite": "mauvais",
             "coef_vitesse": 0.60, "coef_gache": 1.12, "score": 30},
            {"intervalle_max_mm": 7, "qualite": "mauvais",
             "coef_vitesse": 0.55, "coef_gache": 1.15, "score": 20},
            {"intervalle_max_mm": 8, "qualite": "critique",
             "coef_vitesse": 0.50, "coef_gache": 1.20, "score": 10},
            {"intervalle_max_mm": 999, "qualite": "critique",
             "coef_vitesse": 0.40, "coef_gache": 1.25, "score": 5},
        ],
        "notes": "Courbe expertise ICE — à ajuster si machines récentes/anciennes.",
    },
    {
        "code": "effet_banane_ice",
        "type": "effet_banane",
        "nom": "Effet banane ICE",
        # Cas B du 2026-05-16 : `developpe_mini_mm` était auparavant exprimé
        # en dents (80, 96, ..., 160), comme CYLINDRES_STANDARD_MM. Converti
        # en mm réels via ×3.175 pour rester homogène avec
        # `cylindre_magnetique.developpe_mm` (vraies mm).
        "bareme_data": [
            {"largeur_max_mm": 150, "developpe_mini_mm": 254.0},   # 80 dents
            {"largeur_max_mm": 200, "developpe_mini_mm": 304.8},   # 96 dents
            {"largeur_max_mm": 250, "developpe_mini_mm": 330.2},   # 104 dents
            {"largeur_max_mm": 300, "developpe_mini_mm": 381.0},   # 120 dents
            {"largeur_max_mm": 350, "developpe_mini_mm": 508.0},   # 160 dents
            {"largeur_max_mm": 9999, "developpe_mini_mm": 508.0},  # idem
        ],
        "notes": "Saut non-linéaire 250-300 vs 300-350 mm (seuil rigidité physique).",
    },
    {
        "code": "confort_roulage_ice",
        "type": "confort_roulage",
        "nom": "Confort de roulage ICE",
        "bareme_data": {
            "bareme_rayon": [
                {"rayon_max_mm": 0, "coef": 0.75},
                {"rayon_max_mm": 1, "coef": 0.90},
                {"rayon_max_mm": 2, "coef": 1.00},
                {"rayon_max_mm": 3, "coef": 1.02},
                {"rayon_max_mm": 5, "coef": 1.08},
                {"rayon_max_mm": 10, "coef": 1.12},
                {"rayon_max_mm": 999, "coef": 1.12},
            ],
            "coef_forme_courbe": 1.15,
            "coef_quinconce": 1.10,
        },
        "notes": "Angles vifs pénalisent ; rond/ovale = +15%, quinconce = +10%.",
    },
    {
        "code": "compensation_laize_dev_ice",
        "type": "compensation_laize_dev",
        "nom": "Compensation laize/dev ICE",
        "bareme_data": [
            {"intervalle_dev_min_mm": 0, "intervalle_dev_max_mm": 4,
             "intervalle_laize_souhaitable_mm": 3,
             "coef_vitesse_si_atteint": None,
             "notes": "Aucun bonus nécessaire (déjà optimal)"},
            {"intervalle_dev_min_mm": 4, "intervalle_dev_max_mm": 5,
             "intervalle_laize_souhaitable_mm": 4,
             "coef_vitesse_si_atteint": 0.85,
             "notes": "Coef vitesse passe de 0,70 à 0,85"},
            {"intervalle_dev_min_mm": 5, "intervalle_dev_max_mm": 6,
             "intervalle_laize_souhaitable_mm": 5,
             "coef_vitesse_si_atteint": 0.80,
             "notes": "Coef vitesse passe de 0,60 à 0,80"},
            {"intervalle_dev_min_mm": 6, "intervalle_dev_max_mm": 8,
             "intervalle_laize_souhaitable_mm": 6,
             "coef_vitesse_si_atteint": 0.70,
             "notes": "Coef vitesse passe de 0,50 à 0,70"},
            {"intervalle_dev_min_mm": 8, "intervalle_dev_max_mm": 9999,
             "intervalle_laize_souhaitable_pct_dev": 70,
             "coef_vitesse_si_atteint": 0.60,
             "notes": "70 % de l'intervalle dev ; passe de 0,40 à 0,60"},
        ],
        "notes": "Compensation par élargissement laize pour récupérer pénalité vitesse.",
    },
]


# ============================================================================
# Helpers d'accès rapide par code (UI ↔ backend mapping)
# ============================================================================


def get_machine_by_code(code: str) -> dict[str, Any] | None:
    for m in MACHINES_DEFAULT:
        if m["code"] == code:
            return m
    return None


def get_matiere_by_code(code: str) -> dict[str, Any] | None:
    for m in MATIERES_DEFAULT:
        if m["code"] == code:
            return m
    return None


def get_option_by_code(code: str) -> dict[str, Any] | None:
    for o in OPTIONS_FABRICATION_DEFAULT:
        if o["code"] == code:
            return o
    return None


def get_bareme_by_code(code: str) -> dict[str, Any] | None:
    for b in BAREMES_DEFAULT:
        if b["code"] == code:
            return b
    return None


# Sanity checks au chargement (fail fast si désynchro)
assert len(CYLINDRES_STANDARD_DENTS) == 19, (
    f"19 cylindres attendus, {len(CYLINDRES_STANDARD_DENTS)} trouvés"
)
assert len(CYLINDRES_STANDARD_MM) == 19, (
    "CYLINDRES_STANDARD_MM doit être dérivé des dents — incohérence."
)
assert all(c > 200 for c in CYLINDRES_STANDARD_MM), (
    "Les développés en mm doivent être > 200 — sinon ce sont des dents, "
    "pas des mm (cf. fix Cas B du 2026-05-16)."
)
assert len(MACHINES_DEFAULT) == 3, (
    f"3 machines attendues, {len(MACHINES_DEFAULT)} trouvées"
)
assert len(MATIERES_DEFAULT) == 30, (
    f"30 matières attendues, {len(MATIERES_DEFAULT)} trouvées"
)
assert len(OPTIONS_FABRICATION_DEFAULT) == 20, (
    f"20 options attendues, {len(OPTIONS_FABRICATION_DEFAULT)} trouvées"
)
assert len(BAREMES_DEFAULT) == 4, (
    f"4 barèmes attendus, {len(BAREMES_DEFAULT)} trouvés"
)
