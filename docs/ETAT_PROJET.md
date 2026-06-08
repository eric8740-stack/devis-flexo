# État du projet

> **Source de vérité** : ce fichier est généré à partir de `git log`,
> `gh pr list`, et l'exécution réelle des tests. Aucune référence
> personnelle / employeur — uniquement des faits techniques et la
> convention métier flexographique verrouillée.

---

## En-tête

- **Date** : 2026-06-08
- **Branche active** : `main` = **`663c194`** (après #130 — **`/preview` options par CODE LIVE**).
- **Sprint en cours** : **Aucun**. **🎉 Chantier « devis page unique » end-to-end CLOS** : **CC1 endpoint `/api/devis/preview`** (#124, contrat final prix + déltas/option + `machine_id`) + **CC2 front A1** `/devis/nouvelle` réactive (#123, recalc live debounce/AbortController, contrat preview complet). Chantier précédent **« format sans outil » end-to-end CLOS** (#118 + #121 + #120). Autres CLOS : **L1**, **L2** (sacrés re-baselinés), **Souveraineté**. Bugs #5/#6 **CLOS**.
- **Carte qui-fait-quoi** : **CC1 / CC2 = libres**. Chantiers sans-outil + devis-page-unique terminés.

---

## PRs récemment mergées (10 dernières)

- **#130** — feat(devis): **`/preview` options par CODE** — `options_codes: list[str]` (entrée canonique, le front n'envoie que les codes) → € résolu serveur via `OptionFabrication` (catalogue tenant+global) → `forfaits_st` → P6 (moteur intouché). `options[].delta_eur` par code (`€×(1+marge)`) + flag `impact_production` (option coef/temps sans forfait → `delta_eur:null`, pas de faux +0 €) ; décompo ligne `Option · <libelle>` distincte. `finitions:[{montant_eur}]` déprécié (rétro-compat). `OptionDisponiblePublic` inchangé. **Sacrés L2 EXACTS**. Baseline **1197**.
- **#123** — feat(devis): **front A1 « devis page unique »** (CC2) — page `/devis/nouvelle` réactive consommant `POST /api/devis/preview` live (swap mock → endpoint #124). Recalc live (debounce 250ms, AbortController, keep-last), contrat preview complet (€/1000, géométrie, décompo, options/déltas, alertes info/warn, `couleur_plus`), select presse masqué si tenant mono-machine. Front pur. vitest 204→**218**. → **chantier devis page unique CLOS end-to-end**.
- **#126** — ci(backend): **anti-flaky pull postgres** — `postgres:16` sort de `services:` (pullé avant les steps, source du flaky `registry-1.docker.io`) → géré en **step** : cache image (`docker save`+`actions/cache`) + retry ×5 sur le pull, zéro Docker Hub dès le 2ᵉ run. `backend.yml` uniquement, comportement des tests INCHANGÉ (CI 1201 passed, test FK strictes Postgres tourne).
- **#124** — feat(devis): **endpoint `POST /api/devis/preview`** (recalc live page unique, read-only). État partiel → prix + déltas/option en **1 appel**. Réutilise `MoteurDevis` + `bat_calculs` (Ø) + module refente via `LotProduction` transitoire + `_construire_devis_input_pour_lot` (moteur **non modifié**). Wiring : `nb_couleurs`→P2+P3a, `finitions[]`→`forfaits_st` (vrai P6), `machine_id`→P5, `options[].delta_eur` = impact marginal serveur (finition / +1 couleur). Sortie `{prix_ht (7 postes purs), cout_revient, marge_pct, prix_1000, geometrie, decompo (+Refente si sans outil), options, alertes}`. Read-only/idempotent/scopé/best-effort (jamais 500). **Sacrés L2 EXACTS**. Baseline **1195**.
- **#120** — feat(optim): **UI « mode sans outil »** (lot front, CC2) — toggle Card Format avec/sans outil + masquage des champs outil (intervalle dev, développé) + ligne « déchet latéral », consomme le contrat back A. Front pur. vitest 202→**204**.
- **#121** — feat(devis): **lot back B — coût de refente ADDITIF** + persist mode sans outil. Réutilise le moteur rebobinage Sprint-16 (axe Ø) × `nb_filles` résolu (axe largeur), gâche raccord, coût `temps × ConfigCouts.cout_exploitation_rebobineuse_eur_h`. Émis AUTO au chiffrage, porté par `ht_total` (`prix_vente_ht` 7 postes + calage INTOUCHÉS). Champs FR + migration `b3c5d7e9f1a2`. `LotProductionCreate/Read` : `cylindre_id` nullable + persist `mode_sans_outil`/`laize_stock_mm`/`nb_filles_force` (POST sans-outil ne 422 plus). **Sacrés L2 EXACTS** (config neutre par défaut). Baseline **1183**.
- **#118** — feat(optim): **lot back A « mode sans outil »** — 2ᵉ chemin de calcul (impression pleine largeur + refente). `mode_sans_outil` + `laize_stock_mm` (+ `nb_filles_force`) sur requête/`DevisInput`/`LotProduction` ; court-circuit candidats cylindre (`optimiser_pose` bypassé), `intervalle_dev=0`, P1 facture la laize STOCK entière (déchet inclus). `geometrie_laize` +4 clés (`laize_stock_mm`/`laize_utile_mm`/`dechet_lateral_mm`/`nb_filles`) + écho `mode_sans_outil`. Migration `a2b4c6d8e0f1` (additive). **cost_engine / `rotation_se` / `bat_calculs` INTOUCHÉS → sacrés L2 EXACTS.** Baseline **1167**.
- **#114** — feat(cost-engine): **L2 rebasage P1 sur laize papier plafonnée** — P1 (matière) facture la laize papier RÉELLE `min(arrondi_palier(plaque + 2×bord), laize_utile)` au lieu de `laize_utile + marge_confort` (retirée, double-comptait les bords). 5ᵉ param `laize_utile_mm` OPTIONNEL sur `calcul_laize_papier` (cap) ; propagation router + crud (machine du lot) ; `poste_1_matiere` consomme `DevisInput.laize_papier_mm`. **🔴 TOUCHE LES SACRÉS → RE-BASELINE validée Eric** (cf. Baseline tests). Clé `details` `laize_machine_mm`→`laize_facturee_mm`+`base_laize_source`. **P4 calage / Ø diamètre INTOUCHÉS**, zéro migration. CI verte, déployé prod (`/` → 200). Baseline **1148**.
- **#111** — feat(optim): **front souveraineté** (CC2) — motif de forçage recommandé (non bloquant) + note discrète ; consomme `warnings` (inchangé). Câblé derrière #112. → **lot Souveraineté COMPLET**.
- **#112** — feat(optim): **forçages Règle 7 NON BLOQUANTS** — motif optionnel (warning `warnings[]`, plus de 422) pour forçage intervalle dev + épaisseur (laize déjà non bloquant). Bornes `ge/le` conservées ; check structurel lacets asymétriques gardé. **Validation seule, calcul intouché → sacrés EXACTS au moment du merge** (V1a 1 449,09 / tripwire 704,07 ; **rebasés depuis par L2 #114 → 1 424,31 / 695,36**). Déployé prod.
- **#110** — docs(etat-projet): L1 COMPLET (front+back) mergé + déployé prod — CC1+CC2 libres.
- **#108** — feat(optim): **L1-front** (CC2) — saisie **bord latéral (surplus extérieur)** + décompo laize ; consomme `geometrie_laize` + envoie `bord_lateral_mm`/`motif_bord_lateral`. Front pur (back #107 inchangé). vitest 194→198.
- **#109** — docs(etat-projet): L1-back mergé (#107) + déployé prod — carte + baseline + head alembic.
- **#107** — feat(optim): **L1 géométrie laize** — `bord_lateral_mm` (surchargeable) + `motif_bord_lateral` + sortie `geometrie_laize` sur `OptimisationConfigOut` + `laize_papier` déterministe (plancher `laize_mini_roulable`). **P1 INTOUCHÉ** (cost_engine) → V1a 1 449,09 € + tripwire 704,07 € EXACTS **au moment du merge** (**rebasés depuis par L2 #114 → 1 424,31 / 695,36**). Migration `f7a8b9c0d1e2`. Déployé prod (deploy Railway vert).
- **#106** — docs(etat-projet): chantier L1 laize papier (séquencé L1/L2) + carte qui-fait-quoi + reconcile #105.
- **#105** — feat(machine): `type_machine` (presse/finition) + filtre loader optim — les finitions (Daco) ne génèrent plus de candidats. Migration `e6f7a8b9c0d1` (re-type par motif daco/rotoflex/finition, tous tenants). Sacrés EXACTS.
- **#104** — feat(optim): alerte cohérence **fronts ↔ poses laize** (étape Candidats) — `nb_poses_laize` doit être multiple de `nb_fronts_sortie` ; badge + désactivation sélection des incohérents + toggle « Masquer les incohérents » (front pur, `nb_fronts=1` neutre)
- **#103** — fix(devis): signature de montage trop stricte — retirer `nb_poses_laize` du calage (bug #5)
- **#102** — feat(devis): **1 calage par montage** (dedup calage des lots de même signature) (bug #5)

## PRs ouvertes

- **Aucune** — chantier « devis page unique » end-to-end mergé (#124 endpoint + #123 front A1).

## PRs récemment fermées (non mergées)

- #76 — refactor(cost_engine) Lot 4a doublon (branche concurrente) — fermée, redondante avec #75.
- #65 — docs(audit) cartographie config-driven vs hardcode — fermée 29/05, contenu caduc résolu par Lots 1/2/3/4a.
- #54 — feat(strategique-ui) onglet Stratégique 6 sections — fermée 29/05, contenu déjà sur main par cherry-pick.

---

## Baseline tests

> **🔴 RE-BASELINE SACRÉE L2 (#114, 2026-06-05) — LIRE EN PRIORITÉ.**
> P1 (matière) facture désormais la **laize papier réelle plafonnée** (et plus
> `laize_utile + marge_confort`). **Les anciens sacrés `1 449,09 €` et
> `704,07 €` NE SONT PLUS valides** — toute occurrence ci-dessous ou dans les
> archives historiques de ce doc qui les cite est un snapshot PRÉ-L2.
> **Nouvelle baseline sacrée validée Eric** :
>
> | Cas | Valeur sacrée L2 | Plafond mord ? |
> |---|---|---|
> | **V1a** | **1 424,31 €** HT | non (papier 210 < laize_utile 220) |
> | **V1b** | **1 896,31 €** HT | non |
> | **V2** | **738,88 €** HT | non |
> | **V3** | **8 189,67 €** HT | non |
> | **V4** | **1 672,39 €** HT | non |
> | **V7a** | **1 424,31 €** / **6,73 €/mille** | non |
> | **V8a** | **1 424,31 €** / **3,37 €/mille** | non |
> | **Tripwire P0b multi-lots** | **695,36 €** HT | **oui** (papier brut 330 > laize_utile 320 → cap 320) |
>
> V8b-e : **ratios inchangés** (non re-figés — passent par le fallback legacy
> `laize_utile + marge_confort`, vérifiés verts).

- **pytest local — `main`** (SQLite, `PG_TEST_URL` absent) : `1197 passed, 10 skipped, 0 failed` — inclut le chantier sans outil (#118 + #121), l'endpoint **`/api/devis/preview`** (#124) et son **option pricing par CODE** (#130 : `options_codes` → € catalogue → P6, deltas par code + `impact_production`, rétro-compat finitions). Sacrés L2 EXACTS (preview read-only, moteur intouché). Skips : 2 tests subprocess SQLite migration P1+P2, 2 tests obsolètes `ConfigurationPose` / `MachineImprimerie`-spec (tables droppées), 1 test PG sous FK strictes (skip si `PG_TEST_URL` absent → tourne en CI uniquement), 5 autres skip historiques env-dependent. **(CI = +6 : test FK strictes Postgres + skips SQLite-only non comptés.)**
- **pytest CI** (Postgres réel) : **`1201 passed, 4 skipped, 0 failed`**. ⚠️ **Ne pas confondre baseline locale (1195) et CI (1201)** : en CI, `test_migration_p1p2_sous_fk_strictes_postgres` **tourne** (valide la migration P1+P2 sous **FK strictes Postgres**, scénario réel boot Railway prod) et certains skips SQLite-only ne s'appliquent pas → +6 vs local. **Référence locale = 1195** (SQLite, `PG_TEST_URL` absent).
- **CI backend anti-flaky (#126, 2026-06-08)** : `postgres:16` n'est plus un `services:` container (pullé avant les steps, sans cache/retry → un timeout `registry-1.docker.io` rendait la CI rouge alors que pytest n'avait pas tourné). Il passe en **step** : **cache image** (`docker save` + `actions/cache`) + **retry ×5** sur le pull → **zéro accès Docker Hub dès le 2ᵉ run**. **`backend.yml` uniquement**, comportement des tests INCHANGÉ (même PG `localhost:5432`, même `PG_TEST_URL`, test FK strictes tourne).
- **Benchmark `cost_engine` 13/13 EXACT** post-#114 — re-figés aux valeurs L2 (V1a 1 424,31 / V1b 1 896,31 / V2 738,88 / V3 8 189,67 / V4 1 672,39 / V7a 6,73 / V8a 3,37 ; V8b-e ratios inchangés).
- **Tripwire multi-lots P0b : `695,36 €` EXACT** post-#114 — le plafond `laize_utile=320` MORD ici (laize_plaque 310, papier brut 330 → cap 320), base P1 330→320 → P1 243,56→236,18. Garde anti-drift fixture `machine.laize_utile_mm == 320` conservée.
- **vitest** : `218/218 tests passed` (29 fichiers) — +14 sur le front A1 « devis page unique » (#123 : page `/devis/nouvelle` réactive + parsing contrat preview + recalc live).
- **next build** : ✓ compiled successfully (gate Vercel preview vert avant chaque merge).
- **alembic** : HEAD `main` = **`b3c5d7e9f1a2`** (lot back B #121 — `config_couts.cout_exploitation_rebobineuse_eur_h` + `gache_raccord_pct` + `lot_production.nb_filles_force` + rétro-fix SQLite `cylindre_id` nullable, additive/réversible). Précédents `a2b4c6d8e0f1` (lot back A) → `f7a8b9c0d1e2` (L1) → `e6f7a8b9c0d1` (type_machine) → `d5e6f7a8b9c0` (paroi mandrin) → `c4d5e6f7a8b9` (config_couts ICE) → `b2c3d4e5f6g7` (P1+P2 unify). Application prod auto via `CMD` Dockerfile.

---

## En prod (modules livrés récents)

- Rapport de fabrication par lot sur `/devis/[id]` — récap chiffrage + 7 postes color-codés (#62, #63 robustesse off-by-one). **Fix #78 (29/05)** : la modification d'un devis multi-lots ne masque plus le rapport+plan (régression : `update_devis` écrasait le `payload_output` recalculé par `_chiffrer_devis_multilots` avec le placeholder du body ; fix = pop conditionnel `payload_output`/`payload_input` quand `lots_in is not None`).
- Alerte cohérence Ø ext ↔ nb étiq/bobine à la saisie d'un devis — non bloquante, source de vérité backend (`bat_calculs`, SSOT mm) (#64, ε matière saisie en #71).
- Planificateur de bobines (rapport de fabrication, par lot) — 3 scénarios géométriques (A/B/C) + scénario IMPOSE anti-fléau (#66), persistance JSONB + Q ajustée + forçage motif tracé (#68).
- Planificateur — modes IMPOSE étendus : `nb_etiq` (historique), `nb_bobines`, `packaging` (N × X), mutuellement exclusifs. Gestion du surplus avec 3 décisions Q : facturer / stock / réduire (#73).
- Refactor `cost_engine` Phase 2 : Lot 1 benchmark figé (#67), Lot 2 marge scopée tenant + isolation multi-tenant (#70), Lot 3 P5/P7 scopés tenant via `ConfigCouts` (#72), **Lot 4a 7 tarifs P1/P3/P4/P6 scopés tenant via `ConfigCouts` (#75)**. **Dette config-driven Phase 2 identifiée 28/05 → résolue par Lots 1/2/3/4a (marge, P5/P7, P1/P3/P4/P6).**
- Numérotation devis robuste (#77, 29/05) — `UNIQUE(devis.numero)` scopée tenant via `ix_devis_entreprise_id_numero` + `generate_next_numero` en `MAX(seq)+1` scope tenant + retry loop borné (5). Résout 409 sur hard-delete (count+1 rebouchait les trous) et autorise deux tenants à avoir chacun `DEV-YYYY-0001` sans collision.
- **Convergence machines B1/B2/B3a/B3b (#80 + #81 + #82 + #83, 29/05-01/06)** — `Machine` legacy enrichi des 3 champs optim (`laize_utile_mm`, `nb_postes_decoupe`, `options`) + renommage `nb_couleurs` → `nb_groupes_couleurs`. UI `/machines` expose ces champs dans un bloc DISTINCT « Paramètres optimisation » (multi-select alimenté par `GET /api/machines/modules-disponibles`). **Vitesse réelle unique** : `vitesse_moyenne_m_h ÷ 60` pilote chiffrage ET optim, label harmonisé entre `/machines` et Stratégique > Machines (100/58/75 cohérents). **Moteur d'optim repointé sur `Machine` (B3a #82)** : `optimisation_loader.charger_machines_actives` lit le parc réel (P5/Daco/Atelier 2) au lieu du catalogue `MachineImprimerie` (Mark Andy 2200) → étape 2 « Candidats viables » affiche le vrai parc utilisateur. **B3b #83** : colonne morte `machine.vitesse_pratique_m_min` droppée (migration `a1b2c3d4e5f6` réversible).
- **P0b tripwire sacré multi-lots (#84, 02/06)** — `test_benchmark_multilots_sacred_p0b.py` fige le `prix_vente_ht_eur` sur scénario déterministe `POST /api/devis` multi-lots (1 lot, 100×80mm, 2×3 poses, qté 10 000, `laize_utile=320`). Garde anti-drift fixture : assertion explicite `machine.laize_utile_mm == 320` sur la machine source (échoue FORT si l'ordre/le catalogue change). **Valeur figée : `704,07 €` (pré-L2) → REBASÉE par L2 #114 à `695,36 €`** (le plafond `laize_utile=320` MORD ici : papier brut 330 → cap 320).
- **Unify `Machine` ↔ `MachineImprimerie` — P1+P2 (#86 + hotfix #87, 02/06)** — fin de la convergence. Migration `b2c3d4e5f6g7` (RÉVERSIBLE, dialect-aware) : (1) bump `machine_id_seq` Postgres défensif AVANT INSERT presses ; (2) INSERT 3 presses catalogue (Mark Andy 2200 / OMET XFlex 330 / Nilpeter FA-22) depuis `MachineImprimerie` dans `Machine`, idempotent par `(nom, entreprise_id)` ; (3) **UPDATE atomique CASE WHEN** des FK `lot_production.machine_id` + `porte_cliche.machine_id` (`machine_imprimerie.id` → `machine.id`) — anti-cascade bug ; (4) DROP `machine_imprimerie` + DROP `configuration_pose` (table jamais peuplée). Code repointé sur `Machine` (`crud/devis`, `services/onboarding_service`, `routers/porte_cliche`, `scripts/seed`). Modèles `machine_imprimerie.py` + `configuration_pose.py` supprimés. **Test PG sous FK strictes** (`test_migration_p1p2_sous_fk_strictes_postgres`) en CI via service `postgres:16` du workflow `backend.yml` — sentinelle scénario réel boot Railway prod. **Parc démo (`entreprise_id=1`) post-migration : 6 machines actives** — Mark Andy P5 + Daco D250 finition + Atelier 2 (parc utilisateur existant) + Mark Andy 2200 + OMET XFlex 330 + Nilpeter FA-22 (catalogue MI réinsérées). **Aucune fiche `Machine` existante touchée** (Daco / Atelier conservés). Principe VALUE-NEUTRAL respecté : tripwire `704,07 €` resté EXACT **à l'époque** (rebasé depuis à `695,36 €` par L2 #114).
- Hotfix build : fichiers de test exclus du `next build` (`tsconfig.exclude` + `.eslintrc.ignorePatterns`) ; vitest continue de les exécuter via esbuild (#69).

## En cours / à venir

- **🆕 Backlog V1 « mode sans outil »** (corrections trackées, **NON bloquantes** — le chantier est CLOS et value-neutral en l'état) :
  - **Gâche raccord → valoriser au COÛT MATIÈRE** (mètres perdus × prix matière), PAS au taux rebobineuse (V1 actuel = temps-équivalent). **À FAIRE avant d'activer la gâche en prod** (`gache_raccord_pct` défaut **0 = inerte** aujourd'hui).
  - **`cylindre_id` : validator conditionnel** « obligatoire si `mode_sans_outil = False` » (au lieu de juste nullable) — durcir `LotProductionCreate`.
  - **Tracer les hypothèses de sourcing refente** (rebobineuse retenue, Ø mandrin défaut 76, Ø max client→rebobineuse) → motif visible / auditable, façon planner bobine.
- **Backlog horizon (non lancé)** :
  - **🔴 Pricing options PRODUCTION dans le cost_engine** (coef vitesse/gâche, temps calage) — sacred-sensitive : touche P3/P4/P5, **benchmarks à revérifier EXACTS sous contrôle**. Validation Eric requise. (`/preview` renvoie déjà `impact_production:true` pour ces options en attendant.)
  - **Lot 3** — renommages config coûts (P7 → `cout_operateur_eur_h`, P5 → `cout_exploitation_machine_eur_h`).
  - **Lot 4** — 7 champs coût manquants + UI Stratégique (recoupe « Phase 2 / Lot 4b » ci-dessous).
  - **Dette UI rebobinage** — bloc mono-lot périmé · double saisie matière · double saisie mandrin.
  - **#1 « Outils compatibles » inerte** (matcher front non câblé) · **#2 « 0,00 € » cosmétique**.
- **Dette archi : unifier `Machine` ↔ `MachineImprimerie`** — ✅ **FERMÉE** post-merge #86 + hotfix #87 (02/06). Récap des étapes : P0a (audit) → P0b (tripwire `704,07 €` #84, **rebasé `695,36 €` par L2 #114**) → **P1+P2 (#86) + hotfix #87** : migration `b2c3d4e5f6g7` + repoint code + suppression `MachineImprimerie` + `ConfigurationPose`. Tripwire EXACT, V1a 13/13 EXACT (valeurs pré-L2).
- **🔴 NOUVEAU follow-up critique** (cf. [`docs/BACKLOG_BUGS_session_2026-06-02.md`](BACKLOG_BUGS_session_2026-06-02.md)) — **les 3 presses migrées (Mark Andy 2200 / OMET / Nilpeter) sont `actif=true` mais n'apparaissent PAS comme candidates dans l'optim** sur le compte démo. Seuls P5 et Atelier 2 ressortent → 0 config viable pour les 3. Pas le flag `actif` (vérifié post-migration). Investiguer `charger_machines_actives` + la génération de candidats : champ NULL requis (`vitesse_max_m_min` / `largeur_max_mm` / `duree_calage_h` défaultés à NULL par la migration ?) ou appariement cylindre ↔ machine. Sprint dédié à planifier prochaine session.
- **Pattern migrations data à auditer** (leçons P1+P2) :
  - (a) Remap d'ids en boucle = **cascade UPDATE** quand `new_id` coïncide avec un `old_id` futur → toujours faire un **UPDATE atomique CASE WHEN** ou table de mapping temporaire.
  - (b) INSERT de colonnes JSON depuis une `list[str]` Python via `text(":x")` → SQLAlchemy sérialise en `ARRAY[...]` côté Postgres → `DatatypeMismatch`. Toujours `json.dumps` côté Python + `CAST(:x AS json)` côté SQL dialect-aware.
- **Ménage « 4 presses »** (toujours reporté — Daco D250 finition + Atelier 2 ne devraient PAS apparaître dans les sélecteurs presse / optim) — à arbitrer **après** vérif du couplage rebobineuse (cf. BACKLOG_BUGS § 1 sécurisé).
- **Phase 2 / Lot 4b** (à venir) — UI Stratégique pour les 7 nouveaux champs Lot 4a (`marge_confort_roulage_mm`, `cliche_prix_couleur_eur`, `outil_base_eur`, `outil_par_trace_eur`, `surcout_forme_speciale_facteur`, `calage_forfait_eur`, `finitions_prix_m2_eur`).
- **Phase 2 / cleanup `TarifPoste`** (à venir) — suppression des colonnes dépréciées P1/P3/P4/P5/P6/P7 quand toutes les configs sont stables en prod.
- **Phase 2 / `Machine` override** (à venir) — `Machine.cout_horaire_eur` comme override optionnel sur `ConfigCouts.cout_exploitation_machine_eur_h` (P5 par machine).
- **Phase 2 / `matiere_prix_kg_defaut`** (à arbitrer) — fallback P1 conservé sur `TarifPoste` (Q1 audit Lot 4a) ; migrer vers `ConfigCouts` ou supprimer le fallback.
- **Dette `payload_output` = donnée serveur** (PR séparé à prévoir) — durcissement intégral : recalcul serveur mono-config OU purge `DevisSaveBar` si `/devis/nouveau` abandonné. Le pop conditionnel actuel (#78) suffit à éteindre la régression sans casser le flux legacy.

---

## Chantier — Devis page unique (page réactive + recalc live) — ✅ CLOS (end-to-end)

> Page de devis unique `/devis/nouvelle` : tous les leviers sur un écran, le
> prix se recalcule à chaque changement via un **endpoint serveur** (SSOT, zéro
> calcul dupliqué côté front). **CLOS** : endpoint #124 + front A1 #123, mergés.

- **CC1 — endpoint `POST /api/devis/preview` : ✅ MERGÉ (#124 + #130).** Read-only, scopé `entreprise_id`, idempotent, best-effort (jamais 500). **Contrat CANONIQUE (référence front)** :
  - **Input** (tous optionnels) : `laize, dev, forme, quantite, cylindre_id, machine_id, matiere_id, epaisseur_um, mandrin_mm, diam_max_mm, nb_filles_force, mode_sans_outil, laize_stock_mm, nb_couleurs` + **`options_codes: list[str]`** (**CANONIQUE**). ⚠️ **Écart #130** : `finitions:[{montant_eur}]` est **DÉPRÉCIÉ** (rétro-compat — A1 prod envoie `[]`). Le front envoie des **codes** (`/options-disponibles`), JAMAIS des montants.
  - **Output** : `prix_ht` (**7 postes PUR**, sacré) `, cout_revient, marge_pct, prix_1000, geometrie {diametre_mm, nb_poses, nb_filles, dechet_lateral_mm}, decompo [{poste, montant}]` (+ ligne **Refente** additive si sans outil, + lignes **`Option · <libelle>`** distinctes de la sous-traitance) `, options [{code, delta_eur, impact_production}]` `, alertes [{niveau, message}]`.
    - `options[]` = delta marginal **PAR CODE** sur le catalogue tenant (`€ × (1+marge)`, additif) + `couleur_plus`. **Garde-fou** : option à impact production sans forfait → `impact_production:true` + `delta_eur:null` (front : « impact production (chiffré bientôt) », jamais un faux +0 €).
  - **Wiring (réutilisation pure, moteur INTOUCHÉ)** : `nb_couleurs`→`nb_couleurs_par_type` (P2+P3a) ; `options_codes`→€ catalogue `OptionFabrication`→`forfaits_st`→**P6** (`OptionDisponiblePublic` inchangé, pas de fuite `forfait_eur`) ; `machine_id`→P5 (défaut 1ère presse) ; tout via `LotProduction` transitoire + `_construire_devis_input_pour_lot` + `MoteurDevis`.
  - **Pointeur front** : client typé [`frontend/src/app/devis/nouvelle/devisPreview.ts`](../frontend/src/app/devis/nouvelle/devisPreview.ts) + [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts).
  - **🔴 Backlog (chantier séparé, sacred-sensitive, validation Eric)** : **pricing options PRODUCTION** (coef vitesse/gâche, temps calage) **dans le cost_engine** — touche P3/P4/P5 → **benchmarks à revérifier EXACTS sous contrôle**. + best-effort V1 : `diam_max_mm` sourcing fin ; `machine_id` ← contrat optim (front B).
- **CC2 — front A1 : ✅ MERGÉ (#123, `13a579d`).** Page `/devis/nouvelle` réactive + design FlexoSuite, consomme `/api/devis/preview` (swap mock → endpoint live). Recalc live debounce 250ms + AbortController + keep-last ; parse le contrat complet (€/1000, géométrie, décompo, options/déltas, alertes) ; select presse masqué si tenant mono-machine. vitest **218**.

---

## Chantier — Mode « format sans outil » (impression laize entière + refente) — ✅ CLOS (end-to-end)

> Spec métier rédigée par Eric (2026-06-05), **figée** (5 décisions tranchées).
> **CLOS** : lot back A (#118, géométrie + contrat /calculer) + lot back B (#121,
> coût refente additif + persist) + lot front (#120, UI). Mergés + déployés.
> Cartographie back + décisions + découpage en fin de section. **Reste : Backlog
> V1** (3 corrections trackées non bloquantes — cf. « En cours / à venir »).

### Principe

Toggle sur le format : « avec outil » (mode actuel) / « sans outil ».
Sans outil : pas d'outil réel (cylindre/plaque), impression pleine largeur sans découpe par outil, puis refente en bobines filles sur la finisseuse.

### Format

- Format laize × dev TOUJOURS saisi (impératif devis).
- Sans outil : développé LIBRE / factice (aucun outil ne le contraint).
- Sans outil : intervalle DEV = 0 (impression continue, pas d'échenillage transversal) → champ masqué/forcé.
- Intervalle LAIZE conservé = espace entre les filles de refente (lames).

### Matière & unités

- Matière en m² (= laize × ml) ; production en ml.
- Matière = laize bobine STOCK montée (ex 220), PAS l'utile.
- Déchet latéral = laize stock − laize utile (utile = filles + intervalles refente) → AFFICHÉ/tracé.
- V1 : déchet inclus dans le coût (bobine entière consommée) + affiché. « Facturer/absorber » = raffinement futur (cf. surplus planificateur).

### Production & postes

- Impression pleine largeur (sans poses découpées par outil).
- Calage = calage IMPRESSION (pas de calage découpe).
- Refente = BOBINAGE des filles sur finisseuse (type_machine=finition, #105) : réutilise planificateur + rotation_se (8 sens) + bat_calculs (Ø). Chaque fille : sens enroulement (int/ext) + sens lecture (déjà encodés).
- PAS de coût de découpe outil.

### Invariants

- Calage lié à l'outil/cliché (ici clichés d'impression) — 1 calage / montage.
- rotation_se / 8 sens : SACRED → réutilisation pure, JAMAIS modifier le mapping.
- bat_calculs (Ø) : SSOT → prudence.

### À cartographier

- Poste refente/bobinage finisseuse : déjà un poste de coût ?
- Point d'insertion du toggle avec/sans outil (front + back).

### Cartographie back (read-only, 2026-06-05) — réponses

**Le poste refente/bobinage finisseuse N'EXISTE PAS comme poste cost_engine.**

- **cost_engine = 7 postes figés** (P1→P7) assemblés par `MoteurDevis` ([orchestrator.py:59-67](../backend/app/services/cost_engine/orchestrator.py#L59-L67)) ; `prix_vente_ht = Σ(postes) × (1 + marge)` ([orchestrator.py:80-87](../backend/app/services/cost_engine/orchestrator.py#L80-L87)). **Aucun poste « refente/bobinage ».**
- Le **rebobinage est un module ISOLÉ** ([services/rebobinage/](../backend/app/services/rebobinage/)) — déjà branché sur le **planificateur** (3 scénarios A/B/C), **`rotation_se` (8 sens)** et **`bat_calculs` (Ø)** (cf. #66/#68/#73 et bug #6). Son coût est **ADDITIF, hors `prix_vente_ht`** : `ht_total = prix_vente_ht (PUR, 7 postes) + contribution_rebobinage` ([devis_total.py:36-50](../backend/app/services/devis_total.py#L36-L50)). C'est l'ancrage naturel du **bobinage des filles** sans toucher au cost_engine.
- **`type_machine="finition"` (#105)** n'est lu QUE par le loader optim pour exclure les finisseuses des candidats ([optimisation_loader.py:86](../backend/app/services/optimisation_loader.py#L86)). **Aucune logique cost_engine ne le consulte** → un mode « sans outil » devra explicitement router le calcul, le rôle parc ne suffit pas.

**Postes presse en mode sans outil (impression conservée, découpe outil supprimée) :**

- **P1 Matière** ([poste_1_matiere.py](../backend/app/services/cost_engine/poste_1_matiere.py)) : facture déjà `laize × ml` (m²). En mode sans outil, brancher la base sur la **laize bobine STOCK** (ex. 220), pas l'utile → cohérent avec « déchet latéral inclus + tracé ». P1 consomme déjà `DevisInput.laize_papier_mm` (L2 #114) — c'est le point d'entrée pour porter la laize stock.
- **P2 Encres / P5 Roulage / P7 MO** : impression pleine largeur → **conservés** (impression réelle).
- **P3 Outillage/Clichés** ([poste_3_cliches.py:55-107](../backend/app/services/cost_engine/poste_3_cliches.py#L55-L107)) : **P3a clichés impression = CONSERVÉ** (`nb_couleurs × prix`, [L58-61](../backend/app/services/cost_engine/poste_3_cliches.py#L58-L61)) ; **P3b découpe outil = 0** — déjà le cas si `outil_decoupe_existant=True` ([L64-82](../backend/app/services/cost_engine/poste_3_cliches.py#L64-L82)), et le flux multi-lots `_construire_devis_input_pour_lot` ne pose pas ce champ → **P3b déjà à 0** ([crud/devis.py:622-731](../backend/app/crud/devis.py#L622-L731)).
- **P4 Calage** ([poste_4_calage.py:40-42](../backend/app/services/cost_engine/poste_4_calage.py#L40-L42)) : forfait fixe `ConfigCouts.calage_forfait_eur`, non paramétrable par payload → en mode sans outil c'est **calage IMPRESSION** (conservé, conforme à l'invariant « 1 calage / montage »). Pas de calage découpe à retirer (P4 ne distingue pas aujourd'hui).

**Point d'insertion du toggle (back) :**

- **Champ** `mode_sans_outil: bool = False` (ou `format_sans_outil`) sur **`DevisInput`** ([schemas/devis.py](../backend/app/schemas/devis.py), après [L157](../backend/app/schemas/devis.py#L157)) — point d'entrée unique cost_engine, value-neutral par défaut.
- **Schéma optim** : ajouter le toggle sur le **format** côté `OptimisationCalculerRequest` ([schemas/optimisation.py](../backend/app/schemas/optimisation.py)) ; en mode sans outil, forcer `intervalle_dev = 0` (masqué front) et libérer le développé (factice). L'optim pose découpe n'est plus contrainte par un outil → cadrer si l'étape « candidats » est court-circuitée.
- **Threading** : (a) `/api/cost/calculer` (mono) → direct ; (b) flux réel `/api/optimisation/calculer` → multi-lots : porter le flag sur `payload_input` (étape 4) + l'injecter dans `_construire_devis_input_pour_lot` ([crud/devis.py:719](../backend/app/crud/devis.py#L719)) → `DevisInput`. Persistance par lot = colonne `LotProduction.mode_sans_outil` ([models/lot_production.py](../backend/app/models/lot_production.py), migration additive) si flag historisé.
- **Refente des filles** : réutiliser le **module rebobinage** existant (coût additif `ht_total`) pour le bobinage des bobines filles, sans nouveau poste cost_engine.
- **Guardrail** : `mode_sans_outil=False` (défaut) → **sacrés L2 EXACTS** (V1a 1 424,31 € … tripwire P0b 695,36 €) ; **`rotation_se` / 8 sens et `bat_calculs` (Ø) INTOUCHÉS** (réutilisation pure, mapping SACRED).

### ⚠️ Réserve architecture (structurante)

**Le mode sans outil est un 2ᵉ CHEMIN DE CALCUL back, PAS un masquage front.** Concrètement, le flag `mode_sans_outil` doit déclencher côté serveur :

- **court-circuit de la sélection des candidats cylindre** (pas d'outil → aucune contrainte de poses dev par un développé d'outil) ;
- **`intervalle_dev = 0`** (impression continue, pas d'échenillage transversal) ;
- **géométrie laize basculée sur la bobine STOCK** (≠ utile) + calcul du **déchet latéral** (`stock − utile`, utile = filles + intervalles refente) ;
- **refente des filles** via le module rebobinage additif.

Le front (toggle Card Format + masquages) ne fait que refléter ce chemin ; il ne le crée pas. Toute logique de calcul reste serveur (source de vérité).

### Décisions de cadrage — TRANCHÉES (Eric, 2026-06-05)

1. **Périmètre** : on **IMPRIME pleine largeur PUIS refente**. Donc **presse + clichés (P3a) + calage impression (P4) conservés** ; **découpe outil P3b = 0** (déjà le défaut) ; **refente ajoutée**. Ce n'est NI « refente seule sans presse » (on imprime), NI juste « pas de die neuf » : c'est **aucune découpe outil + impression pleine largeur + refente**.
2. **P3a clichés** : **facturé** (on imprime → il faut des clichés).
3. **P4 calage** : **inchangé en V1 = calage IMPRESSION** (1 calage / montage, invariant respecté). Le forfait représente ce calage. **Vérif code (CC1, 2026-06-05)** : `P4` est un **forfait unique opaque** `ConfigCouts.calage_forfait_eur` (`operations_count=0`, `mode="forfait"`, [poste_4_calage.py:1-18,40-42](../backend/app/services/cost_engine/poste_4_calage.py#L40-L42)) — **aucune ventilation impression/découpe** dans le code → pas de ligne découpe distincte qui surfacture. Seule réserve : si la *valeur* (225 € démo) a été calibrée en incluant une part de calage découpe, c'est un sujet **tarif** (non encodé) → **tarif réduit = raffinement futur, non bloquant V1**.
4. **Flag** : **par lot** — `LotProduction.mode_sans_outil` + `DevisInput.mode_sans_outil` (défaut `False`, value-neutral, **migration Alembic additive**). Toggle front V1 au **niveau format** ; le modèle supporte déjà un mix avec/sans outil dans un même devis (extension future).
5. **Finisseuse** : **module rebobinage additif existant, PAS de nouveau poste** → `prix_vente_ht` (7 postes) **intouché** → **sacrés L2 EXACTS + cost_engine non modifié** (invariant SACRED). Choix le plus sûr, pris fermement.

**Garde-fou confirmé** : `mode_sans_outil=False` → **sacrés EXACTS**. En sans outil, la géométrie laize bascule sur le **stock** (≠ outil) et alimente P1 différemment — **attendu, et gaté par le flag**.

### Découpage — état des lots

- **Lot back A — ✅ MERGÉ + DÉPLOYÉ (PR #118, merge `137249f`).** Baseline **1167 passed / 10 skipped / 0 failed** (+19 tests sans outil). Définit le **contrat /calculer** que le front consomme.
  - **Contrat** : `DevisInput.mode_sans_outil` + `laize_stock_mm` ; `OptimisationCalculerRequest.mode_sans_outil` + `laize_stock_mm` (obligatoire si sans outil, validateur) + `nb_filles_force` (override souveraineté). `LotProduction.mode_sans_outil` + `laize_stock_mm` + **`cylindre_id` NULLABLE** (sentinelle `0` côté config), migration **`a2b4c6d8e0f1`** (additive, réversible, dialect-aware).
  - **Sortie** : `geometrie_laize` **+4 clés** (`laize_stock_mm` / `laize_utile_mm` / `dechet_lateral_mm` / **`nb_filles`** explicite, distinct de `nb_poses_laize` ; `None` en mode avec outil) + écho top-level `mode_sans_outil`. Court-circuit candidats cylindre (`optimiser_pose` bypassé), `intervalle_dev=0`, géométrie pure [`sans_outil.py`](../backend/app/services/optimisation/sans_outil.py).
  - **Décisions appliquées** : Option A (champ explicite `laize_stock_mm`) ; intervalle refente défaut **3 mm** (`DEFAULT_INTERVALLE_REFENTE_MM`, acté Eric) ; **`nb_filles` explicite + override** `nb_filles_force` (1 fille = pistes regroupées / pas de refente ; infaisable → presse écartée) ; **bord_lateral L1 NON appliqué** en sans outil. P1 facture la laize STOCK entière (déchet inclus). **cost_engine logique INTOUCHÉE** ; `rotation_se` / `bat_calculs` **INTOUCHÉS**.
- **Lot back B — ✅ MERGÉ + DÉPLOYÉ (PR #121, merge `56abb9e`).** Coût refente ADDITIF émis AUTO au chiffrage des devis sans-outil ([`refente.py`](../backend/app/services/rebobinage/refente.py)). Réutilise le moteur rebobinage Sprint-16 (axe Ø `calculer_bobines`) × **`nb_filles` résolu** (axe largeur, `nb_filles_force` — JAMAIS `nb_poses_laize`) → `total bobines = nb_filles × bobines_Ø` ; 1 fille → pas de ligne. `coût = temps × ConfigCouts.cout_exploitation_rebobineuse_eur_h + gâche raccord`. Porté par `ht_total` (`devis_total.contribution_refente_eur`) — **`prix_vente_ht` 7 postes + calage INTOUCHÉS**. Champs FR + migration `b3c5d7e9f1a2`. Persist `mode_sans_outil`/`laize_stock_mm`/`nb_filles_force` + `cylindre_id` nullable (POST sans-outil ne 422 plus, flag conservé au reload). `bat_calculs`/`rotation_se` INTOUCHÉS. Baseline **1183**.
- **Lot front — ✅ MERGÉ + DÉPLOYÉ (PR #120, merge `89c852e`).** Toggle Card Format avec/sans outil + masquages (intervalle dev, développé) + ligne « déchet latéral », consomme le contrat back A. Front pur, vitest **204**.

---

## Incident prod — 02/06/2026 (boot Railway crash post-merge #86, résolu #87)

- **Symptôme** : post-merge #86 (P1+P2), Railway prod en boot loop, HTTP 502 sur `devis-flexo-production.up.railway.app/`. Logs Railway : `psycopg2.errors.DatatypeMismatch: column "options" of relation "machine" is of type json but expression is of type text[]` au moment du `alembic upgrade head` lancé par le `CMD` du Dockerfile.
- **Cause racine** : dans la migration `b2c3d4e5f6g7`, l'INSERT machine passait `mi.options` directement (lu comme `list[str]` Python par SQLAlchemy depuis la colonne JSON de `machine_imprimerie`). En binding `text(":options")`, SQLAlchemy sérialisait en `ARRAY[...]` côté Postgres, alors que `machine.options` est typée `JSON` → mismatch.
- **Pourquoi le test PG ne l'a pas chopé avant merge** : le seed de `test_migration_p1p2_sous_fk_strictes_postgres` initialisait les MI avec `options='[]'::json` (liste vide). La valeur lue était `[]`, le code path ne tombait pas sur le mismatch. **Sentinelle aveugle** sur l'angle « options non-vides ».
- **État DB prod pendant l'incident** : migration alembic atomique → `ROLLBACK` Postgres automatique → révision maintenue sur `a1b2c3d4e5f6` (B3b). **Aucune corruption** (FK ni data).
- **Fix (PR #87)** :
  1. Migration : `json.dumps(options_list)` côté Python + `CAST(:options AS json)` côté SQL Postgres (dialect-aware ; SQLite reste sur `:options` natif → TEXT). Appliqué à upgrade ET downgrade.
  2. Sentinelle anti-régression : le test PG seede désormais avec options non-vides explicites (Mark Andy 2200 = `["UV","dorure_froid"]`, OMET = `["UV","hot_stamping","laminage"]`, Nilpeter = `[]` pour préserver le cas vide) + assert que `options` post-migration matche la valeur seedée.
- **Résolution** : merge #87 → redéploiement Railway → `alembic upgrade head` re-tente → migration appliquée (révision **`b2c3d4e5f6g7`**) → `/` répond 200 (`{"status":"ok","app":"devis-flexo"}`) en < 30 s.
- **Bonus du même test PG sous FK strictes** : il avait déjà attrapé **AVANT merge #86** un autre bug latent — **cascade UPDATE** dans le remap FK quand `new_machine_id` d'une itération coïncidait avec un `old_mi.id` futur (séquence machine basse → ids contigus). Corrigé par **UPDATE atomique CASE WHEN** (upgrade + downgrade). Railway preview de la PR avait passé par chance (ids prod hauts et disjoints). Sans le test PG FK strictes, le bug aurait silencieusement corrompu les FK `lot_production.machine_id` + `porte_cliche.machine_id` au déploiement prod.

→ Leçons reportées dans « En cours / à venir » §  Pattern migrations data à auditer.

---

## Carte multi-instances

### Chantier — Moteur matière : laize papier réelle (séquencé 2 temps) — **L1 + L2 COMPLETS (back) MERGÉS + DÉPLOYÉS PROD ✅**

**Décision Eric validée** : facturer la matière RÉELLE (bords inclus) = rebaser P1 sur `laize_papier`. La **gate read-only** a montré que le rebasage frontal n'est **PAS value-neutral** (V1a 1 449,09 € → **1 424,31 €**, valeur dépendante de l'intervalle absent de la fixture cost_engine). D'où un **séquençage en 2 temps**, **les deux désormais livrés côté back** :

- **L1 — ✅ COMPLET** : back (#107) + front (#108) **mergés + déployés prod**. Géométrie laize figée + saisie bord latéral (surplus extérieur) + décompo laize côté UI. **P1 INTOUCHÉ** → value-neutral, sacrés EXACTS (à l'époque).
- **L2 — ✅ COMPLET (back, #114)** : P1 rebasé sur `laize_papier` **plafonnée** `min(arrondi_palier(plaque + 2×bord), laize_utile)`, `marge_confort` **retirée** (double-comptait les bords), plancher `laize_mini_roulable` conservé (appliqué après le plafond). **RE-BASELINE COMPLÈTE des sacrés validée Eric** (V1a 1 424,31 · V1b 1 896,31 · V2 738,88 · V3 8 189,67 · V4 1 672,39 · V7a 6,73 · V8a 3,37 · tripwire P0b 695,36 ; V8b-e ratios inchangés). **P4 calage / Ø diamètre INTOUCHÉS**, zéro migration. Déployé prod (`/` → 200). **Front L2 = NO-OP confirmé CC2** : la décompo laize affiche passivement `geometrie_laize.laize_papier_mm` (désormais plafonnée) — aucun câblage ni recalibrage vitest. **Lot L2 = CLOS (back seul).**

**L1 — contrat LIVRÉ (#107 back + #108 front) :**

- Défaut bord : **`bord_lateral_effectif` = `chute_laterale_min_mm` (10 mm)**, PAS intervalle/2. **Symétrique** en L1 ; asymétrie g/d reportée. **Ne PAS toucher** lacets / intervalle interne (concepts séparés).
- **Entrée** `POST /api/optimisation/calculer` : `bord_lateral_mm` (float, `ge=0 le=100`, NULL → défaut chute_min) **+ `motif_bord_lateral`** (str, Règle 7 → warning non bloquant si surcharge sans motif).
- **Sortie** : `geometrie_laize = { laize_plaque_mm, bord_lateral_mm (EFFECTIF), laize_papier_mm, intervalle_laize_mm }` sur **`OptimisationConfigOut.geometrie_laize`** + écho `forcage_bord_lateral` / `motif_bord_lateral`. Front consomme + affiche la décompo (#108).

**L2 — contrat LIVRÉ (#114 back) :**

- `bat_calculs.calcul_laize_papier` : 5ᵉ param `laize_utile_mm` **OPTIONNEL** (défaut `None` = pas de cap → non-régressif pour les appels positionnels). Plafond appliqué AVANT le plancher.
- Propagation `laize_utile` : router `_to_config_out` (laize utile du candidat) + crud `_calcul_laize_papier_lot` (machine du lot).
- `poste_1_matiere` : `surface = laize_papier × ml` quand `DevisInput.laize_papier_mm` fourni (marge_confort retirée) ; fallback legacy `laize_utile + marge_confort` sinon. Clé `details` `laize_machine_mm`→`laize_facturee_mm` + `base_laize_source`.

**Carte qui-fait-quoi :**

- **L1 géométrie laize : COMPLET** (back #107 + front #108, déployés prod).
- **L2 rebasage P1 : COMPLET (back #114, déployé prod) — CLOS**. **Front = no-op confirmé CC2** (affichage passif, rien à câbler).
- **Lot Souveraineté (forçages Règle 7 non bloquants) : COMPLET** — back #112 + front #111 mergés + déployés prod.

**Prochaines étapes** :

- Chantier laize papier réelle **CLOS** (L1 + L2 livrés, front L2 no-op). Plus de PR front en attente.
- Suites Phase 2 (Lot 4b UI Stratégique, cleanup `TarifPoste`, `Machine` override P5) — cf. « En cours / à venir ».

---

> **⚠️ ARCHIVE HISTORIQUE (snapshots PRÉ-L2).** Les cartes datées ci-dessous
> citent les sacrés tels qu'ils étaient à la date de chaque PR : `V1a 1 449,09 €`
> et `tripwire P0b 704,07 €`. **Ces valeurs ont été REBASÉES par L2 #114
> (2026-06-05) à `1 424,31 €` et `695,36 €`** (P1 sur laize papier réelle
> plafonnée, `marge_confort` retirée). Ne PAS les reprendre comme sacrés vivants
> — la baseline sacrée à jour est en tête de doc (§ Baseline tests).

Lots livrés ce 03/06 :

- **#4.3 backend — `type_machine` (presse/finition) + filtrage des candidats optim** — branche `feat/type-machine-presse-finition`. **BACKEND only**. Le modèle `Machine` n'avait aucun champ de rôle → les lignes de finition (Daco) apparaissaient comme presses dans les candidats. Ajout **`Machine.type_machine`** (`String(20)`, NOT NULL, `server_default="presse"` ; validé app-side via `TYPES_MACHINE = {"presse","finition"}`, même idiome que `mode_par_defaut`). Migration **`e6f7a8b9c0d1`** : add column (toutes machines existantes → presse) + **UPDATE finitions par MOTIF robuste** (`lower(nom) LIKE %daco%/%rotoflex%/%finition%`, dialect-safe, **tous tenants** — validé Eric : une Daco/Rotoflex est une finition quel que soit le tenant). ⚠️ **Réconciliation noms** : la `Machine` réelle est `Daco D250 ligne finition` (pas « Daco D Series » = `MachineRebobineuse`, table séparée) ; `ROTOFLEX VSI 330` absent du seed mais couvert par le motif si présent en prod. **Seed mis à jour** (`machine.csv` + `seed_machine`) : Daco typée `finition` pour survivre au re-seed. **Loader optim** `charger_machines_actives` filtre désormais `type_machine="presse"` → les finitions ne génèrent plus de candidats. **SACRED INCHANGÉ** : un filtre de candidats ne touche pas le moteur → V1a 1 449,09 € + tripwire P0b 704,07 € EXACT (la dérivation `vitesse_moyenne_m_h/60` reste lue par le cost_engine sur les presses). +4 tests + 3 asserts B3a basculés (loader = presses uniquement). ZÉRO front (matcher inerte = volet front séparé), pas de modif moteur. Baseline **1141**.

- **Bug #5 — 1 calage par montage (+ correctif signature laize)** — branches `feat/bug5-calage-par-montage` (#102) puis `feat/bug5-signature-laize`. **BACKEND only**. Le calage (P4) est lié à l'**outil** (cylindre + clichés montés), pas à la bobine : un devis multi-lots comptait **N calages** (225 € × N) alors qu'un seul montage = 1 calage. Fix **EN AVAL, hors moteur** (mono-config V1a INTACT) : `cost_engine_aggregator.calculer_devis_multilots` accepte des **`montage_signatures`** par lot ; les lots **2+** d'une signature déjà vue voient leur **poste 4 déduit** (`cout_revient − calage`, prix recalculé `× (1+marge)`). **Signature finale = `(cylindre_id, machine_id, nb_poses_dev)`** — `nb_poses_laize` **retiré** (correctif post-#102) car changer la laize sur le même cylindre/presse = même montage (cas réel Eric : sinon laize différente → signatures distinctes → 2 calages à tort). `nb_poses_dev` conservé en garde-fou (clichés-autour distincts = montage distinct). `_chiffrer_devis_multilots` (crud) construit les signatures depuis `LotProduction`. **Heuristique signature** (zéro migration/UI ; override « changement d'outil/cliché » = vrai 2ᵉ jeu de die sur même cylindre → backlog CC2). Trace d'audit `details["calage_montage_deduplique_eur"]` par lot. **SACRED INCHANGÉ** : un devis à **1 lot** n'est JAMAIS touché → **V1a 1 449,09 € + tripwire P0b 704,07 € EXACT**. `montage_signatures=None` → legacy (somme pure). Tests : dédup unitaire agrégateur + tripwires e2e « 2 lots même montage » ET « même cylindre, laize différente ». ZÉRO front, `poste_4_calage`/`bat_calculs`/`rotation_se` intouchés. Baseline **1137**.

- **Bug #6 étape 6.2e-final — `ht_total` consomme le coût rebobinage** — branche `feat/bug6-2e-final-back-total`. **BACKEND only**. Le coût rebobinage entre désormais dans `devis.ht_total_eur`, depuis la ligne **multi-lots** (`rebobinage_multilots`, épaisseur réelle + paroi) quand elle existe, **sinon mono-lot** (fallback legacy), sinon 0. Helper pur [`devis_total.py`](../backend/app/services/devis_total.py) (`contribution_rebobinage_eur` + `ht_total_avec_rebobinage`, arrondi money 2dp). Recalcul branché au **chiffrage** (`crud.devis._chiffrer_devis_multilots`) ET aux **4 endpoints** rebobinage (apply/delete × mono/multi). **INVARIANT SACRÉ préservé** : `payload_output["prix_vente_ht_eur"]` reste la base cost_engine **PURE** (jamais augmentée) → **benchmark V1a 1 449,09 € + tripwire P0b 704,07 € EXACT** (scénarios sans rebobinage → contribution 0 → `ht_total = base`). ⚠️ `ht_total` **change** pour les devis avec rebobinage (effet voulu) → 3 tests « ht_total inchangé après apply » (sprint16 mono + 6.2e multi) **basculés** sur le nouveau contrat (base sacrée inchangée + `ht_total = base + rebob`). **ZÉRO front / modif formule** (`bat_calculs`/`rotation_se` intouchés). +8 tests, baseline **1131**. Drift baseline ETAT réconcilié.

- **Bug #6 étape 6.2e-back — coût rebobinage persisté PAR LOT** — branche `feat/bug6-2e-apply-multilots-cout`. **BACKEND only**. Corrige le coût HT rebobinage faux : la ligne persistée passait par l'apply **mono-lot** (`POST /api/devis/{id}/rebobinage`) avec épaisseur de **saisie figée (150 µm)**, faux dès ≥2 lots de matières différentes. **Nouvel endpoint additif `POST /api/devis/{id}/rebobinage-multilots`** : calcule le coût **par lot** (nb bobines + temps + mandrins) avec **épaisseur réelle** (matière du lot / saisie) + **override paroi**, via le **résolveur partagé `diametre_resolver`** (réutilisé, point de calcul unique). Persiste agrégé dans `payload_output["rebobinage_multilots"]` (`{applique, machine_rebobineuse_id, nb_lots, cout_total_rebobinage_eur, cout_mandrins_eur, lots[]}`) + `DELETE` symétrique. Le **cœur par lot** de `calculer-multilots` (6.2a) est **factorisé** en helper `_calculer_lots_multilots` partagé preview/apply. **Ligne ADDITIVE** : `ht_total_eur` (denorm cost_engine) **INCHANGÉ** — rebobinage = coût SÉPARÉ des 7 postes, jamais fusionné au benchmark. **Endpoint mono-lot conservé** (legacy, non-régressif). Contrat documenté pour le front **6.2e-front**. **ZÉRO front / modif formule** (`bat_calculs`/`rotation_se` intouchés). +7 tests, baseline **1123**, benchmark 13/13 + tripwire 704,07 EXACT.

- **Bug #6 étape 6.2c — Ø multilots persisté dans le devis + rapport** — branche `feat/bug6-2c-persist-diametre`. **FRONT only**. Clôt l'écart relevé en audit : le multilots (épaisseur réelle + paroi par lot) était **preview-only**, le rapport `/devis/[id]` affichait le **Ø candidat figé** (épaisseur saisie/150 + paroi tenant). Désormais : (1) l'étape **Rebobinage** pousse ses **échos par lot** au store ([`OptimisationPoseStore`](../frontend/src/app/optimisation/_components/OptimisationPoseStore.tsx) `diametreEchoesParLot`, indexés `id_candidat`) ; (2) au **chiffrage** ([`OptimisationChiffrage.tsx`](../frontend/src/app/optimisation/_components/OptimisationChiffrage.tsx)), `payload_visuel` de chaque lot est **enrichi** du Ø réel (`diametre_bobine_mm` écrasé + `diametre_depart_mm`/`epaisseur_effective_um`/`epaisseur_source`/`paroi_mm`/`nb_bobines_rebobinage`) — **fallback candidat** si pas d'écho (non-régressif) ; (3) le **rapport** ([`DevisResultMultiLots.tsx`](../frontend/src/components/devis/DevisResultMultiLots.tsx)) lit ces champs : **VUE B/C** (`SchemaImplantation`) reflète le Ø réel, **badge source** + **Ø départ (paroi)** affichés, et le **plan bobines** part de `epaisseur_effective_um`. Champs optionnels sur `OptimisationConfigOut` (devis legacy → fallback `diametre_bobine_mm`/`epaisseur_appliquee_um`). **ZÉRO backend / migration / `bat_calculs` / `diametre_resolver`** (persistance via `payload_visuel` déjà existante). Gate vert (tsc + lint + build + vitest **186/186**, +4 tests). ⚠️ Le Ø des VUE B/C des devis créés via le flux rebobinage **change** (effet voulu : reflète le vrai papier/paroi) — aucun Ø de référence figé impacté côté tests (fixtures « 242 mm » inchangées).

- **Bug #6 étape 6.2b — UI rebobinage multi-lots (1 Ø par lot)** — branche `feat/bug6-front-rebobinage-multilots`. **FRONT only**, branche l'endpoint additif `POST /api/rebobinage/calculer-multilots` (6.2a) sur l'UI. (1) Étape **Matière** ([`OptimisationPoseDetailLots`](../frontend/src/app/optimisation/_components/OptimisationPoseDetailLots.tsx)) : matière à `epaisseur_microns` **NULL → champ saisie opérateur** (µm) par lot ; sinon épaisseur catalogue en lecture. (2) Étape **Bobinage** ([`OptimisationRebobinage`](../frontend/src/app/optimisation/_components/OptimisationRebobinage.tsx)) : champ **override paroi mandrin** (mm) optionnel (vide = paroi tenant) + envoi **par lot** `{ matiere_id, epaisseur_saisie_um?, mandrin_mm, paroi_override_mm? }` + affichage **1 Ø + nb bobines PAR LOT** (boucle sur tous les lots, fin de la lecture mono-lot `selection[0]`) avec **badge de transparence** `epaisseur_source` (« matière » / « saisie opérateur » / « fallback 150 µm »). Store : `SelectionLot.epaisseur_saisie_um` + `setEpaisseurSaisieLot`. **Endpoint mono-lot conservé** (persistance chiffrage intouchée), **ZÉRO backend / `bat_calculs` / `rotation_se`**. Gate vert (tsc + lint + build + vitest **182/182**, +10 tests). Fixtures Ø « 242 mm » stables.

- **Bug #6 étape 6.2a — orchestration du Ø sur les vraies valeurs** — branche `feat/bug6-orchestration-diametre`. Le Ø part désormais de : **épaisseur réelle de la matière PAR LOT** (`matiere.epaisseur_microns` > saisie opérateur > fallback 150 µm) + **paroi mandrin** (`parametre_mandrin.epaisseur_paroi_mm`, Ø départ = mandrin + 2×paroi ; NULL → 0 **non-régressif**). **Résolveur partagé** [`diametre_resolver.py`](../backend/app/services/diametre_resolver.py) = **point de calcul unique** : alimente le Ø candidat (optim, `_to_config_out`) ET le calcul bobines (rebobinage). **Nouvel endpoint additif `POST /api/rebobinage/calculer-multilots`** = **1 Ø par lot** (l'endpoint mono-lot reste intouché). Contrat de sortie par lot documenté pour brancher le front en **6.2b** : `epaisseur_effective_um`, `epaisseur_source`, `mandrin_mm`, `paroi_mm`, `diametre_depart_mm`, `diametre_bobine_mm`, `nb_bobines`…. **ZÉRO front, ZÉRO modif formule** (`bat_calculs`/`rotation_se` intouchés, Ø passé comme `mandrin_mm`). **Candidat Ø inchangé** (paroi=0 partout → fixtures « 242 mm »-like stables, pas d'escalade). +15 tests, baseline **1116**, benchmark 13/13 + tripwire 704,07 EXACT.
- **Champ `parametre_mandrin.epaisseur_paroi_mm`** — branche `feat/parametre-mandrin-epaisseur-paroi`. Bug #6 (chaîne Format→Outil→Matière→Bobinage) **étape 6.1** : ajout d'une colonne `epaisseur_paroi_mm` (int, **NULLABLE**, default NULL) sur `ParametreMandrin`, migration additive `d5e6f7a8b9c0`. **Aucune valeur de paroi en dur** (NULL = inconnu, Eric renseignera). **NON câblé au calcul du Ø** (réservé à l'étape 6.2). Test modèle (nullable + persistance). ZÉRO câblage géométrie, ZÉRO modif `bat_calculs`/`rotation_se`. Baseline 1101, benchmark 13/13 + tripwire 704,07 EXACT.
- **Reroute « Nouveau devis » → `/optimisation`** — branche `feat/reroute-nouveau-devis-optimisation`. Les 2 CTA de création de [`/devis`](../frontend/src/app/devis/page.tsx) (`+ Nouveau devis` l.93, `Créer un devis` l.154) pointent désormais vers le flux optimisation (multi-lots, persistance `POST /api/devis` via étape 4 chiffrage) au lieu de `/devis/nouveau`. **Legacy mono-config CONSERVÉE** : `/devis/nouveau` + `DevisCalculForm` + `DevisSaveBar` restent accessibles par URL directe et portent le tripwire sacré 1 449,09 € (rien supprimé). Labels inchangés, **ZÉRO backend/moteur**. Test vitest : les 2 CTA pointent vers `/optimisation` (176/176).
- **#88 (mergé)** — **Fix (b) du bug « 3 machines non-candidates »** (UI seule). Ce n'était PAS une exclusion mais une **fusion** par dédoublonnage moteur (`_dedoublonner_configs`, #9.1) : les presses de même clé (cylindre/poses/intervalles → même laize utile) sont fusionnées sous une représentante, les équivalentes reléguées dans `noms_machines_compatibles[1:]` et non affichées (OMET/Nilpeter laize 330 = P5, Mark Andy 2200 320 capée à 5 mm collapsent sous P5 → « seuls P5 et Atelier 2 »). Fix : l'étape 2 affiche « Réalisable aussi sur : … ». **ZÉRO modif backend** (contrat API inchangé). Pistes « champ NULL » / « pairing cylindre » du BACKLOG_BUGS **infirmées**.
- **Fix config_couts démo ICE** — branche `fix/config-couts-demo-realignement-ice`. La ligne `config_couts(ent=1)` EN PROD restée aux defaults template `35/50/25` (jamais ré-alignée : Phase 1 `w7l9g1e5d3f8` crée la table sans backfill, Lot 4a `x8m1h2f6c4e9` n'UPDATE que ses 7 champs) → page devis rend `1 347,35 €` au lieu du sacré `1 449,09 €`. **Local/CI = OK** car re-seed frais ([seed.py:388](../backend/scripts/seed.py#L388) pose déjà 18/375/70). **Fix = migration data `c4d5e6f7a8b9`** : `UPDATE config_couts SET marge=18, exploitation_machine=375, operateur=70 WHERE entreprise_id=1` — idempotente, **scope strict ent=1** (autres tenants intouchés), downgrade no-op. Vérif : `1 228,04 × 1,18 = 1 449,09`. Garde-fou : 2 tests migration (ré-alignement + isolation multi-tenant + idempotence). Baseline 1100, benchmark 13/13 + tripwire 704,07 EXACT.

---

## Cleanup maintenance — 29/05/2026

- 17 branches feature/fix locales → **15 supprimées via `git branch -d`** (toutes mergées sur `origin/main`).
- 2 branches divergentes auditées + supprimées via `-D` :
  - `fix-prod-seeds-cas-b` : 3 commits dupliqués sur main par cherry-pick (SHA différents, contenu identique vérifié — migration `b4e9c7a1f3d2`, test `test_cas_metier_eric_etiquette_laize100_dev80_sur_cyl_104dents`, chore cylindres ICE ×3.175).
  - `docs/audit-phase2-cost-engine` : doc audit caduc (Phase 2 résolue), non archivé sur main pour éviter pollution doc.
- État final : seule `main` reste localement (synchro `origin/main`).

---

## Sacred invariants (rappel + pointeurs)

Ne JAMAIS modifier sans validation explicite. Tests verrouillés en CI.

- **Convention métier flexographique — 8 sens d'enroulement** : `SE1`-`SE8` mappés à des rotations VUE A / VUE C figées. Fichier : [`backend/app/services/rotation_se.py`](../backend/app/services/rotation_se.py). Les sens vierges `SE0` / `SE9` (sans impression) sont délégués à une **façade** [`sens_metadata.py`](../backend/app/services/sens_metadata.py) qui laisse `rotation_se` intact ; tests historiques `tests/test_rotation_se.py` continuent d'asserter que 0/9 lèvent `ValueError` côté `rotation_se`.
- **Benchmark `cost_engine` V1a / V8** : valeurs figées par expertise métier terrain, asserties strictement en CI sur fixture découplée DB. Fichier : [`backend/tests/test_cost_engine_benchmark.py`](../backend/tests/test_cost_engine_benchmark.py) — `EXPECTED_TOTAL_HT = Decimal("1449.09")` · `EXPECTED_COUT_REVIENT = Decimal("1228.04")`.
- **Benchmark `cost_engine` 5 cas (V1a / V1b / V2 / V3 / V4)** : verrou multi-cas Phase 2 sur fixture in-memory pure (snapshot ICE figé en INSERT Python). Fichier : [`backend/tests/test_cost_engine_5cas_benchmark.py`](../backend/tests/test_cost_engine_5cas_benchmark.py) — 11 tests. **Valeurs sacrées L2 (#114)** : V1a **1 424,31 €** HT / V1b **1 896,31 €** / V2 **738,88 €** / V3 **8 189,67 €** / V4 **1 672,39 €** (la fixture injecte la géométrie `laize_papier_mm=210`, plafond `laize_utile 220` ne mord pas).
- **Multi-tenant strict** : toute lecture `cost_engine` scopée `entreprise_id` via `get_config_couts_or_raise(db, entreprise_id)`. Pas de fallback silencieux (`CostEngineError` si la `ConfigCouts` du tenant manque). Fichier : [`backend/app/services/cost_engine/_config_reader.py`](../backend/app/services/cost_engine/_config_reader.py).
- **`UNIQUE(devis.numero)` scope tenant** : la contrainte est portée par l'index composite `ix_devis_entreprise_id_numero` (migration `y9n2i3g7d5f0`, fix #77). `generate_next_numero(db, entreprise_id)` lit `MAX(seq)+1` scope tenant (jamais `count+1`). Retry loop borné (5) sur collision dans `crud.create_devis` / `duplicate_devis`. Repro : [`backend/scripts/repro_409_devis_numero.py`](../backend/scripts/repro_409_devis_numero.py).
- **`update_devis` préserve le `payload_output` recalculé** : quand `lots_in is not None`, `_chiffrer_devis_multilots` enrichit `payload_output` (mode='multi-lots' + `details_par_lot[].details.postes[7]`) ; le pop conditionnel `payload_output`/`payload_input` du `fields` empêche le body de l'écraser (fix #78). Le flux mono-config legacy `DevisSaveBar` (sans `lots`) garde son contrat actuel (le body décrit le payload stocké tel quel). Repro : [`backend/scripts/dump_payload_output_post_put.py`](../backend/scripts/dump_payload_output_post_put.py).
- **Axes UI BAT / Schéma Implantation** : `X = laize` (cote horizontale au-dessus du cadre), `Y = dev` (cote verticale). TOUJOURS, indépendamment du sens d'enroulement. Fichier : [`frontend/src/components/SchemaImplantation.tsx`](../frontend/src/components/SchemaImplantation.tsx) (commentaires lignes ≈ 533 et 614+).
- **SSOT géométrie mm** : `calcul_diametre_bobine` (et inverses `calcul_nb_max_etiq_pour_diametre` / `calcul_diametre_requis_pour_nb_etiq`) — toute formule diamètre ↔ nb étiq passe par ce module. Fichier : [`backend/app/services/optimisation/bat_calculs.py`](../backend/app/services/optimisation/bat_calculs.py). Zéro duplication côté frontend (les surfaces UI cohérence/planificateur appellent les endpoints qui réutilisent ces helpers).
- **`cost_engine` lecture seule depuis les modules avals** : planificateur de bobines, fix planificateur surplus, rebobinage — tous alimentent une `Q` ou un `nb_bobines`, lisent le coût, ne modifient pas la logique métier `cost_engine`.

---

## Invariants métier (convention flexographique standard)

**Calage / mise en route (poste P4) = lié à l'OUTIL (plaque de découpe + clichés), PAS à la bobine.**

- Changer **uniquement la bobine mère** (autre matière, OU même matière en laize différente) sur le **même montage** → **AUCUN nouveau calage**. Un seul calage par montage/outil.
- Recompter un calage **UNIQUEMENT** s'il y a un vrai changement d'outil/cliché (ex. 2 jeux de clichés pour 2 laizes) → via une case dédiée « changement d'outil/cliché » par lot.
- **Bug connu (à corriger en sprint dédié)** : calage compté par lot → sur-facturation.

→ Toute modification du moteur de coût multi-lots doit être vérifiée contre cette règle. Si un calcul facture un calage **par lot** sur un même montage = **anomalie à signaler**.

---

## Procédures (rappel court)

- Avant tout push impactant le frontend : `cd frontend && rm -rf .next && npx tsc --noEmit && npx next lint && npm run build && npx vitest run`. Vercel preview est plus strict que le `npm run build` local non-nettoyé (cf. hotfix #69).
- Aucun merge tant que le preview Vercel et Railway de la PR ne sont pas verts (gate brief explicite, leçon #68).
- Les fichiers `*.test.{ts,tsx}` et `*.spec.{ts,tsx}` sont exclus du `next build` (tsconfig + eslintrc). Les ajouter au scope vitest, jamais au scope build prod.
- **Phase 2 cost_engine — pattern de lot** : pour chaque migration de tarif depuis `TarifPoste` vers `ConfigCouts`, (1) migration alembic additive avec `server_default` = template neutre + `UPDATE` scopé `entreprise_id=1` aux valeurs ICE legacy ; (2) seed démo aligné aux mêmes ICE ; (3) `default=` modèle = template neutre (nouveaux tenants via get-or-create) ; (4) `TarifPoste` champs correspondants conservés en base, plus consommés ; (5) fixture benchmark mise à jour aux ICE → V1a EXACT préservé (`1 449,09 €` à l'ère Phase 2 ; **rebasé `1 424,31 €` par L2 #114**).
