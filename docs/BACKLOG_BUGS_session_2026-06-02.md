# Backlog bugs — relevés session 2026-06-02

Contexte : revue manuelle de l'app (compte démo `entreprise_id=1`). 6 points relevés.
Chaque point = **audit read-only d'abord** (quel fichier, qu'est-ce qui est câblé), puis fix.

## Principe de séquencement
- Ne pas empiler deux changements SACRED en même temps.
- ~~Sprint unify `Machine ↔ MachineImprimerie` (P1+P2) → le finir avant les bugs moteur.~~ ✅ **FAIT** post-merges #86 + #87 (02/06).
- Bugs moteur (#5, #6) = **sprints dédiés**, après unify, sous benchmark + validation.
- Bugs UX/câblage (#2, #3, #4, intervalle laize, filtrage machines) = **légers, hors SACRED**, faisables indépendamment / en parallèle.

---

## 🔴 NOUVEAU — Bug post-unify P1+P2 (02/06, prioritaire)

### 0. Les 3 presses migrées (Mark Andy 2200 / OMET / Nilpeter) ne ressortent PAS comme candidates dans l'optim
**Observé** post-merge #86 + #87 sur compte démo (`entreprise_id=1`) : les 6 machines présentes en BDD sont bien `actif=true` (vérifié) :
- Mark Andy P5 (parc historique)
- Daco D250 finition (parc historique)
- Atelier 2 (parc historique)
- Mark Andy 2200 ⚠️ migrée depuis MI
- OMET XFlex 330 ⚠️ migrée depuis MI
- Nilpeter FA-22 ⚠️ migrée depuis MI

Mais l'étape « Candidats viables » de l'optim n'affiche que **P5 et Atelier 2**. Les 3 presses migrées ne génèrent **aucune config viable** → exclues silencieusement.

**Suspect** : la migration `b2c3d4e5f6g7` INSERT machine avec plusieurs champs **NULL** (mapping MI → Machine sans équivalent direct) :
- `duree_calage_h` = NULL (pas dans MI)
- `largeur_max_mm` = NULL (pas dans MI)
- `commentaire` = NULL (pas dans MI)
- `vitesse_max_m_min` ← `MI.vitesse_nominale_constructeur_m_min` (peut être NULL pour certaines MI)

Si `charger_machines_actives` ou la génération de candidats filtre dur sur un de ces champs NULL (ex. `WHERE vitesse_max_m_min IS NOT NULL`), les 3 presses sont écartées silencieusement.

**À investiguer (read-only d'abord, puis fix)** :
1. [`backend/app/services/optimisation_loader.py::charger_machines_actives`](../backend/app/services/optimisation_loader.py) — filtre `actif=True` + scope tenant déjà OK (cf. tests B3a). Y a-t-il un filtre supplémentaire sur `vitesse_moyenne_m_h IS NOT NULL` ou un autre champ que la migration laisse NULL ?
2. Génération de candidats (`backend/app/services/optimisation/*`) — règles métier qui pourraient écarter une machine sans `largeur_max_mm` / `duree_calage_h` (effet banane, capacité couleurs, contrainte cliente).
3. Appariement cylindre ↔ machine — les 3 presses migrées n'ont-elles pas de cylindre compatible côté `CylindreMagnetique` (qui a des colonnes `nb_pc_10p / nb_pc_13p / nb_pc_2200 / nb_pc_p5`) ? Mark Andy 2200 ↔ `nb_pc_2200` semble couplé, mais OMET et Nilpeter n'ont pas leur colonne → exclues côté cylindre ?

**Hypothèse forte** : c'est l'appariement cylindre ↔ machine (point 3). Le schéma `CylindreMagnetique` connaît `nb_pc_10p / 13p / 2200 / p5` — donc seulement Mark Andy 2200 a une colonne dédiée, et P5 a la sienne (`nb_pc_p5`). Daco/Atelier sont des lignes finition (pas concernées par l'appariement cylindre). OMET et Nilpeter n'ont pas leur colonne → 0 cyl compatible → 0 config.

**Scope/risque** : si confirmé, soit (a) ajouter `nb_pc_omet` / `nb_pc_nilpeter` (migration + seed compte démo), soit (b) redesign vers un modèle générique d'appariement (M:N `CylindreMachine` au lieu de colonnes par machine). Sprint dédié, mini-cadrage avant code.

---

## Déjà traité

### 1. Rebobineuse / suppression de machines — SÉCURISÉ
L'onglet Rebobinage sélectionne une « rebobineuse du parc » (« Daco D-Series »).
La migration unify supprimait Daco/Atelier → risque de casser le rebobinage.
→ Correction donnée : la migration unify **ne supprime plus aucune fiche `Machine`** (P5/Daco/Atelier conservés). Elle se limite à : ajouter les 3 presses + remapper `lot_production`/`porte_cliche` + DROP `machine_imprimerie` + `configuration_pose`. ✅ Appliqué dans #86.
→ À confirmer avant le futur ménage « 4 presses » : comment le rebobinage référence sa machine (`Machine` vs `MachineRebobineuse`, FK ou autre ?).

---

## Sprints moteur (SACRED — dédiés, après unify, benchmark obligatoire)

### 5. Calage compté par lot au lieu d'1 par montage — PRIORITAIRE
**Observé** : devis 2 lots → P4 « Mise en route / Calage » = 225 € **sur chaque lot** (≈450 € total) alors qu'il n'y a qu'un seul montage.
**Règle métier (convention flexographique standard)** : le calage est lié à **l'outil** (plaque de découpe + clichés), pas à la bobine. Changer juste la bobine mère (autre matière, ou même matière en laize différente) sur le même montage = **pas de nouveau calage, pas de recalcul depuis zéro**.
**À faire** :
- Par défaut, un changement de bobine entre lots du même montage → **un seul calage** (1er lot), suivants = changement de bobine seulement.
- Case par lot « **changement d'outil / cliché** » → réactive le calage pour ce lot (vrai cas : 2 jeux de clichés pour 2 laizes).
- Trancher : compter un mini-coût « montée bande » au changement de bobine, ou rien.
**Scope/risque** : change la logique du moteur → **bouge les prix + le benchmark**. Sprint dédié, nouveau benchmark, validation explicite.

### 6. Flux matière ↔ bobinage incohérent + ordre des étapes
**Observé** : le calcul bobinage utilise **épaisseur 150 µm par défaut** au lieu de l'épaisseur de la matière sélectionnée → le Ø bobine ne coïncide pas avec le vrai papier. La matière est demandée à plusieurs endroits déconnectés.
**Cible (chaîne logique A → B)** : Format (laize × dev) → Outil (cylindre/plaque) → Matière (papier) → Bobinage qui **finalise le Ø en fonction de l'épaisseur réelle du papier choisi**.
**À faire** :
- Propager la matière sélectionnée jusqu'au bobinage ; le Ø se calcule sur **son épaisseur réelle**, pas 150 µm.
- Revoir l'ordre des étapes pour suivre la chaîne ci-dessus.
**Scope/risque** : touche `bat_calculs` (géométrie Ø = SACRED-géométrie) + redesign de flux → **mini-cadrage design avant code** (ordre exact, où vit chaque champ).

---

## Bugs UX / câblage (légers, hors SACRED, parallélisables)

### 2. « Options de fabrication » en double
Même liste affichée dans **Optimisation de pose** (niveau lot) **et** Chiffrage final « **globales** » (niveau devis).
Note dans l'UI des globales : « le moteur consommera ces codes à la prochaine itération — pour l'instant snapshot dans le payload » → **les globales ne sont pas branchées au prix**.
**À faire** : confirmer lequel alimente réellement le moteur. Décider : clarifier les libellés (lot vs global) **ou masquer les globales** tant qu'elles ne sont pas câblées.

### 3. Client à re-saisir partout
Le client apparaît à plusieurs étapes (rebobinage, chiffrage final, début de devis). L'UI dit « synchronisé / propagé ».
**À faire** : vérifier si la synchro **marche vraiment** (sélecteurs répétés à unifier) ou si c'est un **vrai bug de propagation**. Cible : **saisie unique** au début + **lecture seule** partout ailleurs. Lister les points de saisie.

### 4. « Outils compatibles » inerte
La sélection d'un cylindre dans « Outils compatibles » **n'alimente rien** en aval (que l'on sélectionne ou non, identique).
**À faire** : vérifier si la sélection est censée se propager (pré-remplir le cylindre dans devis/optim) → bug de câblage, ou si c'est **informatif par design** → alors clarifier l'intention ou retirer.
**Observations liées** : les coûts affichent **0,00 € HT** dans la liste (calcul non fait dans cette vue ?) ; la machine proposée est une **ligne de finition** (Daco) là où on attend une presse.

### Intervalle laize — accessibilité
« Forcer intervalle laize » est enterré dans « Contraintes & bobine » → oublié à chaque fois.
**À faire** : le rendre **visible et éditable inline**, modifiable à tout moment. Fix UX léger, distinct du redesign flux (#6).

### Transverse — filtrage des machines par rôle
La ligne de finition (Daco) apparaît dans des sélecteurs de **presse / cylindre** (#4). Filtrer les machines proposées selon leur **rôle** (presse d'impression vs finition vs rebobineuse) dans chaque sélecteur.

---

## Ordre proposé
1. **Unify** `Machine ↔ MachineImprimerie` (en cours).
2. UX/câblage (#2, #3, #4, intervalle laize, filtrage rôle) — au fil de l'eau, hors SACRED.
3. **Sprint calage** (#5) — dédié, benchmark + validation.
4. **Sprint flux matière↔bobinage** (#6) — cadrage design d'abord, puis code.
