# État du projet

> **Source de vérité** : ce fichier est généré à partir de `git log`,
> `gh pr list`, et l'exécution réelle des tests. Aucune référence
> personnelle / employeur — uniquement des faits techniques et la
> convention métier flexographique verrouillée.

---

## En-tête

- **Date** : 2026-05-29
- **Branche active** : `main` (après merge #78)
- **Sprint en cours** : Phase 2 — refactor `cost_engine` config-driven (lots successifs sur `ConfigCouts` scopée tenant)

---

## PRs récemment mergées (10 dernières)

- #78 — fix(devis): update_devis préserve payload_output recalculé (pop conditionnel)
- #77 — fix(devis): UNIQUE(devis.numero) scopée tenant + MAX+1 + retry loop (résout 409 sur hard-delete)
- #75 — refactor(cost_engine): P1/P3/P4/P6 depuis `ConfigCouts` scopée tenant (Phase 2 / Lot 4a)
- #74 — docs: ajout/maj `ETAT_PROJET.md` (source de vérité état d'avancement)
- #73 — feat(devis): planificateur imposer nb de bobines + gestion du surplus (facture/stock/réduire)
- #72 — refactor(cost_engine): P7 et P5 depuis `ConfigCouts` scopée tenant (Phase 2 / Lot 3)
- #71 — fix(devis): cohérence et planificateur utilisent l'épaisseur de la matière saisie
- #70 — refactor(cost_engine): marge depuis `ConfigCouts` scopée tenant + fix isolation multi-tenant (Phase 2 / Lot 2)
- #69 — fix(build): exclure les tests du `next build` + correctif `PlanificateurBobines.test.tsx`
- #68 — feat(devis): persistance plan bobines + Q ajustée + forçage motif tracé

## PRs ouvertes

_aucune_

## PRs récemment fermées (non mergées)

- #76 — refactor(cost_engine) Lot 4a doublon (branche concurrente) — fermée, redondante avec #75.
- #65 — docs(audit) cartographie config-driven vs hardcode — fermée 29/05, contenu caduc résolu par Lots 1/2/3/4a.
- #54 — feat(strategique-ui) onglet Stratégique 6 sections — fermée 29/05, contenu déjà sur main par cherry-pick.

---

## Baseline tests

- **pytest** : `1083 passed`, 5 skipped, 21 warnings — exécution locale 2026-05-29 sur `main` (durée ≈ 337 s). +6 tests dédiés au fix update_devis (`test_devis_update_preserve_payload_output.py`), +4 au fix 409 (`test_devis_numero_fix_409.py`), +11 au Lot 4a (`test_p1_p3_p4_p6_config_phase2.py`).
- **vitest** : `22 fichiers / 167 tests passed` — exécution locale 2026-05-29 ≈ 08:45 (durée ≈ 8 s, `npx vitest run`).
- **next build** : ✓ compiled successfully (vérifié hors cache `.next` lors du hotfix #69, gate brief : preview Vercel vert avant merge).

---

## En prod (modules livrés récents)

- Rapport de fabrication par lot sur `/devis/[id]` — récap chiffrage + 7 postes color-codés (#62, #63 robustesse off-by-one). **Fix #78 (29/05)** : la modification d'un devis multi-lots ne masque plus le rapport+plan (régression : `update_devis` écrasait le `payload_output` recalculé par `_chiffrer_devis_multilots` avec le placeholder du body ; fix = pop conditionnel `payload_output`/`payload_input` quand `lots_in is not None`).
- Alerte cohérence Ø ext ↔ nb étiq/bobine à la saisie d'un devis — non bloquante, source de vérité backend (`bat_calculs`, SSOT mm) (#64, ε matière saisie en #71).
- Planificateur de bobines (rapport de fabrication, par lot) — 3 scénarios géométriques (A/B/C) + scénario IMPOSE anti-fléau (#66), persistance JSONB + Q ajustée + forçage motif tracé (#68).
- Planificateur — modes IMPOSE étendus : `nb_etiq` (historique), `nb_bobines`, `packaging` (N × X), mutuellement exclusifs. Gestion du surplus avec 3 décisions Q : facturer / stock / réduire (#73).
- Refactor `cost_engine` Phase 2 : Lot 1 benchmark figé (#67), Lot 2 marge scopée tenant + isolation multi-tenant (#70), Lot 3 P5/P7 scopés tenant via `ConfigCouts` (#72), **Lot 4a 7 tarifs P1/P3/P4/P6 scopés tenant via `ConfigCouts` (#75)**. **Dette config-driven Phase 2 identifiée 28/05 → résolue par Lots 1/2/3/4a (marge, P5/P7, P1/P3/P4/P6).**
- Numérotation devis robuste (#77, 29/05) — `UNIQUE(devis.numero)` scopée tenant via `ix_devis_entreprise_id_numero` + `generate_next_numero` en `MAX(seq)+1` scope tenant + retry loop borné (5). Résout 409 sur hard-delete (count+1 rebouchait les trous) et autorise deux tenants à avoir chacun `DEV-YYYY-0001` sans collision.
- Hotfix build : fichiers de test exclus du `next build` (`tsconfig.exclude` + `.eslintrc.ignorePatterns`) ; vitest continue de les exécuter via esbuild (#69).

## En cours / à venir

- **Phase 2 / Lot 4b** (à venir) — UI Stratégique pour les 7 nouveaux champs Lot 4a (`marge_confort_roulage_mm`, `cliche_prix_couleur_eur`, `outil_base_eur`, `outil_par_trace_eur`, `surcout_forme_speciale_facteur`, `calage_forfait_eur`, `finitions_prix_m2_eur`).
- **Phase 2 / cleanup `TarifPoste`** (à venir) — suppression des colonnes dépréciées P1/P3/P4/P5/P6/P7 quand toutes les configs sont stables en prod.
- **Phase 2 / `Machine` override** (à venir) — `Machine.cout_horaire_eur` comme override optionnel sur `ConfigCouts.cout_exploitation_machine_eur_h` (P5 par machine).
- **Phase 2 / `matiere_prix_kg_defaut`** (à arbitrer) — fallback P1 conservé sur `TarifPoste` (Q1 audit Lot 4a) ; migrer vers `ConfigCouts` ou supprimer le fallback.
- **Dette `payload_output` = donnée serveur** (PR séparé à prévoir) — durcissement intégral : recalcul serveur mono-config OU purge `DevisSaveBar` si `/devis/nouveau` abandonné. Le pop conditionnel actuel (#78) suffit à éteindre la régression sans casser le flux legacy.

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
- **Benchmark `cost_engine` 5 cas (V1a / V1b / V2 / V3 / V4)** : verrou multi-cas Phase 2 sur fixture in-memory pure (snapshot ICE figé en INSERT Python). Fichier : [`backend/tests/test_cost_engine_5cas_benchmark.py`](../backend/tests/test_cost_engine_5cas_benchmark.py) — 11 tests, V1a 1 449,09 € HT / V1b 1 921,09 € / V2 743,01 € / V3 8 437,47 € / V4 1 697,17 €.
- **Multi-tenant strict** : toute lecture `cost_engine` scopée `entreprise_id` via `get_config_couts_or_raise(db, entreprise_id)`. Pas de fallback silencieux (`CostEngineError` si la `ConfigCouts` du tenant manque). Fichier : [`backend/app/services/cost_engine/_config_reader.py`](../backend/app/services/cost_engine/_config_reader.py).
- **`UNIQUE(devis.numero)` scope tenant** : la contrainte est portée par l'index composite `ix_devis_entreprise_id_numero` (migration `y9n2i3g7d5f0`, fix #77). `generate_next_numero(db, entreprise_id)` lit `MAX(seq)+1` scope tenant (jamais `count+1`). Retry loop borné (5) sur collision dans `crud.create_devis` / `duplicate_devis`. Repro : [`backend/scripts/repro_409_devis_numero.py`](../backend/scripts/repro_409_devis_numero.py).
- **`update_devis` préserve le `payload_output` recalculé** : quand `lots_in is not None`, `_chiffrer_devis_multilots` enrichit `payload_output` (mode='multi-lots' + `details_par_lot[].details.postes[7]`) ; le pop conditionnel `payload_output`/`payload_input` du `fields` empêche le body de l'écraser (fix #78). Le flux mono-config legacy `DevisSaveBar` (sans `lots`) garde son contrat actuel (le body décrit le payload stocké tel quel). Repro : [`backend/scripts/dump_payload_output_post_put.py`](../backend/scripts/dump_payload_output_post_put.py).
- **Axes UI BAT / Schéma Implantation** : `X = laize` (cote horizontale au-dessus du cadre), `Y = dev` (cote verticale). TOUJOURS, indépendamment du sens d'enroulement. Fichier : [`frontend/src/components/SchemaImplantation.tsx`](../frontend/src/components/SchemaImplantation.tsx) (commentaires lignes ≈ 533 et 614+).
- **SSOT géométrie mm** : `calcul_diametre_bobine` (et inverses `calcul_nb_max_etiq_pour_diametre` / `calcul_diametre_requis_pour_nb_etiq`) — toute formule diamètre ↔ nb étiq passe par ce module. Fichier : [`backend/app/services/optimisation/bat_calculs.py`](../backend/app/services/optimisation/bat_calculs.py). Zéro duplication côté frontend (les surfaces UI cohérence/planificateur appellent les endpoints qui réutilisent ces helpers).
- **`cost_engine` lecture seule depuis les modules avals** : planificateur de bobines, fix planificateur surplus, rebobinage — tous alimentent une `Q` ou un `nb_bobines`, lisent le coût, ne modifient pas la logique métier `cost_engine`.

---

## Procédures (rappel court)

- Avant tout push impactant le frontend : `cd frontend && rm -rf .next && npx tsc --noEmit && npx next lint && npm run build && npx vitest run`. Vercel preview est plus strict que le `npm run build` local non-nettoyé (cf. hotfix #69).
- Aucun merge tant que le preview Vercel et Railway de la PR ne sont pas verts (gate brief explicite, leçon #68).
- Les fichiers `*.test.{ts,tsx}` et `*.spec.{ts,tsx}` sont exclus du `next build` (tsconfig + eslintrc). Les ajouter au scope vitest, jamais au scope build prod.
- **Phase 2 cost_engine — pattern de lot** : pour chaque migration de tarif depuis `TarifPoste` vers `ConfigCouts`, (1) migration alembic additive avec `server_default` = template neutre + `UPDATE` scopé `entreprise_id=1` aux valeurs ICE legacy ; (2) seed démo aligné aux mêmes ICE ; (3) `default=` modèle = template neutre (nouveaux tenants via get-or-create) ; (4) `TarifPoste` champs correspondants conservés en base, plus consommés ; (5) fixture benchmark mise à jour aux ICE → V1a 1 449,09 € EXACT préservé.
