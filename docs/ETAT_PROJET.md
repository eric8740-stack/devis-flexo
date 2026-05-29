# État du projet

> **Source de vérité** : ce fichier est généré à partir de `git log`,
> `gh pr list`, et l'exécution réelle des tests. Aucune référence
> personnelle / employeur — uniquement des faits techniques et la
> convention métier flexographique verrouillée.

---

## En-tête

- **Date** : 2026-05-29
- **Branche active** : `main` (HEAD détaché à `8ed3bb5`)
- **Dernier commit** : `8ed3bb5` — *Merge pull request #73 from feat/planificateur-impose-nb-bobines*
- **Sprint en cours** : Phase 2 — refactor cost_engine config-driven (lots successifs sur `ConfigCouts` scopée tenant)

---

## PRs récemment mergées (10 dernières)

- #73 — feat(devis): planificateur imposer nb de bobines + gestion du surplus (facture/stock/réduire)
- #71 — fix(devis): cohérence et planificateur utilisent l'épaisseur de la matière saisie
- #70 — refactor(cost_engine): marge depuis `ConfigCouts` scopée tenant + fix isolation multi-tenant (Phase 2 / Lot 2)
- #69 — fix(build): exclure les tests du `next build` + correctif `PlanificateurBobines.test.tsx`
- #68 — feat(devis): persistance plan bobines + Q ajustée + forçage motif tracé
- #67 — test(cost_engine): benchmark V1a/V8 sur fixture figée (Phase 2 / Lot 1)
- #66 — feat(devis): planificateur de bobines (3 scénarios) sur le rapport de fabrication
- #64 — feat(devis): alerte cohérence Ø extérieur ↔ nb étiquettes / bobine (saisie)
- #63 — fix(devis): rapport rendu malgré off-by-one ordre entre lots et chiffrage
- #62 — feat(devis): rapport de fabrication (récap + 7 postes color-codés) sous le bobinage

## PRs ouvertes

- #72 — refactor(cost_engine): P7 et P5 depuis `ConfigCouts` scopée tenant (Phase 2 / Lot 3)
- #65 — docs(audit): cartographie config-driven vs hardcode `cost_engine` (Phase 2)
- #54 — feat(strategique-ui): onglet Stratégique — page 6 sections

---

## Baseline tests

- **pytest** : `1059 passed`, 22 warnings — CI GitHub Actions workflow `backend`, run `26622145161` (push sur `main` après merge #73, 2026-05-29 ≈ 06:41 UTC).
- **vitest** : `22 fichiers / 167 tests passed` — exécution locale 2026-05-29 ≈ 08:45 (durée ≈ 8 s, `npx vitest run`).
- **next build** : ✓ compiled successfully (vérifié hors cache `.next` lors du hotfix #69, gate brief : preview Vercel vert avant merge).

---

## En prod (modules livrés récents)

- Rapport de fabrication par lot sur `/devis/[id]` — récap chiffrage + 7 postes color-codés (#62, #63 robustesse off-by-one).
- Alerte cohérence Ø ext ↔ nb étiq/bobine à la saisie d'un devis — non bloquante, source de vérité backend (`bat_calculs`, SSOT mm) (#64, ε matière saisie en #71).
- Planificateur de bobines (rapport de fabrication, par lot) — 3 scénarios géométriques (A/B/C) + scénario IMPOSE anti-fléau (#66), persistance JSONB + Q ajustée + forçage motif tracé (#68).
- Planificateur — modes IMPOSE étendus : `nb_etiq` (historique), `nb_bobines`, `packaging` (N × X), mutuellement exclusifs. Gestion du surplus avec 3 décisions Q : facturer / stock / réduire (#73).
- Refactor `cost_engine` Phase 2 : Lot 1 benchmark figé (#67), Lot 2 marge scopée tenant + isolation multi-tenant (#70).
- Hotfix build : fichiers de test exclus du `next build` (`tsconfig.exclude` + `.eslintrc.ignorePatterns`) ; vitest continue de les exécuter via esbuild (#69).

## En cours / à venir

- **Phase 2 / Lot 3** (PR #72 ouverte) — postes P7 + P5 du `cost_engine` depuis `ConfigCouts` scopée tenant.
- **Audit Phase 2** (PR #65 ouverte) — cartographie config-driven vs hardcode.
- **Onglet Stratégique** (PR #54 ouverte) — UI 6 sections.
- Suite Phase 2 prévue : postes P1-P4 à migrer progressivement sur `ConfigCouts` (à confirmer par PR ultérieures).

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
