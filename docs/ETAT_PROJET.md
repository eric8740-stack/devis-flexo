# État du projet devis-flexo

> Vue d'ensemble vivante. Mise à jour à chaque PR Phase 2.
> **Dernière mise à jour** : 2026-05-29 (Phase 2 Lot 4a).

---

## Architecture cible (rappel brief stratégique v2)

Faire de **devis-flexo** un SaaS configurable par entreprise :
- chaque imprimerie pose ses propres tarifs/coûts via l'onglet **Stratégique** ;
- le `cost_engine` lit ses paramètres depuis ces configs (scope strict `entreprise_id`) ;
- les données ICE deviennent des **fixtures de test** (benchmark protégé), pas du seed prod.

`ConfigCouts` / `ConfigChangements` / `ConfigRoulage` = source unique par tenant.
`Machine` = override optionnel (reporté à un lot ultérieur).
`TarifPoste` = legacy, **dépréciation progressive** (colonnes gardées en base, plus consommées).

## Garde-fous (invariants sacrés)

1. **Benchmark `test_cost_engine_5cas_benchmark.py` = 0 failed.** V1a 1 449,09 € HT et autres sacrés EXACT préservés à chaque lot.
2. **Multi-tenant strict.** Toute lecture cost_engine scopée `entreprise_id` (helper `get_config_couts_or_raise` ; fix incident du bug `select(Entreprise).limit(1)` au Lot 2).
3. **`rotation_se.py` / 8 sens** : hors périmètre Phase 2.
4. **Pas de migration manuelle.** Alembic uniquement.

---

## Phase 1 — Socle Stratégique (livré, mergé)

3 tables config + API CRUD `/api/strategique` + UI 7 sections.

| Table | Type | PR |
|---|---|---|
| `ConfigCouts` | singleton/tenant | #53 |
| `ConfigChangements` | singleton/tenant | #53 |
| `ConfigRoulage` | collection (par format) | #53 |

UI Stratégique frontend (7 sections : Machines / Complexes / Encre / Outils / Roulage / Coûts & Marges / Charges) : #54 + #55 + #57.

---

## Phase 2 — Branchement cost_engine (en cours)

### Lot 1 — Benchmark en fixture pure (PR #67, mergé)
Le benchmark V1a/V8 quitte la DB live (`SessionLocal()` + seed CSV) pour une **session SQLite in-memory** peuplée par INSERTs Python en dur (snapshot ICE figé). Préalable bloquant : toute édition Stratégique du démo ne casse plus les sacrés.

### Lot 2 — Marge config-driven + fix multi-tenant (PR #70, mergé)
- `_resolve_pct_marge` lit `ConfigCouts.marge_standard_pct / 100` (scope `entreprise_id`).
- Fix incident du bug `select(Entreprise).limit(1)` (cross-tenant).
- Fallback `PCT_MARGE_FALLBACK = 0.18` + `Entreprise.pct_marge_defaut` → supprimés.
- Seed démo aligné 18 % (legacy ICE).

### Lot 3 — P5 Roulage + P7 MO config-driven (PR #72, mergé)
- P5 → `ConfigCouts.cout_exploitation_machine_eur_h` (au lieu de `TarifPoste.roulage_prix_horaire`).
- P7 → `ConfigCouts.cout_operateur_eur_h` (au lieu de `TarifPoste.mo_prix_horaire`).
- Helper `get_config_couts_or_raise` factorise la requête scopée (DRY orchestrator/P5/P7).
- Seed démo aligné 375 / 70 (legacy ICE).
- Override `Machine.cout_horaire_eur` (par machine pour P5) → reporté à un lot ultérieur.

### Lot 4a — P1/P3/P4/P6 config-driven (cette PR)

**7 tarifs migrés** depuis `TarifPoste` vers `ConfigCouts` (scope tenant) :

| Poste | Champ ConfigCouts (Lot 4a) | Unité | Démo (legacy ICE) | Template (nouveaux tenants) |
|---|---|---|---|---|
| P1 | `marge_confort_roulage_mm` | mm | 10 | 10 |
| P3a | `cliche_prix_couleur_eur` | €/couleur | 45.00 | 30.00 |
| P3b | `outil_base_eur` | € | 200.00 | 150.00 |
| P3b | `outil_par_trace_eur` | €/trace | 50.00 | 40.00 |
| P3b | `surcout_forme_speciale_facteur` ⚠️ renommé | × multiplicateur | 1.40 | 1.30 |
| P4 | `calage_forfait_eur` | €/devis | 225.00 | 180.00 |
| P6 | `finitions_prix_m2_eur` | €/m² | 0.1250 | 0.1000 |

⚠️ **Renommage `_pct` → `_facteur`** sur le surcoût forme spéciale : la valeur SQL est un **multiplicateur direct** (1.40 = ×1.40), pas un pourcentage — la formule reste `cout_outil × facteur`, mais le nom reflète la sémantique réelle.

Migration `x8m1h2f6c4e9` :
- Schéma additif (7 colonnes, NOT NULL, `server_default` = template).
- Data step : `UPDATE config_couts SET … WHERE entreprise_id=1` aux valeurs ICE legacy → V1a 1 449,09 € préservé.
- Réversible (`drop_column` ×7).

`TarifPoste` correspondants (`marge_confort_roulage_mm`, `cliche_prix_couleur`, `outil_base_eur`, `outil_par_trace_eur`, `surcout_forme_speciale_pct`, `calage_forfait`, `finitions_prix_m2`) : **conservés en base, plus consommés**. Dépréciation progressive comme Lots 2/3.

**Fallback `matiere_prix_kg_defaut`** : conservé sur `TarifPoste` (Q1 audit → option c). Code mort en pratique depuis Lot 1 complexe enrichi (tous les complexes ont prix_m2_eur + grammage). Migration séparée si nécessaire.

---

## Pas encore branchés (lots à venir)

- **Override `Machine.cout_horaire_eur`** (P5/P7 par machine) — décision archi : Machine = override optionnel sur ConfigCouts.
- **UI Stratégique pour les 7 nouveaux champs Lot 4a** (Lot 4b).
- **TarifPoste cleanup** (suppression colonnes dépréciées) — quand toutes les configs sont stables en prod.
- **`matiere_prix_kg_defaut`** (fallback P1) — à arbitrer (migrer vers ConfigCouts ou supprimer le fallback).

---

## Tests & qualité

- **Benchmark sacré** (`test_cost_engine_5cas_benchmark.py`) : 11/11, fixture in-memory pure.
- **Tests Phase 2 dédiés** : `test_orchestrator_marge_phase2.py` (Lot 2, 5 tests), `test_p5_p7_config_phase2.py` (Lot 3, 7 tests), `test_p1_p3_p4_p6_config_phase2.py` (Lot 4a, 11 tests).
- **Baseline backend complète** : voir CI sur main (≥ 1 061 après Lot 3, croissante avec les lots).

Pipeline CI : Python 3.13.5 pinné, WeasyPrint 65.1 vérifié, `alembic upgrade head` + `pytest -v` + Next build/lint + vitest + Railway preview.
