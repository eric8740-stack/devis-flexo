# Brief CC #32 — Liaison optim → cost_engine + page détail multi-lots + workflow modifier

> Sprint 13 avenant · architecture hybride C · ~12-15h · 1 PR

**Repo** : `devis-flexo` (cwd local)
**Branche** : `feat/devis-multilots-chiffrage-auto-et-modifier` depuis `main = <SHA-après-merge-patch-31>`
**Référence** : Patch #31 mergé (bouton "Valider et créer le devis" + redirect liste workaround)

---

## 1. Contexte — trou architectural identifié

Le workflow actuel multi-lots crée un devis à **0,00 € HT** car :

- `/optimisation` → POST `/api/devis` crée juste la **coquille** du devis (lots, matières, configs)
- Le `cost_engine` (V1a/V1b/V7a/V8a-e) **n'est JAMAIS appelé** à la création depuis l'optim
- `/calculer-un-devis` est l'ancien workflow mono-config qui chiffre vraiment via cost_engine
- Les 2 workflows sont **déconnectés**

**Architecture cible (Option C hybride)** :
1. POST optim → **calcul automatique** cost_engine_aggregator par lot → devis sort déjà chiffré
2. Page `/devis/[id]` affiche cards par lot + récap agrégé
3. Bouton "Modifier ce devis" → redirige vers `/calculer-un-devis?devis_id=X` pour ajuster marge/réduction/frais commerciaux
4. PATCH `/api/devis/{id}` persiste les ajustements

---

## 2. Périmètre — 7 livrables en 1 PR

| # | Livrable | Charge |
|---|---|---|
| 1 | Backend : appel cost_engine_aggregator au POST /api/devis depuis optim | 2-3h |
| 2 | Composant `DevisResultMultiLots.tsx` + détection mode dans /devis/[id] | 4-5h |
| 3 | Bouton "Modifier ce devis" sur page détail → redirect /calculer-un-devis?devis_id=X | 30min |
| 4 | Pré-chargement /calculer-un-devis depuis devis_id (lots, matières, configs) | 2-3h |
| 5 | Vérif/ajout champ réduction commerciale (%) si manquant + PATCH /api/devis/{id} | 1-2h |
| 6 | Retirer workaround patch #31 → redirect vers /devis/{id} qui marche maintenant | 30min |
| 7 | Tests E2E + non-régression | 1-2h |
| **Total** | | **~12-15h** |

---

## 3. Fix #1 — Backend : cost_engine_aggregator au POST /api/devis

### Logique actuelle (à modifier)

Le endpoint `POST /api/devis` accepte un payload multi-lots `{quantite_totale, lots: [...]}` et crée le devis avec ses LotProduction sans appeler le cost_engine.

### Logique cible

```python
# backend/app/api/devis.py (ou équivalent)

@router.post("/devis", response_model=DevisOut)
def creer_devis(payload: DevisCreate, db, user):
    # 1. Créer le devis + lots (comme aujourd'hui)
    devis = Devis(entreprise_id=user.entreprise_id, ...)
    lots = [LotProduction(devis=devis, ...) for lot_payload in payload.lots]
    db.add(devis)
    db.flush()  # pour avoir les IDs
    
    # 2. NEW : appel cost_engine_aggregator pour calculer le prix
    cout_agrege = cost_engine_aggregator.calculer_devis_multilots(lots)
    
    # 3. Stocker le résultat
    devis.payload_output = {
        "mode": "multi-lots",
        "prix_vente_ht_eur": float(cout_agrege.cout_total_ht),
        "details_par_lot": [
            {
                "lot_id": cl.lot_id,
                "cout_ht": cl.cout_ht,
                "details": cl.details,  # V1a/V1b/V7a/V8a-e per lot
            }
            for cl in cout_agrege.details_par_lot
        ],
        "note": "Devis créé depuis optimisation multi-lots, chiffrage automatique",
    }
    
    # 4. Persister cout_lot_ht sur chaque LotProduction (déjà champ existant)
    for lot, cl in zip(lots, cout_agrege.details_par_lot):
        lot.cout_lot_ht = cl.cout_ht
    
    db.commit()
    return devis
```

### Sacred preserved

- ✅ `cost_engine` logique : aucune modification (appelé tel quel via aggregator)
- ✅ Valeurs EXACT V1a/V1b/V7a/V8a-e préservées par lot
- ✅ Multi-tenant strict
- ✅ Aggregator déjà créé en PR #25 (réutilisation)

### Tests

```python
def test_post_devis_optim_calcule_prix_aggregate():
    """POST /api/devis depuis optim → devis sort avec prix_vente_ht_eur != 0"""
    payload = {
        "quantite_totale": 10000,
        "lots": [
            {"cylindre_id": X, "machine_id": Y, "nb_poses_dev": 3, "nb_poses_laize": 4,
             "sens_enroulement": 1, "quantite": 10000, "matiere_id": Z}
        ]
    }
    response = client.post("/api/devis", json=payload, headers=auth)
    assert response.status_code == 201
    devis = response.json()
    assert devis["payload_output"]["prix_vente_ht_eur"] > 0
    assert devis["payload_output"]["mode"] == "multi-lots"
    assert len(devis["payload_output"]["details_par_lot"]) == 1
```

---

## 4. Fix #2 — Page /devis/[id] mode multi-lots

### Détection mode

```tsx
// frontend/src/app/devis/[id]/page.tsx

const isMultiLots = data?.payload_output?.mode === "multi-lots"
  || (data?.lots && data.lots.length > 0);

return isMultiLots
  ? <DevisResultMultiLots devis={data} />
  : <DevisResult data={data} />;  // legacy mono-lot intact
```

### Nouveau composant `DevisResultMultiLots.tsx`

Layout :

```
┌─────────────────────────────────────────────────────────────┐
│ Devis DEV-2026-0004 · Brouillon · 19/05/2026                │
│ [Modifier ce devis]  [Imprimer]  [Dupliquer]                │
│                                                             │
│ ═══════════════════════════════════════════════════════════ │
│                                                             │
│ ┌─ LOT 1 ────────────────────────────────────────────────┐ │
│ │ Cyl 104 dents (Z=330.2 mm) · Mark Andy P5              │ │
│ │ 3×4=12 poses · Sens 1 · 10 000 étiquettes              │ │
│ │ Matière : PP couché 80g/m²                             │ │
│ │ [SchemaImplantation Vue A/B/C SACRED réutilisé]        │ │
│ │ Coût lot HT : 1 234,56 €                               │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                             │
│ ═══════════════════════════════════════════════════════════ │
│                                                             │
│ COÛT TOTAL HT : 1 234,56 €                                  │
│ Quantité totale : 10 000 étiquettes                         │
│                                                             │
│ [Modifier ce devis →]                                       │
└─────────────────────────────────────────────────────────────┘
```

### Composants à créer

```tsx
// frontend/src/components/devis/DevisResultMultiLots.tsx — NEW
export function DevisResultMultiLots({ devis }: { devis: DevisOut }) {
  const router = useRouter();
  
  return (
    <div className="space-y-6">
      <DevisHeader devis={devis} />
      
      {devis.lots.map((lot, idx) => (
        <LotCard key={lot.id} lot={lot} index={idx + 1} />
      ))}
      
      <CoutTotalCard devis={devis} />
      
      <div className="flex gap-4">
        <Button
          size="lg"
          variant="primary"
          onClick={() => router.push(`/calculer-un-devis?devis_id=${devis.id}`)}
          className="bg-gradient-to-r from-[var(--accent)] to-[var(--gold)] text-white"
        >
          ✎ Modifier ce devis
        </Button>
      </div>
    </div>
  );
}
```

### Composant `LotCard`

```tsx
function LotCard({ lot, index }: { lot: LotProductionOut, index: number }) {
  return (
    <Card>
      <CardHeader>Lot {index}</CardHeader>
      <CardContent>
        <div>Cyl {lot.cylindre_nb_dents} dents · {lot.machine_nom}</div>
        <div>{lot.nb_poses_dev}×{lot.nb_poses_laize}={lot.nb_poses_dev*lot.nb_poses_laize} poses</div>
        <div>Sens {lot.sens_enroulement} · {lot.quantite} étiquettes</div>
        <div>Matière : {lot.matiere_nom}</div>
        
        <SchemaImplantation
          {...lot.visuel_data}  // réutilisation 1:1 du composant SACRED
        />
        
        <div className="text-lg font-bold text-[var(--accent)]">
          Coût lot HT : {lot.cout_lot_ht.toFixed(2)} €
        </div>
      </CardContent>
    </Card>
  );
}
```

### Sacred preserved

- ✅ Composant `SchemaImplantation` (Vue A/B/C) réutilisé tel quel
- ✅ `DevisResult` legacy intact pour devis mono-lot existants

---

## 5. Fix #3 — Bouton "Modifier ce devis" → redirect /calculer-un-devis

Click sur "Modifier ce devis" depuis la page détail → navigation vers `/calculer-un-devis?devis_id=X` qui pré-charge.

---

## 6. Fix #4 — Pré-chargement /calculer-un-devis depuis devis_id

### Logique

```tsx
// frontend/src/app/calculer-un-devis/page.tsx

export default function CalculerUnDevisPage() {
  const searchParams = useSearchParams();
  const devisId = searchParams.get("devis_id");
  
  const [devis, setDevis] = useState<DevisOut | null>(null);
  
  useEffect(() => {
    if (devisId) {
      fetch(`/api/devis/${devisId}`)
        .then(r => r.json())
        .then(setDevis);
    }
  }, [devisId]);
  
  // Pré-remplir les champs depuis devis.lots si présent
  // Si devis.lots existe → mode édition multi-lots
  // Sinon → mode classique (nouveau devis vide)
  
  return <DevisCalculator devisExistant={devis} />;
}
```

### Champs pré-remplis depuis le devis existant

- Lots (cylindres, machines, poses, quantités, matières par lot)
- Quantité totale
- Format étiquette
- Toutes les options de fabrication
- Marge / réduction commerciale (si déjà set)

### Sauvegarde

PATCH `/api/devis/{id}` au lieu de POST. Recalcul cost_engine_aggregator si lots/options changent.

---

## 7. Fix #5 — Réduction commerciale + PATCH

### Vérif existant

```bash
grep -rn "reduction" backend/app/models/devis*.py
grep -rn "reduction_pct\|reduction_commerciale" backend/app/
```

### Si absent : ajout champ

```python
class Devis(Base):
    # ... champs existants
    reduction_pct = Column(Numeric(5, 2), nullable=True, default=0)
    # 0-100, applicable sur prix_vente_ht_eur final
```

Migration Alembic légère.

### Application

```python
def calculer_prix_final(prix_brut: float, reduction_pct: float) -> float:
    return prix_brut * (1 - reduction_pct / 100)
```

Affichage UI :
- `payload_output.prix_vente_ht_eur` = prix brut (sans réduction)
- `prix_apres_reduction` = prix brut × (1 - réduction%)
- Afficher les 2 dans le récap pour transparence

### Endpoint PATCH /api/devis/{id}

```python
@router.patch("/devis/{id}", response_model=DevisOut)
def modifier_devis(id: int, payload: DevisUpdate, db, user):
    devis = get_or_404_scoped(Devis, id, user.entreprise_id)
    
    # Update lots si changement
    if payload.lots is not None:
        # Re-calculer cost_engine_aggregator
        ...
    
    # Update réduction
    if payload.reduction_pct is not None:
        devis.reduction_pct = payload.reduction_pct
    
    db.commit()
    return devis
```

---

## 8. Fix #6 — Retirer workaround patch #31

Dans `OptimisationPoseDetailLots.tsx` (ou équivalent) :

```tsx
// AVANT (patch #31) :
const devis = await response.json();
router.push('/devis');  // workaround

// APRÈS :
const devis = await response.json();
router.push(`/devis/${devis.id}`);  // page détail multi-lots qui marche
```

---

## 9. Fix #7 — Tests E2E

Baseline cible : **737 + 6 nouveaux = 743 passed**

```python
# backend/tests/

test_creation_devis_calcule_prix_aggregate.py
  - test_post_devis_optim_prix_non_zero
  - test_prix_aggregate_egal_somme_cout_lots
  - test_valeurs_EXACT_V1a_V1b_preservees_par_lot

test_devis_modifier_avec_reduction.py
  - test_patch_devis_avec_reduction_pct
  - test_prix_apres_reduction_calcule
  - test_recalcul_cost_engine_si_lots_modifies

# frontend/tests/

test_page_devis_multi_lots_e2e (Playwright si infra existe)
  - test_navigate_devis_id_multi_lots_rend_cards_par_lot
  - test_bouton_modifier_redirect_calculer_un_devis_avec_param
```

---

## 9bis. Design joyeux — guidelines couleurs (NON NÉGOCIABLE)

L'UX cible reste **simple + colorée + joyeuse**, cohérente avec les briefs #29/#30. Le nouveau composant `DevisResultMultiLots` doit respecter ces patterns visuels :

### Palette à appliquer (CSS variables projet)

```css
--bg: #fef8ea          /* fond chaleureux beige crème */
--accent: #1a52a3      /* bleu profond — boutons primaires */
--gold: #c79a3a        /* or — accents premium */
--green: #2d7a4f       /* vert — état actif, succès */
--red-soft: #f5d8d8    /* rouge doux */
--ink: #1a2238         /* texte principal */

/* Gradients à réutiliser systématiquement */
bg-gradient-to-r from-[var(--accent)] to-[var(--gold)]  /* boutons primary, CTA */
bg-gradient-to-br from-[var(--bg)] to-white             /* fond cards et hero */
```

### Patterns design par composant

| Composant | Design joyeux |
|---|---|
| **Header devis** | Gradient subtle background + numéro DEV-XXXX en gros (font Fraunces) + badge statut coloré (brouillon = ambre, envoyé = bleu, accepté = vert) |
| **Cards par lot** | Border-left 4px accent coloré (varie par index : LOT 1 bleu, LOT 2 or, LOT 3 vert) + shadow douce + hover lift |
| **SchemaImplantation embed** | Sur fond crème (`--bg`) pour mise en valeur visuelle |
| **Coût lot HT** | Typo bold gros, couleur accent bleu, séparateur ornemental |
| **Récap total HT** | **Card hero gradient** bleu→or, font Fraunces gros, prominent (même style que la card "Mon parc") |
| **Bouton "Modifier ce devis"** | Primary rempli gradient bleu→or, taille `lg`, icône ✎ |
| **Bouton "Imprimer" / "Dupliquer"** | Secondary outlined coloré (pas gris terne) |
| **Champ réduction (%)** | Input avec border accent au focus + slider visuel coloré si possible |
| **État chargement** | Skeleton coloré accent, pas gris classique |
| **État erreur** | Toast rouge doux + emoji ⚠️ |
| **État succès création** | Toast vert + emoji ✅ + animation slide-in |

### Microcopie tutoyée

- "Ton devis" pas "Le devis"
- "Modifie ce devis" pas "Éditer"
- "Coût total HT" pas "Total"
- "Imprime" pas "Imprimer"

### Wireframe enrichi visuellement

```
╔═════════════════════════════════════════════════════════════╗
║ 📋 Devis DEV-2026-0004                       [⌐ Brouillon] ║  ← header gradient subtle
║ Créé le 19/05/2026 — Mark Andy P5                           ║
╚═════════════════════════════════════════════════════════════╝

┌──🔵 LOT 1 ──────────────────────────────────────────────────┐  ← border-left bleu
│ Cyl 104 dents · Mark Andy P5 · 3×4=12 poses                │
│ Sens 1 · 10 000 étiquettes · PP couché 80g/m²              │
│                                                             │
│       [SchemaImplantation — fond crème mis en valeur]      │
│                                                             │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━         │
│         Coût lot HT  · 1 234,56 €  (bleu accent gros)      │
└─────────────────────────────────────────────────────────────┘

┌──🟡 LOT 2 ──────────────────────────────────────────────────┐  ← border-left or
│ ...                                                         │
└─────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════╗
║                                                            ║  ← card hero gradient bleu→or
║       💰 COÛT TOTAL HT                                     ║
║          1 921,79 €                                        ║  ← Fraunces XL bold
║          (10 000 étiquettes · 2 lots)                      ║
║                                                            ║
║   ┌────────────────────────────────────────────┐           ║
║   │  ✎ Modifie ton devis                       │           ║  ← gradient bleu→or
║   └────────────────────────────────────────────┘           ║
║                                                            ║
║   [🖨️ Imprime]  [📑 Duplique]                              ║
╚════════════════════════════════════════════════════════════╝
```

### Antipatterns visuels à éviter

- ❌ Fond blanc plat sur toute la page (Excel-like)
- ❌ Texte gris terne pour les valeurs importantes
- ❌ Boutons bordés sans remplissage (gris austère)
- ❌ Statut "Brouillon" en pill grise (utiliser ambre/or)
- ❌ Total HT en petit texte courant — doit être **prominent**, hero
- ❌ Card de lot sans démarcation visuelle (border-left coloré indispensable)
- ❌ Microcopie froide style "Liste · Détails · Modifier"

---

```bash
git checkout main && git pull
git checkout -b feat/devis-multilots-chiffrage-auto-et-modifier

# Commit 1 — Backend cost_engine au POST
feat(devis/api): appel cost_engine_aggregator au POST /api/devis multi-lots (devis chiffré automatiquement)

# Commit 2 — Champ réduction + PATCH endpoint
feat(devis): champ reduction_pct + endpoint PATCH /api/devis/{id} avec recalcul cost_engine

# Commit 3 — Composant DevisResultMultiLots
feat(devis/ui): nouveau composant DevisResultMultiLots avec cards par lot + SchemaImplantation SACRED réutilisé

# Commit 4 — Détection mode /devis/[id]
feat(devis/ui): détection mode multi-lots vs legacy dans page /devis/[id]

# Commit 5 — Pré-chargement /calculer-un-devis
feat(calculer-un-devis): pré-chargement depuis ?devis_id=X (lots, matières, options, réduction)

# Commit 6 — Retrait workaround patch #31
fix(optim/ui): redirect vers /devis/{id} après création (page détail multi-lots opérationnelle)

# Commit 7 — Tests
test(devis): 6 nouveaux tests E2E création chiffrée + modifier + réduction + non-régression

# Pas de Co-Authored-By
# pytest vert à chaque commit
# Pas de push avant validation chat
```

---

---

## 10. Plan commits (7 commits cohérents)

```bash
git checkout main && git pull
git checkout -b feat/devis-multilots-chiffrage-auto-et-modifier

# Commit 1 — Backend cost_engine au POST
feat(devis/api): appel cost_engine_aggregator au POST /api/devis multi-lots (devis chiffré automatiquement)

# Commit 2 — Champ réduction + PATCH endpoint
feat(devis): champ reduction_pct + endpoint PATCH /api/devis/{id} avec recalcul cost_engine

# Commit 3 — Composant DevisResultMultiLots avec design joyeux
feat(devis/ui): nouveau composant DevisResultMultiLots avec cards colorées par lot (border-left accent) + récap hero gradient bleu→or + SchemaImplantation SACRED réutilisé

# Commit 4 — Détection mode /devis/[id]
feat(devis/ui): détection mode multi-lots vs legacy dans page /devis/[id]

# Commit 5 — Pré-chargement /calculer-un-devis
feat(calculer-un-devis): pré-chargement depuis ?devis_id=X (lots, matières, options, réduction)

# Commit 6 — Retrait workaround patch #31
fix(optim/ui): redirect vers /devis/{id} après création (page détail multi-lots opérationnelle)

# Commit 7 — Tests
test(devis): 6 nouveaux tests E2E création chiffrée + modifier + réduction + non-régression

# Pas de Co-Authored-By
# pytest vert à chaque commit
# Pas de push avant validation chat
```

---

## 11. SACRED Invariants — INTOUCHABLES

- ❌ Logique `cost_engine` (V1a/V1b/V7a/V8a-e préservés, appelé via aggregator existant)
- ❌ Mapping rotation `rotation_se.py`
- ❌ Composant `SchemaImplantation` (Vue A/B/C) — réutilisé tel quel dans LotCard
- ❌ Modèle `Cylindre` et `LotProduction` (juste lecture + écriture cout_lot_ht qui existe)
- ❌ Auth JWT + multi-tenant strict (`get_or_404_scoped`)
- ❌ Composant `DevisResult` legacy (intact pour devis mono-lot existants)

---

## 12. Hors-scope explicite

- ❌ Génération PDF devis pro (Sprint 17)
- ❌ Refonte UI /calculer-un-devis (juste ajout pré-chargement)
- ❌ Modification du modèle Cylindre ou LotProduction
- ❌ Nouvelle page d'édition multi-lots dédiée (on réutilise /calculer-un-devis avec param)
- ❌ Historique d'audit des modifs devis
- ❌ Workflow d'approbation/statuts devis (brouillon → envoyé → accepté)

---

## 13. Antipatterns à éviter

- ❌ Réimplémenter le cost_engine — réutiliser l'aggregator existant
- ❌ Modifier les valeurs EXACT V1a/V1b/V7a/V8a-e
- ❌ Casser le composant `DevisResult` legacy
- ❌ Réécrire `SchemaImplantation`
- ❌ Suppression dure d'un devis existant à la modification (toujours PATCH, jamais DELETE + INSERT)
- ❌ Co-Authored-By dans un commit

---

## 14. Critères d'acceptation

1. POST /api/devis depuis optim → devis sort avec `prix_vente_ht_eur > 0` calculé via cost_engine_aggregator
2. Page `/devis/[id]` mode multi-lots affiche cards par lot avec SchemaImplantation SACRED + coût par lot + total agrégé
3. Page `/devis/[id]` mode mono-lot legacy intact (DevisResult preservé)
4. Bouton "Modifier ce devis" redirige vers `/calculer-un-devis?devis_id=X`
5. `/calculer-un-devis?devis_id=X` pré-charge lots, matières, options, réduction
6. Champ réduction commerciale (%) existant ou ajouté + applicable + persistant
7. PATCH /api/devis/{id} fonctionne avec recalcul cost_engine si lots/options changent
8. Workaround patch #31 retiré : redirect /devis/{id} après création
9. pytest 743+ passed, 0 failed
10. TypeScript `tsc` clean
11. Vercel deploy preview review OK
12. SACRED tous préservés
13. Pas de mention nominative

---

## 15. Démarrage

```bash
cd ~/projets/devis-flexo
git checkout main && git pull
git checkout -b feat/devis-multilots-chiffrage-auto-et-modifier

# Copier ce brief dans docs/
cp ~/Downloads/Brief_CC_32_Devis_Multilots_Chiffrage.md docs/
git add docs/Brief_CC_32_Devis_Multilots_Chiffrage.md
git commit -m "docs: ajout brief #32 devis multi-lots chiffrage auto + modifier"

# Démarrer commit 1 (backend cost_engine call PRIORITAIRE car débloque tout le reste)
# Puis 2 → 7 dans l'ordre
# pytest vert à chaque commit
# Pas de push avant validation du responsable produit
```

---

**Brief #32 — ~12-15h dev solo · 7 commits · 1 PR · architecture hybride C · SACRED préservés**
