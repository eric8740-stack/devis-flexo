# Backlog bugs — relevés session 2026-06-02

Contexte : revue manuelle de l'app (compte démo `entreprise_id=1`). 6 points relevés.
Chaque point = **audit read-only d'abord** (quel fichier, qu'est-ce qui est câblé), puis fix.

## Principe de séquencement
- Ne pas empiler deux changements SACRED en même temps.
- ~~Sprint unify `Machine ↔ MachineImprimerie` (P1+P2) → le finir avant les bugs moteur.~~ ✅ **FAIT** post-merges #86 + #87 (02/06).
- Bugs moteur (#5, #6) = **sprints dédiés**, après unify, sous benchmark + validation.
- Bugs UX/câblage (#2, #3, #4, intervalle laize, filtrage machines) = **légers, hors SACRED**, faisables indépendamment / en parallèle.

---

## ✅ RÉSOLU — Bug post-unify P1+P2 (clos par #88, 03/06)

### 0. Les 3 presses migrées (Mark Andy 2200 / OMET / Nilpeter) ne ressortaient PAS comme candidates dans l'optim — **RÉSOLU (#88)**
**Observé** post-merge #86 + #87 sur compte démo (`entreprise_id=1`) : les 6 machines en BDD étaient bien `actif=true`, mais l'étape « Candidats viables » n'affichait que **P5 et Atelier 2** ; les 3 presses migrées (Mark Andy 2200, OMET XFlex 330, Nilpeter FA-22) ne généraient aucune **ligne** candidate visible.

**✅ Résolution** : PR #88 (`feat(optim): afficher machines équivalentes sur lignes candidates`, mergée 03/06, head `cdde171`). Fix **UI pur, zéro modif moteur** (option (b) ci-dessous).

**Les 2 pistes initiales étaient erronées — INFIRMÉES :**
1. ~~Champs **NULL** défautés par la migration `b2c3d4e5f6g7` (`duree_calage_h` / `largeur_max_mm` / `vitesse_max_m_min` NULL → filtre dur silencieux type `IS NOT NULL`)~~ → **INFIRMÉ** : les 3 presses migrées ont des **valeurs saines**, aucune n'est écartée par un filtre sur champ NULL.
2. ~~**Appariement cylindre ↔ machine** (colonnes `CylindreMagnetique.nb_pc_2200 / nb_pc_p5 / …` → OMET & Nilpeter sans colonne dédiée → 0 cylindre compatible)~~ → **INFIRMÉ** : le moteur **n'apparie pas** par ces colonnes ; les colonnes `nb_pc_*` ne participent **pas** à la génération de candidats → piste sans objet.

**🎯 Vraie cause — dédoublonnage moteur** (`_dedoublonner_configs`, héritage PR #9.1) : le moteur **fusionne** les configs qui ne diffèrent que par la machine. Deux presses de **même laize utile** produisent une **clé de config identique** (même cylindre, mêmes poses dev/laize, mêmes intervalles) → elles sont **fusionnées en une seule ligne**, la machine au meilleur score représentant les autres (agrégées dans `machines_compatibles`). Les presses « manquantes » n'étaient donc **pas exclues** : elles étaient **masquées derrière une ligne équivalente**.

**Fix livré (#88, option b)** : exposer les machines équivalentes **côté UI** sur chaque ligne candidate (lecture du `machines_compatibles` déjà produit par le moteur) — **aucune modification du moteur ni de son scoring**. L'option (a) écartée (ajouter `nb_pc_omet`/`nb_pc_nilpeter` ou refondre l'appariement en M:N) était inutile, la piste appariement étant infirmée.

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

### 6. Flux matière ↔ bobinage incohérent — Ø calculé sur défauts (épaisseur matière + paroi mandrin) — **CADRÉ**
**Observé** : le Ø bobine ne coïncide pas avec le vrai papier. Deux causes de « valeur de départ fausse » fournie au calcul du Ø :
- **Épaisseur matière** : le Ø lit `candidat.epaisseur_appliquee_um` **figé à la saisie** (étape 1), pas la matière choisie à l'étape **Matière** (`detail`, par lot, dont l'épaisseur est affichée mais jamais propagée). Fallback **150 µm** injecté à 3 endroits (front saisie `useState("150")`, schéma `epaisseur_matiere_um=Field(150.0)`, rebobinage `?? 150`). `matiere.epaisseur_microns` est **NULLABLE** → NULL traité en 150.
- **Paroi mandrin** : le Ø de départ de l'enroulement = `mandrin_mm` **brut** (Ø intérieur nominal), sans paroi → léger sous-estimé. Aucun champ d'épaisseur de paroi n'existe nulle part.

**Principe directeur (3 facettes, MÊME nature)** : fournir la **bonne valeur de départ** au calcul du Ø. **ZÉRO formule SACRED touchée** — `bat_calculs` (`calcul_diametre_bobine` + inverses) et `calcul_bobines` prennent épaisseur et Ø mandrin en **paramètres** ; on ne change que ce qu'on leur passe.

**Décisions tranchées :**
1. **Épaisseur matière** — source = l'étape **Matière (PAR LOT)**, plus la saisie. Matière à `epaisseur_microns` **NULL → saisie opérateur** (champ éditable à l'étape Bobinage). **150 µm = ultime fallback seulement** (ni matière, ni saisie).
2. **Paroi mandrin** — nouveau champ **`epaisseur_paroi_mm` sur `parametre_mandrin`** (par Ø mandrin), **pré-rempli + override** à l'étape Bobinage. **Ø de départ = Ø intérieur + 2×paroi**, **pré-composé en amont** et passé à `bat_calculs` (formule **intacte**). `epaisseur_paroi_mm` **NULL → comportement actuel** (Ø brut, pas de correction).
3. **Cohérence** — la **vérité du Ø est finalisée à l'étape Bobinage** ; le Ø candidat (étape 2) devient une **estimation ré-alignée**. **Un seul point de calcul** du Ø → pas de divergence d'affichage entre étape 2 et étape Bobinage.

**Granularité** : **1 Ø PAR LOT**. Le rebobinage actuel ne lit que `selection[0]` (mono-lot) → **à étendre** au multi-lots.

**SACRED** : `bat_calculs` / `rotation_se` **non modifiés**. Re-valider les **fixtures Ø** (242 mm `CoherenceBobineAlerte`, benchmarks) **uniquement si** la valeur effective de départ change.

**Plan en lots** :
- **6.1** — champ `epaisseur_paroi_mm` sur `parametre_mandrin` (migration + modèle + expo). *(en cours)*
- **6.2** — propagation matière + paroi → **Ø par lot** + cohérence (front + orchestration), **après** validation du cadrage et **merge de 6.1**.

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
