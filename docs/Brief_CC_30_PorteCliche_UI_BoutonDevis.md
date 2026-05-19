# Brief CC #30 — Refonte PorteCliche + UI + fix bouton créer devis

> Sprint 13 avenant · correctif métier PR #29 + amélioration UI + fix workflow critique · ~13h · 1 PR

**Repo** : `devis-flexo` (cwd local)
**Branche** : `fix/porte-cliche-metier-plus-ui-couleurs` depuis `main = 6eba3b5`
**Référence** : Brief #29 mergé (modèle PorteCliche basé sleeves modernes — **interprétation métier incorrecte**)

---

## 1. Contexte — pourquoi cette PR

Trois corrections en 1 PR :

1. **Erreur métier majeure** sur le modèle `PorteCliche` livré en PR #29 :
   - Modèle livré : sleeves modernes avec marque/modèle commercial (Rotec/DuPont Cyrel Fast/Flint), matière (polyuréthane/carbone), laize utile en mm, mandrin
   - **Réalité métier flexo étroite** : un porte-cliché est un cylindre métallique avec engrenage **dent par dent identique** au cylindre magnétique. On y colle adhésif + cliché polymère. Synchronisation mécanique par engrenage
   - Cardinalité : N porte-clichés par (machine × cyl mag), où N = **nombre de couleurs de la machine** (machine 8 couleurs = 8 PC montés, machine 4 couleurs = 4 PC)
   - Les 3 seeds compte demo (PC-220 Rotec, PC-330 DuPont, PC-410 Flint) sont **absurdes métier** à supprimer

2. **UI Mon parc trop austère** (PR #29 retour utilisateur) :
   - Pas assez de couleurs sur la page interne (gradient présent uniquement sur la card d'accès)
   - Boutons "Modifier"/"Désactiver" en texte gris bordé noir, pas engageants
   - Manque illustrations états vides
   - Cards pas assez visuelles
   - Pas faire peur = pas Excel

3. **Bug UX critique étape 3 optim** : le bouton "Valider et créer le devis" est manquant ou invisible. L'utilisateur arrive en étape 3, voit son visuel d'enroulement, voit un toast informatif "Devis multi-lots prêt à créer" en bas à droite, mais **ne sait pas où cliquer** pour finaliser. Workflow bloqué en bout de chaîne.

---

## 2. Périmètre — 7 livrables en 1 PR

| # | Livrable | Charge |
|---|---|---|
| 1 | Fix bouton "Créer le devis" étape 3 optim (PRIORITAIRE) | 1-2h |
| 2 | Vérif/ajout champ `Machine.nb_couleurs` + migration + seed | 1-2h |
| 3 | Refonte modèle `PorteCliche` (drop absurdes + nouveau schéma) | 2-3h |
| 4 | Refonte endpoints `/api/porte-cliches` (nouveau schemas Pydantic) | 2h |
| 5 | Refonte UI onglet "Mes porte-clichés" avec filtre machine | 2-3h |
| 6 | Amélioration UI globale Mon parc (couleurs, primary remplis, illustrations) | 2-3h |
| 7 | Tests (nouveau modèle PC + endpoint POST /api/devis multi-lots E2E) | 1-2h |
| **Total** | | **~13h** |

**Ordre d'exécution recommandé** : 1 → 2 → 3 → 4 → 5 → 6 → 7. Le fix #1 est prioritaire car bloquant pour l'usage en prod.

---

## 3. Fix #1 — Bouton "Créer le devis" étape 3 optim (PRIORITAIRE)

### Diagnostic à faire

```bash
grep -rn "Valider.*cr[ée]er" frontend/src/app/optimisation/
grep -rn "Cr[ée]er le devis" frontend/src/
grep -rn "POST.*devis" frontend/src/app/optimisation/
```

Vérifier :
- Le composant étape 3 (probablement `OptimisationPoseDetailLots.tsx` ou équivalent)
- Si bouton "Valider et créer le devis" est codé : est-il visible ? Bien placé ? Stylé en primary ?
- Si absent : l'ajouter

### Spec UI

```
┌──── ÉTAPE 3 ─ Détail lots ─────────────────────────────────────────┐
│ [ ← Retour aux candidats ]                                         │
│                                                                    │
│ LOT 1 ... (card existante)                                         │
│ LOT 2 ... (card existante)                                         │
│                                                                    │
│ ══════════════════════════════════════════════════════════════════ │
│ COÛT TOTAL DEVIS HT : 1 921,79 €                                   │
│                                                                    │
│         ┌──────────────────────────────────────────┐               │
│         │  ✓ Valider et créer le devis  (1921,79€) │  ← PRIMARY    │
│         └──────────────────────────────────────────┘               │
│                                                                    │
│ Le toast "Devis multi-lots prêt" en bas à droite reste informatif  │
└────────────────────────────────────────────────────────────────────┘
```

### Comportement

1. **Visible** : centré sous le récap coût, primary rempli (gradient bleu→ambre ou accent solide), taille `lg`, prominent
2. **Désactivé** tant que :
   - Au moins un lot n'a pas de matière sélectionnée
   - Σ quantités lots ≠ quantité totale
3. **Loading state** pendant POST : spinner inline, texte "Création en cours..."
4. **Success** : redirection vers `/devis/{id}` créé OU `/devis` liste avec toast confirmation
5. **Error** : toast erreur explicite, bouton reste actif pour retry

### Implémentation suggérée

```tsx
// frontend/.../OptimisationPoseDetailLots.tsx

const handleCreerDevis = async () => {
  setLoading(true);
  try {
    const response = await fetch('/api/devis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        quantite_totale,
        lots: lots.map(lot => ({ ... }))
      })
    });
    const devis = await response.json();
    router.push(`/devis/${devis.id}`);
  } catch (e) {
    toast.error("Erreur lors de la création du devis");
  } finally {
    setLoading(false);
  }
};

<Button
  size="lg"
  variant="primary"
  disabled={!tousMatieresOK || sommeQuantitesIncorrecte || loading}
  onClick={handleCreerDevis}
  className="bg-gradient-to-r from-[var(--accent)] to-[var(--gold)] text-white font-semibold px-8 py-4"
>
  {loading ? "Création en cours..." : `✓ Valider et créer le devis (${cout_total} €)`}
</Button>
```

---

## 4. Fix #2 — Champ `Machine.nb_couleurs`

### Vérif existant

```bash
grep -rn "nb_couleurs" backend/app/models/machine*.py
cat backend/app/models/machine.py | grep -A 30 "class Machine"
```

### Si absent : ajout + migration

```python
class Machine(Base):
    # ... champs existants
    nb_couleurs = Column(Integer, nullable=False, default=8, server_default="8")
```

Migration Alembic :

```python
op.add_column('machines',
    sa.Column('nb_couleurs', sa.Integer(), nullable=False, server_default='8')
)
# Seed compte demo : ajuster selon machines réelles
op.execute("""
    UPDATE machines SET nb_couleurs = 8 WHERE entreprise_id=1 AND nom IN ('Mark Andy 2200', 'OMET XFlex 330');
    UPDATE machines SET nb_couleurs = 6 WHERE entreprise_id=1 AND nom = 'Nilpeter FA-22';
""")
# Si tu as d'autres machines avec nb_couleurs différent, adapter
```

> **Vérification à faire par CC** : combien de machines en seed compte demo et leur nb_couleurs réel ? Si tu ne sais pas, demander en chat avant d'exécuter cette partie.

### Si déjà présent

Vérifier les valeurs actuelles et seed manquant. Migration data uniquement si besoin.

---

## 5. Fix #3 — Refonte modèle `PorteCliche`

### Nouveau schéma

```python
# backend/app/models/porte_cliche.py — REFONTE COMPLÈTE

class PorteCliche(Base):
    __tablename__ = "porte_cliches"

    id = Column(Integer, primary_key=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    cylindre_magnetique_id = Column(Integer, ForeignKey("cylindres.id"), nullable=False)

    quantite = Column(Integer, nullable=False)  # default applicatif = nb_couleurs(machine)
    actif = Column(Boolean, nullable=False, default=True, server_default="true")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entreprise = relationship("Entreprise")
    machine = relationship("Machine")
    cylindre_magnetique = relationship("Cylindre")

    __table_args__ = (
        UniqueConstraint("entreprise_id", "machine_id", "cylindre_magnetique_id",
                        name="uq_porte_cliche_entreprise_machine_cyl"),
        Index("ix_porte_cliches_entreprise", "entreprise_id"),
        CheckConstraint("quantite >= 0", name="ck_porte_cliche_quantite_positive"),
    )
```

### Champs supprimés (vs PR #29)

❌ `reference` · ❌ `marque` · ❌ `modele` · ❌ `laize_utile_mm` · ❌ `diametre_interieur_mm` · ❌ `matiere`

### Migration Alembic

```python
# alembic revision -m "refonte_porte_cliche_machine_cylindre"

# Up :
# 1. Drop des 3 seeds absurdes
op.execute("DELETE FROM porte_cliches WHERE entreprise_id=1 AND reference IN ('PC-220', 'PC-330', 'PC-410')")

# 2. Drop des colonnes obsolètes
op.drop_column('porte_cliches', 'reference')
op.drop_column('porte_cliches', 'marque')
op.drop_column('porte_cliches', 'modele')
op.drop_column('porte_cliches', 'laize_utile_mm')
op.drop_column('porte_cliches', 'diametre_interieur_mm')
op.drop_column('porte_cliches', 'matiere')

# 3. Add new columns
op.add_column('porte_cliches', sa.Column('machine_id', sa.Integer(),
              sa.ForeignKey('machines.id'), nullable=False))
op.add_column('porte_cliches', sa.Column('cylindre_magnetique_id', sa.Integer(),
              sa.ForeignKey('cylindres.id'), nullable=False))
op.add_column('porte_cliches', sa.Column('quantite', sa.Integer(), nullable=False))

# 4. Unique constraint
op.create_unique_constraint('uq_porte_cliche_entreprise_machine_cyl',
    'porte_cliches', ['entreprise_id', 'machine_id', 'cylindre_magnetique_id'])

# 5. Seed compte demo (entreprise_id=1) : 21 cyl × N machines avec quantite = nb_couleurs
op.execute("""
    INSERT INTO porte_cliches (entreprise_id, machine_id, cylindre_magnetique_id, quantite, actif, created_at, updated_at)
    SELECT
        1,
        m.id,
        c.id,
        m.nb_couleurs,
        true,
        NOW(),
        NOW()
    FROM cylindres c
    CROSS JOIN machines m
    WHERE c.entreprise_id = 1
      AND c.actif = true
      AND m.entreprise_id = 1
    ON CONFLICT (entreprise_id, machine_id, cylindre_magnetique_id) DO NOTHING
""")

# Down : reverse
# (laisser un down compatible mais sans restaurer les anciens seeds)
```

> ⚠️ **Migration multi-dialect** : utiliser `op.get_bind().dialect.name` pour adapter syntaxe Postgres/SQLite (CROSS JOIN, ON CONFLICT). Pattern existant dans le projet.

---

## 6. Fix #4 — Endpoints REST `/api/porte-cliches`

### Schemas Pydantic refondus

```python
class PorteClicheCreate(BaseModel):
    machine_id: int
    cylindre_magnetique_id: int
    quantite: Optional[int] = None  # si None, default = machine.nb_couleurs
    notes: Optional[str] = None

class PorteClicheUpdate(BaseModel):
    quantite: Optional[int] = None
    actif: Optional[bool] = None
    notes: Optional[str] = None

class PorteClicheOut(BaseModel):
    id: int
    machine_id: int
    machine_nom: str  # joined pour UI
    machine_nb_couleurs: int  # joined pour info
    cylindre_magnetique_id: int
    cylindre_nb_dents: int  # joined pour UI
    quantite: int
    actif: bool
    notes: Optional[str]
```

### Validation create

- `quantite` >= 0
- Si `quantite` non fourni → utiliser `machine.nb_couleurs`
- Vérifier `machine_id` et `cylindre_magnetique_id` appartiennent à la même `entreprise_id` que l'user

### Routes

Conservées : GET liste, POST, GET id, PATCH, DELETE (soft), POST toggle-actif.
Filtres GET liste : `?machine_id=X`, `?actif=true|false` (default true).

---

## 7. Fix #5 — UI onglet "Mes porte-clichés"

### Wireframe

```
┌────────────────────────────────────────────────────────────────────┐
│ 📐 Mes porte-clichés                              [+ Ajouter]      │
│ Cylindres synchronisés avec tes magnétiques                        │
│                                                                    │
│ Filtre : [Mark Andy 2200 (8 couleurs) ▼]   [☐ Voir désactivés]    │
│                                                                    │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ 🔧 96 dents                                       [●━━━]       │ │
│ │ 8 porte-clichés disponibles · synchro avec cyl mag 96 dents    │ │
│ │                                          [Modifier qté]  [⋯]   │ │
│ └────────────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ 🔧 104 dents                                      [●━━━]       │ │
│ │ 8 porte-clichés disponibles                                    │ │
│ │                                          [Modifier qté]  [⋯]   │ │
│ └────────────────────────────────────────────────────────────────┘ │
│ ...                                                                │
└────────────────────────────────────────────────────────────────────┘
```

### Comportement

- **Dropdown machine** en haut filtre la liste. Affiche le nb_couleurs de la machine sélectionnée. Default = première machine actif
- **Suppression** des champs/recherche "référence, marque, matière" (n'ont plus de sens)
- **Cards** : nb_dents en gros (titre), quantité en sous-titre, toggle actif coloré à droite
- **Bouton "Modifier qté"** : dialog avec input number + notes optionnelles, save inline
- **Menu `[⋯]`** : Désactiver/Réactiver, voir devis liés (futur)
- **État vide** par machine : illustration + "Pas encore de porte-cliché pour cette machine. Ajoutes-en un en 30 secondes" + CTA
- **Bouton "+ Ajouter"** : dialog avec dropdown machine + dropdown cyl mag + qté (default = nb_couleurs machine)

---

## 8. Fix #6 — Amélioration UI globale Mon parc

### Principes design renforcés

| Élément | Avant (PR #29) | Cible (PR #30) |
|---|---|---|
| Boutons "Modifier"/"Désactiver" | Gris bordé noir | **Primary rempli coloré** (Modifier = bleu accent / Désactiver = rouge doux) |
| Cards cylindres | Fond blanc plat | **Légère ombre douce + hover lift + accent border-left coloré** |
| Toggle actif | Vert/gris discret | **Toggle plus contrasté avec animation transition fluide** |
| États vides | Texte simple | **Illustration SVG + microcopie + CTA gros bouton coloré** |
| Header de page | "Mon parc" texte | **Titre + sous-titre + petit éclat coloré accent** |
| Onglets tabs | Sobre | **Tab actif avec underline coloré gradient** |
| Compteur "21 cyl actifs · 3 désactivés" | Petit texte gris | **Badge coloré pill** |
| Champ recherche | Bord gris fin | **Border accent au focus + icône colorée** |

### Palette à appliquer

```css
/* Réutilise les variables existantes */
--bg: #fef8ea          /* fond chaleureux */
--accent: #1a52a3      /* bleu profond */
--gold: #c79a3a        /* or */
--green: #2d7a4f       /* vert actif */
--red-soft: #f5d8d8    /* rouge doux désactiver */
--ink: #1a2238         /* texte */

/* Gradients */
bg-gradient-to-r from-[var(--accent)] to-[var(--gold)]  /* boutons primary */
bg-gradient-to-br from-[var(--bg)] to-white             /* fond cards */
```

### Microcopie

- "Tes cylindres" pas "Liste des cylindres"
- "Ajoute un cylindre" pas "Créer"
- "Désactiver" pas "Supprimer"
- "Bien joué, tu as configuré X cylindres" en footer si plus de 10 actifs (engagement)

### Illustrations états vides

SVG simples cohérents avec le ton (engrenage stylisé, atelier flexo). Pas d'illustrations 3D commerciales. Style line-art avec accent coloré.

---

## 9. Fix #7 — Tests

Baseline cible : **731 + 10 nouveaux = 741 passed**

```python
# backend/tests/

test_porte_cliche_refonte.py
  - test_modele_nouveau_schema (machine_id + cyl_id + quantite)
  - test_unique_constraint_entreprise_machine_cyl
  - test_seed_compte_demo_genere_21_x_N_lignes
  - test_quantite_default_egale_nb_couleurs_machine
  - test_validation_meme_entreprise

test_machine_nb_couleurs.py
  - test_champ_nb_couleurs_existe
  - test_seed_machines_avec_nb_couleurs

test_porte_cliche_api_refonte.py
  - test_crud_nouveau_schema
  - test_filter_par_machine_id

test_creer_devis_multi_lots_e2e.py
  - test_post_devis_avec_2_lots_renvoie_201_et_id
  - test_redirect_vers_detail_devis_apres_creation
```

---

## 10. Plan commits (8 commits cohérents)

```bash
git checkout main && git pull
git checkout -b fix/porte-cliche-metier-plus-ui-couleurs

# Commit 1 — Fix bouton Créer le devis (PRIORITAIRE)
fix(optim/ui): bouton primary "Valider et créer le devis" étape 3 + redirect après création

# Commit 2 — Machine.nb_couleurs
feat(machine): champ nb_couleurs + migration + seed compte demo

# Commit 3 — Refonte modèle PorteCliche
feat(porte-cliche): refonte modèle métier (machine_id + cyl_id + quantite) + migration drop seeds absurdes + reseed 21*N

# Commit 4 — Endpoints REST refondus
feat(porte-cliches/api): nouveau schemas Pydantic + validation + filter par machine

# Commit 5 — UI onglet PC refondue
feat(parametres/ui): onglet porte-clichés avec filtre machine + cards simplifiées

# Commit 6 — Amélioration UI globale Mon parc
feat(parametres/ui): couleurs accent partout, primary remplis, illustrations états vides, gradients

# Commit 7 — Tests
test(parc): 10 nouveaux tests refonte PC + nb_couleurs + creation devis E2E

# Commit 8 (optionnel) — Doc brief dans docs/
docs: ajout brief #30 refonte PC + UI + fix créer devis

# Pas de Co-Authored-By
# pytest vert à chaque commit
# Pas de push avant validation chat
```

---

## 11. SACRED Invariants — INTOUCHABLES

- ❌ Logique `cost_engine` (V1a/V1b/V7a/V8a-e préservés)
- ❌ Composant `SchemaImplantation` (Vue A/B/C)
- ❌ Mapping rotation `rotation_se.py`
- ❌ Modèle `Cylindre` (juste lecture via FK)
- ❌ Endpoints `/api/cylindres` (déjà OK depuis #29)
- ❌ Auth JWT + multi-tenant strict (`get_or_404_scoped`)
- ❌ Compte `entreprise_id=1` cyl actifs (21) — uniquement les PR #29 seeds porte-clichés (PC-220, PC-330, PC-410) sont supprimés car absurdes

---

## 12. Hors-scope explicite

- ❌ Liaison directe PorteCliche → Cylindre dans le moteur d'optim (juste référentiel pour l'instant)
- ❌ Track usure individuelle des PC (modèle Option B = type + quantité, pas instance)
- ❌ Génération PDF devis (Sprint 17)
- ❌ Refonte du workflow 3 étapes (déjà OK depuis #28)
- ❌ Refonte écran liste devis (futur)
- ❌ Permissions granulaires sur le parc
- ❌ Modification de toute autre page que `/parametres/mon-parc` et `/optimisation/etape3`

---

## 13. Antipatterns à éviter

- ❌ Garder les anciens champs (reference, marque, modele, laize_utile_mm, diametre_interieur_mm, matiere) "au cas où"
- ❌ Garder les 3 seeds absurdes PC-220/PC-330/PC-410
- ❌ Bouton "Créer le devis" en variant secondary ou texte gris terne
- ❌ Redirection après création vers une page random — soit `/devis/{id}` soit liste
- ❌ Suppression dure des PR #29 PC (soft delete via DELETE, mais migration peut clean ces 3 seeds spécifiques par DELETE SQL)
- ❌ Oublier la migration multi-dialect (Postgres + SQLite tests)
- ❌ Refactor "bonus" hors scope
- ❌ Co-Authored-By dans un commit

---

## 14. Critères d'acceptation

1. **Bouton "Valider et créer le devis"** visible, primary rempli, prominent en étape 3
2. POST /api/devis multi-lots fonctionne + redirection après création
3. Modèle `PorteCliche` refondu : machine_id + cylindre_magnetique_id + quantite (PAS de marque/matière/laize_utile)
4. Migration Alembic réversible appliquée
5. 3 seeds absurdes PC-220/PC-330/PC-410 supprimés en compte demo
6. Compte demo seedé avec 21 cyl × N machines actives PC (default qté = nb_couleurs machine)
7. `Machine.nb_couleurs` existe et seedé en compte demo
8. UI onglet PC : filtre machine fonctionnel, cards simplifiées, microcopie tutoyée
9. UI Mon parc globalement plus colorée : primary remplis, gradients, illustrations états vides, hover effects
10. pytest 741+ passed, 0 failed
11. TypeScript `tsc` clean
12. Vercel deploy preview review OK
13. SACRED tous préservés (cost_engine, rotation_se, SchemaImplantation, multi-tenant strict)
14. Pas de mention nominative dans tout le code/commits/docs

---

## 15. Démarrage

```bash
cd ~/projets/devis-flexo
git checkout main && git pull
git checkout -b fix/porte-cliche-metier-plus-ui-couleurs

# Copier ce brief dans docs/
cp ~/Downloads/Brief_CC_30_PorteCliche_UI_BoutonDevis.md docs/
git add docs/Brief_CC_30_PorteCliche_UI_BoutonDevis.md
git commit -m "docs: ajout brief #30 refonte PC + UI + fix bouton créer devis"

# Démarrer par commit 1 (fix bouton créer devis — PRIORITAIRE car bloquant prod)
# Puis 2 → 7 dans l'ordre
# pytest vert à chaque commit
# Pas de push avant validation du responsable produit
```

---

**Brief #30 — ~13h dev solo · 8 commits · 1 PR · 3 corrections (métier + UI + workflow) · SACRED préservés**
