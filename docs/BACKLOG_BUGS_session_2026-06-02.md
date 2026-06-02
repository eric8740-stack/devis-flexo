# Backlog bugs — relevés session 2026-06-02

Contexte : revue manuelle de l'app (compte démo `entreprise_id=1`). 6 points relevés.
Chaque point = **audit read-only d'abord** (quel fichier, qu'est-ce qui est câblé), puis fix.

## Principe de séquencement
- Ne pas empiler deux changements SACRED en même temps.
- Sprint unify `Machine ↔ MachineImprimerie` (P1+P2) **en cours** → le finir avant les bugs moteur.
- Bugs moteur (#5, #6) = **sprints dédiés**, après unify, sous benchmark + validation.
- Bugs UX/câblage (#2, #3, #4, intervalle laize, filtrage machines) = **légers, hors SACRED**, faisables indépendamment / en parallèle.

---

## Déjà traité

### 1. Rebobineuse / suppression de machines — SÉCURISÉ
L'onglet Rebobinage sélectionne une « rebobineuse du parc » (« Daco D-Series »).
La migration unify supprimait Daco/Atelier → risque de casser le rebobinage.
→ Correction donnée : la migration unify **ne supprime plus aucune fiche `Machine`** (P5/Daco/Atelier conservés). Elle se limite à : ajouter les 3 presses + remapper `lot_production`/`porte_cliche` + DROP `machine_imprimerie` + `configuration_pose`.
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
