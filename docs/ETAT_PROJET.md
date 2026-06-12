# État du projet

> **Source de vérité** : ce fichier est généré à partir de `git log`,
> `gh pr list`, et l'exécution réelle des tests. Aucune référence
> personnelle / employeur — uniquement des faits techniques et la
> convention métier flexographique verrouillée.

---

## En-tête

- **Date** : 2026-06-12
- **Branche active** : `feat/D1-back-calage-montage` (rebasée sur `main`=`db1a8b7`) — **Lot D1 back implémenté, tests verts (1251/0), en attente validation/merge**. `main` = `db1a8b7` (après #155 — **fix 409 consommation front CC2**, distingue stock insuffisant / devis déjà consommé).
- **Sprint en cours** : **Lot D1 — calage lié au montage** (bug sur-facturation : calage par lot → par montage, cf. section 2026-06-12 · Lot D1). Module Stock COMPLET EN PROD (S1 #149/#150 · S2 #151/#152 · S3 #153/#154 · fix 409 #155). Lots F/E COMPLETS EN PROD. Chantiers CLOS antérieurs : « format sans outil », L1, L2, Souveraineté. Bugs #5/#6 **CLOS**.
- **Baseline** : **1251/0** · **sacrés EXACTS** V1a **1 424,31** / P0b **695,36** (inchangés) · **+ nouveau sacré D1** : 1 calage **1 125,22 €** / 2 calages **1 390,72 €**.
- **Carte qui-fait-quoi** : **CC1 = Lot D1** (calage montage, prêt à merger) ; **CC2 = fix 409** (mergé `db1a8b7`). **Prochain lot : D suite** (autres facettes calage) ; lot « facturation temps d'arrêt » = lot DÉDIÉ ultérieur (touche cost_engine → re-baseline).

---

## 2026-06-12 · Lot D1 back — calage lié au montage (`changement_outil_cliche`)

- **Bug métier corrigé** : le calage était compté PAR LOT → sur-facturation. Règle flexo : le calage est lié à l'**OUTIL (plaque + clichés)**, pas à la bobine. Changer de bobine mère (matière/laize) sur le même montage = **0 calage supplémentaire**.
- **Règle** : `nb_calages = 1 + nb_lots(changement_outil_cliche=True)`. Le 1er lot porte le calage du montage ; un lot 2+ n'ajoute un calage que sur un **vrai changement d'outil/cliché** (flag explicite). Remplace l'heuristique « signature de montage » (bug #5) par le flag.
- **Modèle** : `LotProduction.changement_outil_cliche` (bool, NOT NULL, default False) + **migration `f7a9c1e3d5b7`** (`op.add_column` natif FK-safe, leçon F). **Périmètre cost_engine : SEUL `cost_engine_aggregator.py`** (comptage calage) modifié ; `poste_4_calage`, orchestrator, autres postes, optimisation, rotation_se **INTOUCHÉS**.
- **API** : champ optionnel `changement_outil_cliche` (default False) sur `LotProductionCreate` / `LotProductionRead` / `DevisPreviewIn` → front ancien 100 % compatible (leçon #137). Câblé sur les 2 flux multi-lots (POST persist + preview/edit `preview_couts_multilots`).
- **SACRÉS** : V1a **1 424,31 € EXACT** (mono-lot, inchangé). **P0b 695,36 € EXACT INCHANGÉ** — P0b est un scénario **mono-lot** (asserte `len(details_par_lot)==1`) : `nb_calages=1` avant comme après ; la règle ne modifie QUE les devis ≥ 2 lots. **Aucun re-baseline**, aucun `xfail`.
- **Nouveau benchmark SACRÉ D1** (`test_benchmark_calage_montage_sacred.py`) : 2 lots même montage flags False → 1 calage → **1 125,22 €** ; lot 2 `changement_outil_cliche=True` → 2 calages → **1 390,72 €** (delta 265,50 = 1 calage 225,00 × 1,18). Lot 1 seul = 695,36 € (cohérent P0b).
- **Baseline = 1251/0** (+4 e2e D1 + 3 benchmark sacré D1 ; tests aggregator réécrits API flag).
- **Leçon 422** : contrat ENTRÉE enrichi (champ optionnel default False, non breaking) → déployer Railway avant un éventuel front D1.

---

## 2026-06-11 · Stock S3 back — lien devis↔stock (proposition FIFO + consommer/annuler)

- **Module ADDITIF strict** : `cost_engine` / `bat_calculs` / `optimiser_pose` / `/preview` / **chiffrage devis** INTOUCHÉS (diff vide). **Modèle Devis INTOUCHÉ**, **AUCUNE migration** (réutilise `MouvementStock.devis_id`).
- **`ml_requis` lu en LECTURE** depuis le moteur : `besoin_consommation` somme `devis_input.ml_total` par lot (= `bobinage.ml_total` du Lot F) via `_construire_devis_input_pour_lot` (réutilisé, non modifié). Devis n'a pas de `matiere_id` direct → matière/laize lues depuis ses `LotProduction`.
- **`GET /api/devis/{id}/proposition-consommation`** → `{ ml_requis, lignes[{bobine_id, emplacement, laize_mm, ml_restant, ml_propose}], stock_suffisant, manque_ml }`. **FIFO** : `matiere_id` du devis + `laize_mm >= laize_requise`, `statut=en_stock`, `ml_restant>0`, tri `date_creation` asc (= date de réception en stock), allocation gloutonne. Insuffisance = **non bloquante** (`stock_suffisant=false` + `manque_ml`).
- **`POST /api/devis/{id}/consommer`** `{ lignes:[{bobine_id, ml}] }` → 1 mouvement `sortie` (devis_id) par ligne + décrément `ml_restant`. **ATOMIQUE** : toutes les lignes validées AVANT écriture → **409 « stock insuffisant »** si une ligne dépasse, aucun effet partiel. Renvoie `{ mouvements, bobines }`.
- **`POST /api/devis/{id}/annuler-consommation`** → mouvement `entree` inverse du **net** encore consommé par ce devis (Σsortie − Σentrée par bobine), ré-incrémente `ml_restant`. **Idempotent** (2ᵉ appel = no-op).
- **Guard DELETE bobine (S1)** : une bobine avec historique de mouvements → **409 « bobine avec historique »** (la traçabilité prime). Seule modif d'un endpoint existant (stricte, non breaking).
- **« Déjà consommé »** déduit des mouvements `sortie` portant `devis_id` (pas de flag sur Devis). **Amendement gap #4** : la proposition expose `deja_consomme` (bool), `consomme_ml` (NET = Σsortie−Σannulation), `mouvements` (du devis) → le front affiche « consommé + Annuler » au lieu de la proposition. **`POST consommer` refuse si déjà consommé → 409 « devis déjà consommé »** (garde back contre double conso, indépendante du front). Filtre `GET /api/mouvements?devis_id=` ajouté.
- **Sacrés EXACTS** : V1a **1 424,31** / P0b **695,36** · **Baseline = 1244/0** (+10 tests S3 ; `test_stock_consommation_s3.py`).
- **Leçon 422** : API **nouvelle** → **déployer Railway AVANT** le front S3 (CC2). **Suite : D (calage).**

---

## 2026-06-11 · Stock S2 back — mouvements (journal d'audit + ajustement transactionnel)

- **Module ADDITIF strict** : `cost_engine` / `bat_calculs` / `optimiser_pose` / `devis` / `/preview` **INTOUCHÉS** (diff vide). Aucun endpoint existant modifié (seule la note de dépréciation `BobineUpdate.ml_restant` ajoutée — pas de breaking).
- **Modèle `MouvementStock`** (migration `e6f8a0b2c4d6`, `create_table` natif FK-safe) : `entreprise_id` FK CASCADE, `bobine_id` FK **CASCADE** (la suppression dure d'une bobine S1 emporte son historique), `devis_id` FK **SET NULL** (nullable, renseigné en S3), `type` (`entree`/`sortie`/`inventaire`), `ml` (>0), `ml_avant`/`ml_apres` (audit), `motif`/`reference` (nullable), `date_creation`.
- **Endpoints TRANSACTIONNELS** (un seul commit = mouvement + `bobine.ml_restant` atomiques) :
  - `POST /api/bobines/{id}/mouvements` → `{ mouvement, bobine }`. `entree` +ml · `sortie` −ml (**409 « stock insuffisant »** si `ml > ml_restant`, jamais négatif) · `inventaire` `ml_restant = ml` (audit ancien→nouveau).
  - `GET /api/bobines/{id}/mouvements` (historique d'une bobine, récent d'abord) · `GET /api/mouvements` (journal tenant, filtre `?type=`, paginé).
- **`ml` toujours positif** : le `type` porte le sens. PATCH `ml_restant` direct (S1) **DÉPRÉCIÉ** au profit du mouvement `inventaire` (mais conservé sans casse).
- **Sacrés EXACTS** : V1a **1 424,31** / P0b **695,36** · **Baseline = 1234/0** (+7 tests S2 ; `test_stock_mouvement_s2.py` : entree/sortie/inventaire ajustent `ml_restant`, sortie insuffisante → 409 atomique, historique + journal tenant, isolation cross-tenant 404).
- **Leçon 422** : API **nouvelle** → **déployer Railway AVANT** le front S2 (CC2).
- **Suite** : S3 lien devis↔stock (devis confirmé → mouvement `sortie` avec `devis_id`), puis D (calage).

---

## 2026-06-11 · Stock S1 back — modèle Bobine + CRUD (option B, granularité A)

- **Module ADDITIF strict** : `cost_engine` / `bat_calculs` / `optimiser_pose` / `devis` / `/preview` **INTOUCHÉS** (diff vide). Aucun endpoint existant modifié.
- **Granularité A** : 1 ligne = **1 bobine physique unique** (emplacement + ml restant propres).
- **Table `bobine`** (migration `d5e7f9a1b3c5`, `create_table` natif FK-safe) : `entreprise_id` FK CASCADE, `matiere_id` FK, `laize_mm`, `epaisseur_microns` (pré-rempli depuis la matière à la création, éditable), `ml_initial` (figé) / `ml_restant` (éditable), `rangee`/`etage`/`position`, `statut` (défaut `en_stock`). Emplacement exposé **calculé `A.0.25`**.
- **CRUD `/api/bobines`** scopé tenant strict (`get_or_404_scoped` → **404 anti-énumération**) : POST / GET liste (filtre `statut`, tri emplacement) / GET id / PATCH (champs partiels, `matiere_id`/`ml_initial` figés) / DELETE (suppression dure — pas d'enfants en S1). POST vérifie `matiere_id` scopé tenant + `ml_restant` initial = `ml_initial`.
- **Sacrés EXACTS** : V1a **1 424,31** / P0b **695,36** · **Baseline = 1227/0** (+9 tests S1 ; `test_stock_bobine_s1.py` : création/prefill, emplacement calculé, ml_restant éditable, isolation tenant, 404 anti-énum, suppression scopée, matière hors périmètre).
- **Leçon 422** : API **nouvelle** (aucun contrat existant modifié) → **déployer Railway AVANT** le front S1 (CC2).
- **Suite** : S2 mouvements (décrémentent `ml_restant`) → S3 lien devis↔stock (devis confirmé consomme le ml). Pas de gating produit `has_flexostock` en S1.

---

## 2026-06-11 — Lot F back : bobinage + appro matière (géométrie/appro, AUCUN chiffrage)

- **Value-neutral, AFFICHAGE seul** : `cost_engine` **INTOUCHÉ** (diff vide), `bat_calculs` (Ø) + `optimiser_pose` (métrage/poses) = **lecture seule**. La **facturation du temps d'arrêt = lot DÉDIÉ ultérieur** (touchera le cost_engine → re-baseline contrôlée).
- **`ml_total` LU depuis la source moteur existante** (`devis_input.ml_total`, celle du coût matière P1) — jamais recalculé de façon divergente.
- **Bloc sortie `bobinage`** (sibling de `geometrie`, `None` si état partiel → dégradation propre) : `ml_total`, `m2_total` (= ml × laize papier appro), `ml_par_bobine`, `nb_bobines` (= ceil(ml_total/ml_par_bobine)), `diametre_bobine_mm` (bat_calculs sur 1 bobine), `diametre_mandrin_mm`, `diametre_max_presse_mm`, `depasse_max` (Ø bobine > Ø max presse → **alerte** warn non bloquante), `nb_changements` (= nb_bobines−1), `temps_arret_min` (= nb_changements × temps_changement — **AFFICHÉ, PAS facturé**).
- **Entrées `/preview`** (overrides, sinon défauts config) : `ml_par_bobine` (sinon `Entreprise.ml_par_bobine_defaut`), `diametre_mandrin_mm` (défaut 76).
- **3 colonnes modèle + migration `c4d6e8f0a1b3`** : `Entreprise.ml_par_bobine_defaut` (2000), `Machine.diametre_max_bobine_mm` (1100), `Machine.temps_changement_bobine_min` (15). **DDL natif `op.add_column`/`op.drop_column` (PAS batch_alter_table)** : `machine` est une table PARENT (FK) et le recreate batch SQLite avec `PRAGMA foreign_keys=ON` forcé **vide les lignes** → pattern FK-safe de `a2b4c6d8e0f1` (bug attrapé par `test_migration_backfill_defaults`).
- **Sacrés EXACTS** : V1a **1 424,31** / P0b **695,36** · **Baseline = 1218/0** (+6 tests F ; `test_bobinage_f.py`).
- **Leçon 422** : contrat ENTRÉE change (`ml_par_bobine`/`diametre_mandrin_mm`) → **déployer Railway AVANT** le front F (CC2).

---

## 2026-06-10 — Lot E back : matière → épaisseur → Ø

- **Cascade** : `matiere_id` (entrée A1 existante) → Matiere **scopée tenant** → `epaisseur_microns` lue → passée à **`bat_calculs`** (SSOT **lecture pure**, intouché) pour le Ø. Aucun nouveau champ requête.
- **Fallback 150 µm TRACÉ** (jamais silencieux) : épaisseur NULL ou matière hors périmètre → `geometrie.epaisseur_fallback=true` + **alerte** (warn/info « Ø estimé sur 150 µm »). `epaisseur_um` explicite reste accepté si pas de `matiere_id` (value-neutral) ; la **matière prime** sur l'explicite.
- **Sortie** enrichie : `geometrie.epaisseur_utilisee_microns` (int) + `geometrie.epaisseur_fallback` (bool).
- **PATCH `/api/matieres/{id}`** body `{ "epaisseur_microns": int }`, scopé tenant (`get_or_404_scoped` → **404 anti-énumération**) → renvoie `MatiereOut` ; renseigne la vraie épaisseur sur les matières à NULL (élimine le fallback). **Aucune migration** (colonne `epaisseur_microns` préexistante, nullable).
- **Contrat figé microns** (source unique CC1+CC2) : `epaisseur_microns` (DB/PATCH), `epaisseur_utilisee_microns`/`epaisseur_fallback` (sortie).
- **Sacrés EXACTS** : V1a **1 424,31** / P0b **695,36** · `cost_engine`/`optimiser_pose`/`rotation_se`/`bat_calculs` **intouchés** (diff vide) · **Baseline = 1212/0** (+6 tests E ; 6 nouveaux `test_matiere_epaisseur_e.py`).
- **Leçon 422** : la sortie geometrie s'enrichit (entrée requête inchangée) → **déployer Railway AVANT** le front E (CC2). **Sans risque ici** : le front E (#145) n'envoie aucun nouveau champ `/preview` (juste `matiere_id` déjà accepté) + dégrade proprement si back absent ; PATCH user-triggered.
- **EN PROD** : #146 mergé → `main`=`2ca56de` → **Railway prod déployé** (vérifié : `GET /` 200 ; OpenAPI prod expose `PATCH /api/matieres/{matiere_id}` + `geometrie.epaisseur_utilisee_microns`/`epaisseur_fallback`).

---

## 2026-06-09 — Boucle live V0+C COMPLÈTE end-to-end

- **Pilotée par `/preview`** : configs + écarts (Règle 7) + matière + finitions + marge % + remise % → **bougent la marge en direct**.
- **Remise tracée à part**, par-dessus le **HT brut sacré** → `prix_ht_net`. `decompo_groupee` = **5 lignes** (matiere_p1 / impression_presse_calage / cliches_outil / option_finitions / refente).
- **Mergés ce jour** : #134 #135 #136 #137 #138 #139 #140 #141 #142.
- **Sacrés EXACTS** : V1a **1 424,31** / P0b **695,36** · `cost_engine`/`optimiser_pose`/`rotation_se`/`bat_calculs` **intouchés** · **1206/0**. **Baseline = 1 424,31** (**1 449,09 PÉRIMÉ**, cf. L2 #114).
- **Leçon 422** : front déployé **avant** back → la dégradation propre couvrait `configs=[]` vide **mais pas un schéma rejeté**. **Règle** : ne **jamais** envoyer un champ que le back déployé refuse ; **guards de bornes** côté front ; **déployer le back (Railway) AVANT le front (Vercel)** quand le contrat ENTRÉE change.
- **Horizon** : **E** (matière/Ø) → **F** (bobinage) → **D** (calage, **DÉBLOQUÉ**) ; `config_id` à étendre sur E/F.

---

## PRs récemment mergées (10 dernières)

- **(en attente) Lot D1 back** — feat(devis): **calage lié au montage** (CC1). Flag `LotProduction.changement_outil_cliche` → `nb_calages = 1 + nb_lots(flag=True)` (remplace l'heuristique signature bug #5). Migration `f7a9c1e3d5b7`. SEUL `cost_engine_aggregator` touché. V1a/P0b EXACTS inchangés (P0b mono-lot) + nouveau sacré D1 (1 125,22 / 1 390,72 €). Baseline **1251**.
- **#155** — fix(stock): **fix 409 consommation front** (CC2) — distingue les deux 409 (stock insuffisant / devis déjà consommé) via le `detail` de la réponse ; `ApiError` expose `detail`.
- **#154** — feat(stock): **Stock S3 back — lien devis↔stock** (CC1). `GET proposition-consommation` (FIFO + `deja_consomme`/`consomme_ml`/`mouvements`), `POST consommer` (mouvements sortie devis_id, atomique 409, **refus si déjà consommé**), `POST annuler-consommation` (entree inverse idempotente), guard DELETE bobine 409, filtre `GET /api/mouvements?devis_id=`. Modèle Devis intouché, **aucune migration** (réutilise `MouvementStock.devis_id`), chiffrage devis intouché. Baseline **1244**.
- **#153** — feat(stock): **Stock S3 front** (CC2) — action « Consommer le stock » sur un devis (proposition FIFO ajustable + bandeau manque non bloquant + 409 atomique géré + annuler), persistance `deja_consomme` au rechargement. → **Stock S3 COMPLET EN PROD**.
- **#152** — feat(stock): **Stock S2 front** (CC2) — mouvements entree/sortie/inventaire + historique bobine, consomme `/api/mouvements`. → **Stock S2 COMPLET EN PROD**.
- **#151** — feat(stock): **Stock S2 back — `MouvementStock` + endpoints mouvements** (CC1). Journal d'audit append-only, ajustement TRANSACTIONNEL de `ml_restant` (entree/sortie/inventaire), sortie insuffisante → 409, module ADDITIF (cost_engine/devis/preview intouchés). Migration `e6f8a0b2c4d6` (create_table natif). PATCH ml_restant S1 déprécié (sans casse). Baseline **1234**.
- **#150** — feat(stock): **Stock S1 back** — modèle `Bobine` + CRUD `/api/bobines` (CC1). Module ADDITIF, granularité A, emplacement `A.0.25`, multi-tenant strict, epaisseur pré-remplie. Migration `d5e7f9a1b3c5`. Baseline **1227**. → **Stock S1 COMPLET EN PROD** (+ front #149).
- **#149** — feat(stock): **Stock S1 front** (CC2) — page `/stock` CRUD bobines + inventaire (emplacement A.0.25), consomme `/api/bobines`. Module ADDITIF (cost_engine/devis/preview intouchés), granularité A (1 ligne = 1 bobine physique), emplacement calculé `A.0.25`, multi-tenant strict (404 anti-énum), epaisseur pré-remplie depuis la matière. Migration `d5e7f9a1b3c5` (create_table natif). Baseline **1227**.
- **#148** — feat(devis): **F front** (CC2) — réactive `ml_par_bobine` + `diametre_mandrin_mm` vers `/preview` (le réglage ml/bobine + Ø mandrin bougent nb_bobines/Ø en direct). → **Lot F COMPLET end-to-end EN PROD**.
- **#147** — feat(devis): **Lot F back — bobinage + appro matière** (CC1). Bloc `bobinage` sur `/preview` (ml/m²/nb bobines/Ø bobine/temps d'arrêt/alerte depasse_max), géométrie/appro **AUCUN chiffrage** (cost_engine intouché, bat_calculs/optimiser_pose lecture seule). 3 colonnes (Entreprise.ml_par_bobine_defaut 2000, Machine.diametre_max_bobine_mm 1100, Machine.temps_changement_bobine_min 15) + migration `c4d6e8f0a1b3` (DDL natif FK-safe). Baseline **1218**. Temps d'arrêt AFFICHÉ, pas facturé.
- **#146** — feat(devis): **Lot E back — matière → épaisseur réelle → Ø** (CC1). `matiere_id` (entrée A1) → Matiere scopée tenant → `epaisseur_microns` → `bat_calculs` (SSOT lecture pure, intouché) pour le Ø. Fallback **150 µm TRACÉ** (`geometrie.epaisseur_fallback` + alerte, jamais silencieux) ; matière prime sur `epaisseur_um` explicite. Sortie `geometrie.epaisseur_utilisee_microns`/`epaisseur_fallback`. **PATCH `/api/matieres/{id}`** `{epaisseur_microns:int}` scopé tenant (404 anti-énum). Aucune migration. **Sacrés EXACTS** V1a 1 424,31 / P0b 695,36 · `cost_engine`/`optimiser_pose`/`rotation_se`/`bat_calculs` intouchés. Baseline **1212**. Railway prod OK.
- **#145** — feat(devis): **Lot E front** (CC2) — sélecteur matière : Ø bobine live + épaisseur utilisée + bandeau fallback visible + enregistrement épaisseur au catalogue (PATCH matière). Consomme `geometrie.epaisseur_utilisee_microns`/`epaisseur_fallback` (dégradation propre si back absent), input `/preview` `epaisseur_um` (A1) inchangé.
- **#142** — feat(devis): **Étape 2 front** — réactive l'envoi `config_id` + forçage écarts vers `/preview` (boucle live complète). (CC2.)
- **#139** — feat(devis): **V0 front** — panneau prix live (rail sticky + marge/remise), consomme `marge_pct`/`remise_pct`/`prix_ht_net`/`decompo_groupee`. (CC2.)
- **#140** — feat(devis): **`/preview` contrat ENTRÉE Lot C** — `DevisPreviewIn` accepte `config_id` ('cyl-mach-DxL', **fige** cylindre/machine/poses → `geometrie.nb_poses` = poses_total config) + `force_intervalle_laize`/`intervalle_laize_mm` + `nb_poses_laize_force`, threadés dans `optimiser_pose` (params existants). **Ferme le 422 à la source** (dette stopgap #137). Défauts value-neutral, cost_engine intouché. Baseline **1206**.
- **#136** — feat(devis): **`/preview` V0 boucle marge live** — `marge_pct` override (→ `pct_marge_override`) + `remise_pct` **tracée à part** (par-dessus HT brut, hors coût → `remise_eur`/`prix_ht_net`) + `decompo_groupee` (5 lignes métier, somme = coût) + `_appliquer_remise` isolée (archi ouverte marge-cible). cost_engine INTOUCHÉ, value-neutral. Baseline **1202**.
- **#135** — feat(devis): **`/preview` configs cylindre × machine + écarts (Lot C back)** — `configs[]` (tri score, top 3 `recommande`) + `ecarts`, via réutilisation `optimiser_pose` (SSOT, lecture pure, AUCUN coût). Sans-outil → `configs=[]`, `intervalle_dev=0`. Baseline **1199**.
- **#134** — feat(devis): **Lot C front** « choix outil & pose » (CC2) — 3 cartes config + table N configs + bloc écarts, consomme `configs[]`/`ecarts`. ⚠️ a introduit le 422 traité par **#137** (inputs non acceptés).
- **#132** — feat(devis): **A2bis front** — chips finitions (aria-pressed, actif orange) + coût marginal « +X € » par code via `options[].delta_eur` (impact production → « chiffré bientôt », jamais +0 €) + `couleur_plus` ; requête `/preview` + POST via `options_codes`.
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

- **Aucune** — boucle live V0+C mergée end-to-end (back #140 + front V0 #139 + réactivation inputs #142) ; cadrage V2 #133 mergé.

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
  - **Lot C (configs outil & pose)** : ajout NON breaking `configs [{id, cylindre_dents, developpe_mm, machine, poses_laize/dev/total, delta_dev_mm, delta_laize_mm, sens, score, recommande}]` (tri score DESC, **top 3 `recommande`**) `+ ecarts {intervalle_laize_mm (défaut 5), intervalle_dev_mm, nb_poses_laize "auto"|int, force_intervalle_laize}`. **Réutilise `optimiser_pose` (SSOT) — géométrie/lecture PURE, AUCUN coût** ; mode sans outil → `configs=[]`, `intervalle_dev=0`. (#135.)
  - **Lot C-inputs (contrat ENTRÉE)** : `DevisPreviewIn` accepte désormais `config_id` ('cyl-mach-DxL', **fige** cylindre/machine/poses dans le calcul → `geometrie.nb_poses` = poses_total de la config) + `force_intervalle_laize`/`intervalle_laize_mm` + `nb_poses_laize_force` (Règle 7), threadés dans `optimiser_pose` (params existants). **Ferme le 422 à la source** (dette du stopgap #137). Défauts = value-neutral. cost_engine intouché. (CC1 `feat/L-back-Cin-preview-inputs`.) **Au merge → CC2 réactive l'envoi `config_id` + écarts.**
  - **V0 (boucle marge live)** : input `marge_pct` (override %, → `DevisInput.pct_marge_override`, défaut tenant `ConfigCouts.marge_standard_pct`) + `remise_pct`. Sortie + `remise_eur, prix_ht_net` (remise **tracée à part**, par-dessus le HT brut, **hors coût de revient** ; `prix_ht` reste le HT brut 7 postes sacré) + `decompo_groupee {matiere_p1=P1, impression_presse_calage=P2+P4+P5+P7, cliches_outil=P3, option_finitions=P6, refente}` (somme = coût de revient + refente ; NON breaking, en plus de `decompo` plate). Fonction `_appliquer_remise` isolée (archi ouverte marge-cible, pas de mode cible en V0). cost_engine INTOUCHÉ, value-neutral par défaut. (CC1 `feat/L-back-V0-preview-live`.)
    - `options[]` = delta marginal **PAR CODE** sur le catalogue tenant (`€ × (1+marge)`, additif) + `couleur_plus`. **Garde-fou** : option à impact production sans forfait → `impact_production:true` + `delta_eur:null` (front : « impact production (chiffré bientôt) », jamais un faux +0 €).
  - **Wiring (réutilisation pure, moteur INTOUCHÉ)** : `nb_couleurs`→`nb_couleurs_par_type` (P2+P3a) ; `options_codes`→€ catalogue `OptionFabrication`→`forfaits_st`→**P6** (`OptionDisponiblePublic` inchangé, pas de fuite `forfait_eur`) ; `machine_id`→P5 (défaut 1ère presse) ; tout via `LotProduction` transitoire + `_construire_devis_input_pour_lot` + `MoteurDevis`.
  - **Pointeur front** : client typé [`frontend/src/app/devis/nouvelle/devisPreview.ts`](../frontend/src/app/devis/nouvelle/devisPreview.ts) + [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts).
  - **🔴 Backlog (chantier séparé, sacred-sensitive, validation Eric)** : **pricing options PRODUCTION** (coef vitesse/gâche, temps calage) **dans le cost_engine** — touche P3/P4/P5 → **benchmarks à revérifier EXACTS sous contrôle**. + best-effort V1 : `diam_max_mm` sourcing fin ; `machine_id` ← contrat optim (front B).
- **CC2 — front A1 : ✅ MERGÉ (#123, `13a579d`).** Page `/devis/nouvelle` réactive + design FlexoSuite, consomme `/api/devis/preview` (swap mock → endpoint live). Recalc live debounce 250ms + AbortController + keep-last ; parse le contrat complet (€/1000, géométrie, décompo, options/déltas, alertes) ; select presse masqué si tenant mono-machine. vitest **218**.
- **CC2 — front A2 : ✅ MERGÉ (#129).** Transitions douces du toggle sans-outil (`Collapsible` grid-rows+opacité, a11y `aria-hidden`/`tabIndex`) + pré-remplissage profil bobine client (Ø mandrin/Ø max/sens depuis `Client`, fallbacks tracés) + `client_id` persisté.
- **CC2 — front A2bis : ✅ MERGÉ (#132).** Chips finitions (`aria-pressed`, actif orange) + coût marginal « +X € » **par code** via `options[].delta_eur` (impact production → « chiffré bientôt », jamais +0 €) + `couleur_plus` ; requête `/preview` + POST via `options_codes`. vitest **220**.

---

## Chantier — Devis page unique **V2** (maquette north-star, remplacement complet du wizard) — 🟡 CADRAGE (à trancher 2026-06-09)

> Maquette HTML fournie par Eric le 2026-06-08 (`devis-flexo-maquette-v9 (1).html`,
> « pas finie »). C'est la cible complète : **toute** la saisie devis sur un
> écran réactif, en 2 colonnes + rail prix sticky, accordéon 6 sections. A1/A2/
> A2bis (ci-dessus, en prod) = socle ; V2 = la suite, par lots. **Rien décidé**,
> Eric tranche le 09/06. Avant tout code : vérifier les contrats back réels
> (optim wizard, rebobinage) comme pour /preview — ne pas coder contre une spec.

**Déjà en prod (socle A1+A2+A2bis)** : hero prix HT/€1000/marge live · laize/dev/qté/couleurs · toggle sans-outil (transition) · matière+épaisseur · bobinage mandrin/Ø max/sens · chips finitions + « +X € » + couleur_plus + impact prod · décompo postes+refente · prefill client · Valider→devis.

**Nouveaux blocs de la maquette (non bâtis)** :
1. **Layout 2 colonnes + rail sticky** (prix + décompo détaillée + carte « config retenue » + Valider/**Aperçu PDF**) + **accordéon numéroté 1→6**. 100 % front, zéro back.
2. **Section 2 « Choix outil & pose »** (cœur) : **config cards scorées** (3 meilleures) + table « 75 configs » = l'**auto-optim** différé (« lot front B », sélecteur malin du même `cylindre_id` ; le wizard `/optimisation` calcule déjà ces configs → réutilisable) ; **Écarts + Souveraineté Règle 7** (forcer intervalle dev/laize, bord latéral, nb poses — *tracé* ; payload lot porte déjà `intervalle_dev_reel_mm`, `intervalle_laize_reel_mm`, `bord_lateral_mm`) ; **Cadence & calage** (vitesse, temps calage, €/h) + types de changement.
3. **Multi-lots** : répartir la quantité sur plusieurs développés/laizes (consommer le stock). `DevisCreate.lots[]` le supporte déjà.
4. **Section 5 enrichie** : sens enroulement **8 tuiles**, **plan de bobines** (rebobinage — endpoints existants), lacets, tarifs mandrins, entrée fichier (radio), **délais appro→livraison** (jours ouvrés).
5. **Matière enrichie** (laize calculée+chute live, adhésif, certifs sanitaires/env, stockage→conseil) · **Commercial** (marge éditable + remise) · **Section 1** (forme, rayon, tolérance qté, matière transparente).

**Découpage proposé (CC2, 1 PR/lot)** :
- **C — Layout & rail** : 2 colonnes + rail sticky + accordéon. *Recommandé en 1er* (pose le cadre, 100 % front, aucune dépendance CC1).
- **D — Section 2 outil & pose** : config cards auto-optim (réutilise l'optim wizard) + écarts/Règle 7 + cadence/calage. *Le plus gros ; remplace le select cylindre actuel.*
- **E — Multi-lots** + calage/changements.
- **F — Section 5** : sens 8 tuiles + plan bobines + lacets + tarifs mandrins + entrée fichier + délais.
- **G — Matière/Commercial/Section 1** (complétude).

**Questions ouvertes (à trancher 09/06)** :
1. Finir/itérer la maquette d'abord (retour design section par section) **ou** commencer à coder vers la cible ?
2. Si code : démarrer par **C (layout+rail)** ou prioriser les **config cards section 2** (débloquent l'auto-optim) ?

**Hors scope tant que pas tranché** : bascule des CTA wizard → `/devis/nouvelle` (gated, après validation terrain Eric). Le wizard reste intact.

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
