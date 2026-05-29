# État du projet

> **Source de vérité** : ce fichier est généré à partir de `git log`,
> `gh pr list`, et l'exécution réelle des tests. Aucune référence
> personnelle / employeur — uniquement des faits techniques et la
> convention métier flexographique verrouillée.

---

## En-tête

- **Date** : 2026-05-29 (resync après merge Lot 4a)
- **Branche active** : `main` (HEAD détaché à `fc465dc` à la rédaction, sera mis à jour à `<commit-merge-#75>` après merge Lot 4a)
- **Sprint en cours** : Phase 2 — refactor cost_engine config-driven (Lots 1-4a livrés, suite à venir : exposition des 7 nouveaux champs côté UI Stratégique et fin de migration des postes restants)

---

## PRs récemment mergées (10 dernières)

- #74 — docs: ETAT_PROJET.md + neutralisation commentaire test benchmark
- #73 — feat(devis): planificateur imposer nb de bobines + gestion du surplus (facture/stock/réduire)
- #72 — refactor(cost_engine): P7 et P5 depuis `ConfigCouts` scopée tenant (Phase 2 / Lot 3)
- #71 — fix(devis): cohérence et planificateur utilisent l'épaisseur de la matière saisie
- #70 — refactor(cost_engine): marge depuis `ConfigCouts` scopée tenant + fix isolation multi-tenant (Phase 2 / Lot 2)
- #69 — fix(build): exclure les tests du `next build` + correctif `PlanificateurBobines.test.tsx`
- #68 — feat(devis): persistance plan bobines + Q ajustée + forçage motif tracé
- #67 — test(cost_engine): benchmark V1a/V8 sur fixture figée (Phase 2 / Lot 1)
- #66 — feat(devis): planificateur de bobines (3 scénarios) sur le rapport de fabrication
- #64 — feat(devis): alerte cohérence Ø extérieur ↔ nb étiquettes / bobine (saisie)

## PRs ouvertes

- #65 — docs(audit): cartographie config-driven vs hardcode `cost_engine` (Phase 2)
- #54 — feat(strategique-ui): onglet Stratégique — page 6 sections

---

## Baseline tests

- **pytest** : `1062 passed, 7 skipped, 0 failed` — exécution locale 2026-05-29 ≈ 10:00 sur HEAD courant Lot 4a (durée ≈ 5 m 22 s, `python -m pytest -q`). Les 7 skipped incluent 2 nouveaux skip Lot 4a (tests qui asseraient `PUT /api/tarif-poste/outil_base_eur → moteur reflète` — comportement cassé volontairement par la dépréciation des 7 clés legacy).
- **vitest** : `22 fichiers / 167 tests passed` — `npx vitest run` après `rm -rf .next` et `tsc --noEmit` exit 0.
- **next build** : ✓ compiled successfully (vérifié hors cache `.next`, gate brief : preview Vercel vert avant merge).
- **Benchmark V1a 1 449,09** : préservé exactement par construction (le UPDATE entreprise_id=1 de la migration `x8m1h2j6f0g4` et le seed démo posent les valeurs ICE historiques sur les 7 nouvelles colonnes ConfigCouts).

---

## En prod (modules livrés récents)

- Rapport de fabrication par lot sur `/devis/[id]` — récap chiffrage + 7 postes color-codés (#62, #63 robustesse off-by-one).
- Alerte cohérence Ø ext ↔ nb étiq/bobine à la saisie d'un devis — non bloquante, source de vérité backend (`bat_calculs`, SSOT mm) (#64, ε matière saisie en #71).
- Planificateur de bobines (rapport de fabrication, par lot) — 3 scénarios géométriques (A/B/C) + scénario IMPOSE anti-fléau (#66), persistance JSONB + Q ajustée + forçage motif tracé (#68).
- Planificateur — modes IMPOSE étendus : `nb_etiq` (historique), `nb_bobines`, `packaging` (N × X), mutuellement exclusifs. Gestion du surplus avec 3 décisions Q : facturer / stock / réduire (#73).
- Refactor `cost_engine` Phase 2 : Lot 1 benchmark figé (#67), Lot 2 marge scopée tenant + isolation multi-tenant (#70), Lot 3 P5/P7 (#72), Lot 4a 7 colonnes additives + branchement P1/P3/P4/P6 (cette PR).
- Hotfix build : fichiers de test exclus du `next build` (`tsconfig.exclude` + `.eslintrc.ignorePatterns`) ; vitest continue de les exécuter via esbuild (#69).
- État ETAT_PROJET versionné (#74) — source de vérité factuelle régénérable depuis git/gh/tests.

## En cours / à venir

- **Audit Phase 2** (PR #65 ouverte) — cartographie config-driven vs hardcode.
- **Onglet Stratégique** (PR #54 ouverte) — UI 6 sections. À étendre pour exposer en lecture/édition les 7 nouvelles colonnes Lot 4a (`marge_confort_roulage_mm`, `cliche_prix_couleur_eur`, `outil_base_eur`, `outil_par_trace_eur`, `surcout_forme_speciale_facteur`, `calage_forfait_eur`, `finitions_prix_m2_eur`) — actuellement consommées par le moteur via le modèle SQLAlchemy direct, **non exposées par le schema `ConfigCoutsBase/Update`** (à faire dans un Lot 4b ou avec PR #54).
- Suite Phase 2 prévue : finir la sortie ICE (notamment `matiere_prix_kg_defaut` qui reste sur `tarif_poste` comme fallback P1 — marqué TODO dans Lot 4a, hors scope).
- Suppression effective des 7 rows `tarif_poste` correspondantes : reportée à un lot ultérieur quand toutes les références code (frontend `ReadonlySections.tsx` Stratégique inclus) seront purgées.

---

## Sacred invariants (rappel + pointeurs)

Ne JAMAIS modifier sans validation explicite. Tests verrouillés en CI.

- **Convention métier flexographique — 8 sens d'enroulement** : `SE1`-`SE8` mappés à des rotations VUE A / VUE C figées. Fichier : [`backend/app/services/rotation_se.py`](../backend/app/services/rotation_se.py). Les sens vierges `SE0` / `SE9` (sans impression) sont délégués à une **façade** [`sens_metadata.py`](../backend/app/services/sens_metadata.py) qui laisse `rotation_se` intact ; tests historiques `tests/test_rotation_se.py` continuent d'asserter que 0/9 lèvent `ValueError` côté `rotation_se`.
- **Benchmark `cost_engine` V1a / V8** : valeurs figées par expertise métier terrain, asserties strictement en CI sur fixture découplée DB. Fichier : [`backend/tests/test_cost_engine_benchmark.py`](../backend/tests/test_cost_engine_benchmark.py) — `EXPECTED_TOTAL_HT = Decimal("1449.09")` · `EXPECTED_COUT_REVIENT = Decimal("1228.04")`.
- **Axes UI BAT / Schéma Implantation** : `X = laize` (cote horizontale au-dessus du cadre), `Y = dev` (cote verticale). TOUJOURS, indépendamment du sens d'enroulement. Fichier : [`frontend/src/components/SchemaImplantation.tsx`](../frontend/src/components/SchemaImplantation.tsx) (commentaires lignes ≈ 533 et 614+).
- **SSOT géométrie mm** : `calcul_diametre_bobine` (et inverses `calcul_nb_max_etiq_pour_diametre` / `calcul_diametre_requis_pour_nb_etiq`) — toute formule diamètre ↔ nb étiq passe par ce module. Fichier : [`backend/app/services/optimisation/bat_calculs.py`](../backend/app/services/optimisation/bat_calculs.py). Zéro duplication côté frontend (les surfaces UI cohérence/planificateur appellent les endpoints qui réutilisent ces helpers).
- **`cost_engine` lecture seule depuis les modules avals** : planificateur de bobines, fix planificateur surplus, rebobinage — tous alimentent une `Q` ou un `nb_bobines`, lisent le coût, ne modifient pas la logique métier `cost_engine`.

---

## Procédures (rappel court)

- Avant tout push impactant le frontend : `cd frontend && rm -rf .next && npx tsc --noEmit && npx next lint && npm run build && npx vitest run`. Vercel preview est plus strict que le `npm run build` local non-nettoyé (cf. hotfix #69).
- Aucun merge tant que le preview Vercel de la PR n'est pas vert (gate brief explicite, leçon #68).
- Les fichiers `*.test.{ts,tsx}` et `*.spec.{ts,tsx}` sont exclus du `next build` (tsconfig + eslintrc). Les ajouter au scope vitest, jamais au scope build prod.
