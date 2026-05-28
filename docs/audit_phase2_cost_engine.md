# Audit Phase 2 — Config-driven vs hardcodé (cost_engine)

**Date** : 2026-05-28 · **Branche** : `main` (HEAD `dd2897f`) · **Type** : lecture seule.
**Objectif** : cartographier chaque input du cost_engine pour scoper la Phase 2 (brancher le moteur sur les configs par entreprise — tables Stratégique livrées en Phase 1) sans rien casser.

---

## TL;DR

**Aucun input du cost_engine n'est lu depuis les tables Stratégique (Phase 1).** Tout vient du seed `tarif_poste` (~ICE) + `Machine` (parc) + `TarifEncre` + `Complexe`, plus `Entreprise.pct_marge_defaut` pour la marge. **Phase 1 a livré les tables ; Phase 2 = câblage**. Le benchmark V1a tourne sur la DB seedée (`entreprise_id=1`, complexe id=31), donc **toute édition Stratégique du tenant démo modifie le benchmark** — il faut le découpler en fixture pure avant Phase 2.

---

## Livrable 1 — Tableau de cartographie

`mo_prix_horaire`, `roulage_prix_horaire` etc. = clés exactes seedées dans `seeds/tarif_poste.csv`. Toutes les lectures `tarif_poste` passent par `get_by_cle(db, cle, entreprise_id)` (déjà scopée tenant).

| Poste | Input (variable) | Valeur observée (seed/DB) | Source actuelle (code) | Config Stratégique existante ? | Action Phase 2 |
|---|---|---|---|---|---|
| **P1 Matière** | `prix_m2_eur` du complexe sélectionné | varie par complexe (BOPP 1.45, vélin 0.35…) | `complexe.prix_m2_eur` | non — par MATIÈRE, pas par tenant ; reste un catalogue Stratégique « Complexes & Matières » (cf. UI livrée) | ✅ aucune action — catalogue déjà éditable |
| **P1 Matière** | `grammage_g_m2` du complexe | varie par complexe (Numeric depuis Lot 1) | `complexe.grammage_g_m2` | idem (catalogue) | ✅ aucune action |
| **P1 Matière** | `marge_confort_roulage_mm` | **10 mm** | `TarifPoste.cle="marge_confort_roulage_mm"` | **non** — ni `ConfigCouts` ni `ConfigRoulage` ne porte cette marge globale | 🆕 **créer champ** sur `ConfigRoulage` (ou `ConfigCouts.marge_confort_roulage_mm`). Brancher P1. |
| **P1 Matière** | `matiere_prix_kg_defaut` (fallback) | **1.75 €/kg** | `TarifPoste.cle="matiere_prix_kg_defaut"` | non | 🟡 **mineur** — fallback rarement utilisé (complexe.prix_m2_eur prioritaire). À pousser sur `ConfigCouts` ou à supprimer (le catalogue matière couvre déjà). |
| **P2 Encres** | `prix_kg_defaut` par type | varie par `type_encre` | `TarifEncre.prix_kg_defaut` | non — catalogue éditable par type ; **API GET exposée** en read-only (`/api/tarif-encre`) | 🟡 exposer écriture (PUT/POST) Stratégique. Pas de champ Config*. |
| **P2 Encres** | `ratio_g_m2_couleur` par type | défaut 2.000 g/m²/couleur | `TarifEncre.ratio_g_m2_couleur` | idem (catalogue) | 🟡 idem (écriture catalogue) |
| **P3 Clichés/Outil** | `cliche_prix_couleur` | **45 €/couleur** | `TarifPoste.cle="cliche_prix_couleur"` | non | 🆕 **créer champ** sur `ConfigCouts` (ou table dédiée Clichés). |
| **P3 Clichés/Outil** | `outil_base_eur` | **200 €** | `TarifPoste.cle="outil_base_eur"` | non | 🆕 idem |
| **P3 Clichés/Outil** | `outil_par_trace_eur` | **50 €/trace** | `TarifPoste.cle="outil_par_trace_eur"` | non | 🆕 idem |
| **P3 Clichés/Outil** | `surcout_forme_speciale_pct` | **1.40** (×40 %) | `TarifPoste.cle="surcout_forme_speciale_pct"` | non | 🆕 idem |
| **P4 Calage** | `calage_forfait` | **225 €/devis** | `TarifPoste.cle="calage_forfait"` | non — `ConfigChangements` couvre couleur/format/nettoyage **séparément**, pas le forfait calage devis | 🆕 **créer champ** `ConfigCouts.calage_forfait_eur` OU rediriger P4 vers la somme `ConfigChangements.*_cout_eur` (refonte métier — hors Phase 2 simple). |
| **P5 Roulage** | `vitesse_moyenne_m_h` machine | varie par machine | `Machine.vitesse_moyenne_m_h` | non — par MACHINE, géré sur la page Machines (acquis) | ✅ aucune action |
| **P5 Roulage** | `roulage_prix_horaire` | **375 €/h** | `TarifPoste.cle="roulage_prix_horaire"` | **partiel** — `ConfigCouts.cout_exploitation_machine_eur_h` existe (défaut 50 €/h) mais **non lue par P5**. ⚠️ Doublon. | 🔧 **brancher P5 sur `ConfigCouts.cout_exploitation_machine_eur_h`** OU garder une dichotomie (cf. Q4). |
| **P6 Finitions** | `finitions_prix_m2` | **0.125 €/m²** | `TarifPoste.cle="finitions_prix_m2"` | non | 🆕 **créer champ** `ConfigCouts.finitions_prix_m2` |
| **P6 Finitions** | `forfaits_st[]` | saisi par devis | `devis.forfaits_st` (input) | n/a (saisie devis) | ✅ aucune action |
| **P7 MO** | `duree_calage_h` machine | varie par machine | `Machine.duree_calage_h` | non — par MACHINE | ✅ aucune action |
| **P7 MO** | `vitesse_moyenne_m_h` machine | varie par machine | `Machine.vitesse_moyenne_m_h` | non | ✅ aucune action |
| **P7 MO** | `mo_prix_horaire` | **70 €/h** | `TarifPoste.cle="mo_prix_horaire"` | **`ConfigCouts.cout_operateur_eur_h`** (défaut 25 €/h) **non lue** par P7 | 🔧 **brancher P7 sur `ConfigCouts.cout_operateur_eur_h`** |
| **Marge globale** | `pct_marge_defaut` | varie par entreprise | `Entreprise.pct_marge_defaut` (singleton) | **`ConfigCouts.marge_standard_pct`** (défaut 35 %) **non lue** | 🔧 **brancher orchestrator sur `ConfigCouts.marge_standard_pct`**. ⚠️ voir aussi bug multi-tenant ci-dessous. |
| **Marge fallback** | `PCT_MARGE_FALLBACK` | **0.18** (hard) | const Python dans `orchestrator.py:39` | non | 🟡 retirer le hard-code une fois `ConfigCouts.marge_standard_pct` branchée (la config a un défaut neutre 35 %). |
| **Aucun input** | `ConfigChangements.*` | toutes valeurs (15/12.50, 25/18, 45/35) | seed Phase 1 | ✅ existe | ❌ **non consommée par le moteur** — Phase 2 doit décider : nouveau modèle P4 détaillé (cf. note historique poste_4_calage.py) ou table d'usage futur (PDF, planning) ? |
| **Aucun input** | `ConfigRoulage.*` (debit/mode/rebut) | seed (A5 hélic. 280 mm/s 3 %, A4 alt. 250 mm/s 3 %) | seed Phase 1 | ✅ existe | ❌ **non consommée par le moteur**. P5 utilise `Machine.vitesse_moyenne_m_h` (m/h, indépendant du format). Phase 2 : décider si P5 doit pondérer la vitesse machine par `ConfigRoulage.debit_mm_s` par format (changement de formule) ou si la table reste informative pour le planning. |
| **Aucun input** | `ConfigCouts.cout_energies_eur_h` | 3.50 €/h | seed Phase 1 | ✅ existe | ❌ aucun poste ne lit l'énergie séparément — actuellement noyée dans `roulage_prix_horaire`. Phase 2 : décider si P5 décompose machine + énergie séparément. |
| **Aucun input** | `ConfigCouts.cout_fixe_atelier_eur_mois` / `_maintenance_eur_mois` | 2500 / 800 | seed Phase 1 | ✅ existe | ❌ aucun poste ne lit les coûts fixes — Phase 2 : décider si un FG est ajouté (ou si `Entreprise.pct_fg` reste la voie). |
| **Aucun input** | `ConfigCouts.buffer_rebut_pct` / `buffer_setup_pct` | 2.5 % / 1.0 % | seed Phase 1 | ✅ existe | ❌ aucun poste ne lit les buffers — Phase 2 : décider si quantité produite = quantité commandée × (1 + buffer_rebut). Aujourd'hui le moteur ne gère pas le rebut. |

### Notes hors périmètre

- `app/services/optimisation/bat_calculs.py` : **ne consomme aucun tarif** (calculs géométriques laize papier / mandrin / sens d'enroulement) — pas concerné par Phase 2.
- `app/services/optimisation/moteur.py` + règles : zéro lecture `tarif_*` ni `ConfigCouts/Roulage/Changements` ; seul `type Machine.cout_horaire_eur` figure dans `types.py` (modèle Pydantic) mais **n'est pas utilisé pour calculer un prix** — c'est de l'info de catalogue. Hors Phase 2.
- `rotation_se.py` / convention 8 sens : explicitement hors périmètre (rappel brief).

---

## Livrable 2 — Réponses aux 5 questions

### Q1 — Quels inputs sont **déjà** lus depuis les configs Stratégique (acquis Phase 1) ?

**Aucun.** Phase 1 a livré les trois tables (`ConfigCouts`, `ConfigRoulage`, `ConfigChangements`) + l'API `/api/strategique/*` + l'UI 7 sections, **mais le cost_engine n'a pas encore été branché** (Phase 2 = ce branchement). Le moteur lit toujours `TarifPoste` (clés seedées) + `Machine` + `TarifEncre` + `Complexe` + `Entreprise.pct_marge_defaut`.

### Q2 — Quels inputs sont **encore en dur / dérivés du seed** (ICE) ?

Tous les paramètres tarifaires globaux du tenant. Liste exacte :

| Clé seed | Valeur ICE | Lu par |
|---|---|---|
| `matiere_prix_kg_defaut` | 1.75 €/kg | P1 (fallback uniquement, complexe.prix_m2_eur prioritaire) |
| `marge_confort_roulage_mm` | 10 mm | P1 |
| `cliche_prix_couleur` | 45 €/couleur | P3a |
| `outil_base_eur` | 200 € | P3b |
| `outil_par_trace_eur` | 50 €/trace | P3b |
| `surcout_forme_speciale_pct` | 1.40 (×40 %) | P3b |
| `calage_forfait` | 225 €/devis | P4 |
| `roulage_prix_horaire` | 375 €/h | P5 |
| `finitions_prix_m2` | 0.125 €/m² | P6 |
| `mo_prix_horaire` | 70 €/h | P7 |

Plus :
- **`Entreprise.pct_marge_defaut`** (singleton globale, par tenant via la table `entreprise` — voir bug Q4) — orchestrator.
- **`PCT_MARGE_FALLBACK = Decimal("0.18")`** (constante Python en dur, `orchestrator.py:39`) — fallback ultime.

### Q3 — Pour chaque « en dur » : config Stratégique correspondante ?

| Clé seed | Phase 1 — champ correspondant ? | Action |
|---|---|---|
| `mo_prix_horaire` (70) | ✅ `ConfigCouts.cout_operateur_eur_h` (défaut 25, **mêmes unités**) | 🔧 brancher P7 dessus |
| `roulage_prix_horaire` (375) | ✅ `ConfigCouts.cout_exploitation_machine_eur_h` (défaut 50, **mêmes unités**, **valeurs ≠**) | 🔧 brancher P5 dessus (cf. Q4) |
| `Entreprise.pct_marge_defaut` | ✅ `ConfigCouts.marge_standard_pct` (défaut 35 %) | 🔧 brancher orchestrator dessus |
| `marge_confort_roulage_mm` (10 mm) | ❌ aucun | 🆕 ajouter à `ConfigRoulage` (par format) ou `ConfigCouts` (global) |
| `cliche_prix_couleur` (45) | ❌ aucun | 🆕 ajouter `ConfigCouts.cliche_prix_couleur_eur` ou table dédiée |
| `outil_base_eur` (200) | ❌ aucun | 🆕 idem (groupe « Outils ») |
| `outil_par_trace_eur` (50) | ❌ aucun | 🆕 idem |
| `surcout_forme_speciale_pct` (1.40) | ❌ aucun | 🆕 idem |
| `calage_forfait` (225) | 🟡 `ConfigChangements.changement_couleur/format/nettoyage` couvrent la base — mais P4 est un forfait par DEVIS, pas une somme d'opérations | 🆕 décider : champ `ConfigCouts.calage_forfait_eur` OU refonte P4 « détaillée » qui consomme `ConfigChangements` |
| `finitions_prix_m2` (0.125) | ❌ aucun | 🆕 ajouter `ConfigCouts.finitions_prix_m2` |
| `matiere_prix_kg_defaut` (1.75) | ❌ aucun (fallback rare) | 🟡 ajouter ou supprimer le fallback (le catalogue Complexe couvre tous les cas) |
| `PCT_MARGE_FALLBACK` (0.18) | ✅ `ConfigCouts.marge_standard_pct` (35 % par défaut) | 🔧 retirer la constante, fallback = défaut DB |

**Bilan** : 3 inputs déjà mappés à un champ Phase 1 (P5 cout machine, P7 cout opérateur, marge), **7 champs à créer** (clichés, outils ×3, calage, finitions, marge confort), 2 à supprimer/migrer (fallback matière, fallback marge).

### Q4 — Les 3 sources de coût horaire — laquelle fait foi ? Doublons ?

État actuel (sur main) :

| Source | Valeur seed (€/h) | Utilisée par cost_engine ? |
|---|---|---|
| **`TarifPoste.cle="roulage_prix_horaire"`** | **375** | ✅ **P5 Roulage** lit ici |
| **`TarifPoste.cle="mo_prix_horaire"`** | **70** | ✅ **P7 MO** lit ici |
| `Machine.cout_horaire_eur` | varie par machine (champ catalogue) | ❌ **aucun poste n'y lit** — info catalogue uniquement |
| `MachineImprimerie.cout_horaire_eur` | varie | ❌ idem (table optim, non utilisée par cost_engine) |
| **`ConfigCouts.cout_exploitation_machine_eur_h`** | **50** (template neutre) | ❌ **non lu** (Phase 1 pas branchée) |
| **`ConfigCouts.cout_operateur_eur_h`** | **25** | ❌ **non lu** |
| `ConfigCouts.cout_energies_eur_h` | 3.5 | ❌ non lu (pas de poste énergie séparé) |

**Qui fait foi aujourd'hui** : `TarifPoste` (roulage 375, mo 70). Les valeurs catalogue `Machine.cout_horaire_eur` et `ConfigCouts.cout_*` sont **dormantes**.

**Doublons et incohérences à trancher en Phase 2** :

1. **3 endroits où poser le coût horaire machine** : `TarifPoste.roulage_prix_horaire`, `Machine.cout_horaire_eur`, `ConfigCouts.cout_exploitation_machine_eur_h`. **Reco** : faire de `ConfigCouts.cout_exploitation_machine_eur_h` la **source unique**, `Machine.cout_horaire_eur` reste un **override optionnel par machine**, `TarifPoste.roulage_prix_horaire` est déprécié (ou conservé en miroir lecture le temps de la transition).
2. **Coût horaire MO** : `TarifPoste.mo_prix_horaire` (70) ≠ `ConfigCouts.cout_operateur_eur_h` (25). **Reco** : `ConfigCouts.cout_operateur_eur_h` devient la source unique, `TarifPoste.mo_prix_horaire` déprécié.
3. **Énergie** : aucun poste ne lit `ConfigCouts.cout_energies_eur_h` — c'est aujourd'hui noyé dans `roulage_prix_horaire`. À ouvrir : laisser dormant, ou décomposer P5 en `machine_horaire + énergie_horaire`.

⚠️ **Bug multi-tenant détecté incidemment** (`orchestrator.py:_resolve_pct_marge`, ligne ~234) :
```python
entreprise = self.db.scalar(select(Entreprise).limit(1))
```
**N'est PAS scopé sur `self.entreprise_id`** — retourne la première entreprise globalement. Pas exploité en pratique parce que prod n'a qu'un tenant productif, mais c'est une fuite logique qui doit être corrigée dans la même PR que le branchement Phase 2 (`select(Entreprise).filter_by(id=self.entreprise_id)`). À **signaler hors audit** — pas un fix à faire dans le cadre lecture seule.

### Q5 — Benchmark V1a/V8 : data live ou fixture ?

**Tourne sur la DB seedée live** — `complexe_id=31`, `machine_id=1`, `entreprise_id=1` (tenant démo), via `SessionLocal()` à chaque test (cf. `tests/test_cost_engine_5cas_benchmark.py:32,43,47,211,223,239`). Les valeurs `TarifPoste`, `TarifEncre`, `Machine`, `Complexe` viennent du seed CSV ré-appliqué par `run_seed()` autouse à chaque test.

⇒ **La cible 1 449,09 € HT V1a est verrouillée à la valeur du seed à T0**, pas à un set de paramètres figés dans le code. Toute évolution du seed (`tarif_poste.csv`, `complexe.csv`, …) — ou de la valeur ICE en bord de table — **casse le benchmark**. Et inversement, **toute modification Stratégique du tenant démo casse le benchmark**.

**Recommandation Phase 2 — préalable obligatoire** :

> 🛡️ **Découpler le benchmark V1a/V8 du seed avant Phase 2.** Le transformer en **fixture pure** :
> - Le test injecte directement un set figé de tarifs (`TarifPoste` + `TarifEncre` + `Machine` + `Complexe` + `Entreprise.pct_marge_defaut`) — soit via une session DB seedée à la main avec valeurs hard-codées en haut du fichier de test, soit (mieux) via un fixture pytest qui upsert ces lignes avec les valeurs ICE exactes.
> - Le benchmark devient ainsi **invariant aux modifications Stratégique** du tenant démo ET aux évolutions du seed.
> - Une fois ce découplage fait, on peut brancher Phase 2 (ConfigCouts → moteur) sans risquer 1 449,09 € à chaque PR.
> - Action complémentaire : ajouter un test « la config Stratégique du tenant démo peut évoluer librement sans casser le benchmark V1a » pour rendre ce contrat explicite.

---

## Recommandation d'ordre Phase 2 (séquencement)

1. **Préalable** — découpler le benchmark V1a/V8 en fixture pure (1 commit, 0 risque).
2. **R-A** — Brancher la **marge** (`ConfigCouts.marge_standard_pct` au lieu de `Entreprise.pct_marge_defaut`) + fixer le bug multi-tenant de `_resolve_pct_marge`. Risque faible, isolé à l'orchestrator.
3. **R-B** — Brancher **P7 MO** (`ConfigCouts.cout_operateur_eur_h`) puis **P5 Roulage** (`ConfigCouts.cout_exploitation_machine_eur_h`). Ces deux sont les pivots du coût horaire ; les benchmarks bougent mais sont protégés par la fixture.
4. **R-C** — Créer les champs manquants sur `ConfigCouts` (clichés, outils, finitions, calage_forfait, marge_confort_roulage) + UI Stratégique correspondante, puis brancher P1/P3/P4/P6. Plus gros lot (migration + UI + branchement).
5. **R-D** — Décider du sort des inputs Phase 1 **dormants** (`ConfigRoulage`, `ConfigChangements`, `cout_energies`, coûts fixes mensuels, buffers rebut/setup) : refonte P4/P5 ou conservation pour usages futurs (planning, PDF, FG).

Chaque étape : 1 PR ciblée, baseline pytest + benchmark fixture verts, pas de merge sans validation.

---

## Garde-fous tenus pendant l'audit

- ✅ Aucun fichier modifié, aucune migration, aucun commit de code.
- ✅ `cost_engine` lu uniquement (orchestrator + 7 calculateurs + aggregator).
- ✅ Sacrés EXACT intacts.
- ✅ `rotation_se.py` non lu (hors périmètre rappelé).

Livrable unique : ce fichier markdown. Pas de PR de code.
