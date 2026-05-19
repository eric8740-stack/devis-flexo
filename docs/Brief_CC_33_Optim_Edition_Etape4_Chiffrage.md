# Brief CC #33 — Page optim = source unique pour création + édition multi-lots

> Sprint 13 avenant · étape 4 chiffrage NEW + mode édition · ~13-15h · 1 PR

**Repo** : `devis-flexo` (cwd local)
**Branche** : `feat/optimisation-edition-mode-et-etape4-chiffrage` depuis `main` (après merge brief #32)
**Référence** : Brief #32 mergé (chiffrage auto au POST + DevisResultMultiLots + édition réduction seule)

---

## 1. Contexte — asymétrie édition résiduelle

Après brief #32, l'asymétrie d'édition n'est toujours pas résolue :

| Type devis | Voir | Modifier |
|---|---|---|
| Mono-config legacy (4 785 €) | ✅ DevisResult complet | ✅ `/devis/[id]/edit` complet (form Calculer un devis classique) |
| Multi-lots (0 € → chiffré auto #32) | ✅ DevisResultMultiLots | ❌ `/devis/[id]/edit` réduit : **uniquement réduction commerciale**, lots figés |

**Cause** : le brief #32 a livré le mode édition multi-lots en version réduite (commit 5 hors-scope assumé). Les lots ne peuvent pas être modifiés.

---

## 2. Architecture cible — page optim = source unique

**Décision stratégique** : la page `/optimisation` (workflow 3 étapes "parfait" selon brief #28) devient la **source unique de vérité** pour création ET édition d'un devis multi-lots. On y ajoute une **étape 4 NEW** dédiée au chiffrage (options de fabrication globales, marge override, réduction commerciale).

### Workflow

```
CRÉATION                                    ÉDITION
─────────                                   ───────
/optimisation                               /devis/[id] (vue détail)
  Étape 1 : saisie                            ↓ bouton "Modifie ton devis"
  Étape 2 : candidats + multi-sélect         /optimisation?devis_id=X
  Étape 3 : matières par lot                   Étapes 1-3 pré-remplies depuis devis
  Étape 4 NEW : chiffrage                      Étape 4 : ajuste options/marge/réduction
   options globales · marge · réduction       ↓ "Mettre à jour le devis"
  ↓ "Créer le devis"                           PUT /api/devis/{id}
  POST /api/devis                                recalcul cost_engine_aggregator
  → redirect /devis/{id}                       → redirect /devis/{id}
```

### Avantages

- ✅ 1 seul outil pour créer + modifier un devis multi-lots
- ✅ UX cohérente : on édite avec l'outil qui a créé
- ✅ Étapes 1-3 réutilisées tel quel (SACRED workflow #28)
- ✅ Étape 4 NEW centralise toute la dimension "commerciale" (options, marge, réduction)
- ✅ Page `/devis/[id]/edit` legacy reste intacte pour mono-config

### Sacred preserved

- ❌ `/devis/[id]/edit` legacy mono-config : aucune modification
- ❌ `DevisResult` legacy : aucune modification
- ❌ Étapes 1-3 workflow optim : aucune modification (juste pré-remplissage en mode édition)
- ❌ `cost_engine` logique : appelée via aggregator existant
- ❌ `SchemaImplantation` Vue A/B/C : réutilisée tel quel

---

## 3. Périmètre — 7 livrables en 1 PR

| # | Livrable | Charge |
|---|---|---|
| 1 | Composant **Étape 4 NEW** : `OptimisationChiffrage` (options globales, marge, réduction, récap brut/net) | 4-5h |
| 2 | Page `/optimisation` détection `?devis_id=X` → mode édition, pré-remplit étapes 1-3 | 3-4h |
| 3 | Bouton "Modifie ton devis" sur `/devis/[id]` redirige vers `/optimisation?devis_id=X` | 30min |
| 4 | Backend : PUT `/api/devis/{id}` accepte payload optim complet + recalcul cost_engine_aggregator | 2-3h |
| 5 | **Intégration `SchemaImplantation` Vue A/B/C par lot** dans `DevisResultMultiLots` (dette tech #32) | 2h |
| 6 | Design coloré joyeux cohérent #29/#30/#32 (étape 4 + récap) | inclus |
| 7 | Tests E2E création + édition | 1-2h |
| **Total** | | **~13-15h** |

---

## 4. Fix #1 — Composant Étape 4 NEW : `OptimisationChiffrage`

### Spec UI

```
┌──── ÉTAPE 4 ─ Chiffrage devis ─────────────────────────────────────┐
│ Récap des 2 lots :                                                 │
│   • Lot 1 — Cyl 104 · MA 2200 · 10 000 étiq · PP couché 80g       │
│   • Lot 2 — Cyl 132 · MA 2200 · 5 000 étiq · PET blanc 50µ        │
│                                                                    │
│ ╔══════════════════════════════════════════════════════════════╗   │
│ ║ 🛠️  Options de fabrication (globales devis)                  ║   │
│ ║                                                              ║   │
│ ║ ☑ Pose en paravents/accordéon       vit ×0.95 · gâche ×1.02 ║   │
│ ║ ☐ Étiquettes livret (booklet)                                ║   │
│ ║ ☐ Codes variables (QR, DataMatrix)                           ║   │
│ ║ ☐ Numérotation séquentielle                                  ║   │
│ ║ ☐ Découpe split-liner                                        ║   │
│ ║ ☐ Perforation liner                                          ║   │
│ ║ ☐ Pré-découpe / micro-perforation                            ║   │
│ ║ ☐ Encre invisible UV / thermochrome                          ║   │
│ ║ ☐ Dorure à chaud (hot foil)                                  ║   │
│ ║ ☐ Dorure à froid (cold foil)                                 ║   │
│ ║ ☐ Pelliculage / lamination                                   ║   │
│ ║ ☐ Impression sur colle (back-print)                          ║   │
│ ║ ☐ Impression verso complète                                  ║   │
│ ║ ☐ Sérigraphie inline (opacité maxi)                          ║   │
│ ║ ☐ Vernis sélectif                                            ║   │
│ ║ ☐ RFID inline                                                ║   │
│ ║ ☐ Gaufrage / embossage                                       ║   │
│ ║ ☐ Sérialisation pharma (FMD)                                 ║   │
│ ║ ☐ Hologramme / anti-contrefaçon                              ║   │
│ ║ ☐ Étiquettes inviolables / VOID                              ║   │
│ ╚══════════════════════════════════════════════════════════════╝   │
│                                                                    │
│ ╔══════════════════════════════════════════════════════════════╗   │
│ ║ 💰  Marge & réduction commerciale                            ║   │
│ ║                                                              ║   │
│ ║ Marge override (%)    [ 35 ] %   (vide = défaut entreprise)  ║   │
│ ║                                                              ║   │
│ ║ Réduction commerciale (%)  [ 0 ] %                           ║   │
│ ║ Remise globale appliquée par-dessus le coût calculé          ║   │
│ ╚══════════════════════════════════════════════════════════════╝   │
│                                                                    │
│ ╔══════════════════════════════════════════════════════════════╗   │
│ ║                                                              ║   │
│ ║   💰 COÛT TOTAL DEVIS HT                                     ║   │  ← card hero gradient bleu→or
│ ║                                                              ║   │
│ ║      Brut       2 145,80 €                                   ║   │
│ ║      Réduction  −0,00 € (0%)                                 ║   │
│ ║      ───────────────────────                                 ║   │
│ ║      Net        2 145,80 €                                   ║   │  ← Fraunces XL bold
│ ║                                                              ║   │
│ ║   15 000 étiquettes · 2 lots                                 ║   │
│ ╚══════════════════════════════════════════════════════════════╝   │
│                                                                    │
│ [ ← Retour étape 3 ]    [ ✓ Créer le devis ] ou [ ✓ Mettre à jour]│
└────────────────────────────────────────────────────────────────────┘
```

### Comportement

- **Options de fabrication** : cases à cocher globales (s'appliquent à TOUS les lots, pas par lot). Microcopie discrète à côté de chaque option pour rappeler les coefs vitesse/gâche.
- **Recalcul live** : à chaque toggle d'option ou changement de marge/réduction → appel API endpoint léger `POST /api/devis/preview-couts` qui retourne le coût brut/net sans persister
- **Bouton final** :
  - Mode création : "✓ Créer le devis" → POST `/api/devis` → redirect `/devis/{id}`
  - Mode édition : "✓ Mettre à jour le devis" → PUT `/api/devis/{id}` → redirect `/devis/{id}`
- **Bouton retour** : "← Retour étape 3" remet l'utilisateur sur l'édition des matières

### Endpoint preview-couts NEW (backend)

```python
# backend/app/api/devis.py

@router.post("/devis/preview-couts", response_model=PreviewCoutsOut)
def preview_couts(payload: PreviewCoutsIn, db, user):
    """Calcule le coût brut/net sans persister. Pour live update étape 4."""
    # Construction DevisInput par lot via mapper existant brief #32
    devis_inputs = [
        construire_devis_input_depuis_payload(lot, payload.contexte_global)
        for lot in payload.lots
    ]
    cout_agrege = cost_engine_aggregator.calculer_devis_multilots(devis_inputs)
    
    cout_brut = cout_agrege.cout_total_ht
    reduction_eur = cout_brut * (payload.reduction_pct or 0) / 100
    cout_net = cout_brut - reduction_eur
    
    return {
        "cout_brut_ht": cout_brut,
        "reduction_eur": reduction_eur,
        "reduction_pct": payload.reduction_pct or 0,
        "cout_net_ht": cout_net,
    }
```

---

## 5. Fix #2 — Mode édition `/optimisation?devis_id=X`

### Détection mode

```tsx
// frontend/src/app/optimisation/page.tsx

const searchParams = useSearchParams();
const devisId = searchParams.get("devis_id");
const isModeEdition = !!devisId;

const [devisExistant, setDevisExistant] = useState<DevisOut | null>(null);

useEffect(() => {
  if (devisId) {
    fetch(`/api/devis/${devisId}`)
      .then(r => r.json())
      .then(devis => {
        setDevisExistant(devis);
        // Pré-remplir les étapes 1-3 depuis devis
        optimStore.hydraterDepuisDevis(devis);
      });
  }
}, [devisId]);
```

### Pré-remplissage `OptimisationPoseStore.hydraterDepuisDevis()`

```typescript
hydraterDepuisDevis(devis: DevisOut) {
  // Étape 1 : saisie format + paramètres
  this.params = {
    laize: devis.format_laize,
    dev: devis.format_dev,
    rayon_angles: devis.rayon_angles ?? 2,
    nb_couleurs: devis.nb_couleurs ?? 4,
    quantite_totale: devis.quantite_totale,
    sens_enroulement: devis.lots[0]?.sens_enroulement ?? 1,
    intervalle_dev_min_imprimerie: 2,
    intervalle_dev_min_client: 2,
    // ... autres champs
  };
  
  // Étape 2-3 : lots déjà choisis
  this.lots = devis.lots.map(lot => ({
    candidatId: `${lot.cylindre_id}-${lot.machine_id}-${lot.nb_poses_dev}-${lot.nb_poses_laize}`,
    cylindre_id: lot.cylindre_id,
    machine_id: lot.machine_id,
    nb_poses_dev: lot.nb_poses_dev,
    nb_poses_laize: lot.nb_poses_laize,
    quantite: lot.quantite,
    matiere_id: lot.matiere_id,
  }));
  
  // Étape 4 : options + marge + réduction
  this.options = devis.payload_input?.options ?? [];
  this.marge_override_pct = devis.payload_input?.pct_marge_override;
  this.reduction_pct = devis.reduction_pct ?? 0;
  
  this.etape = "chiffrage"; // ouvre direct l'étape 4 en mode édition
  this.estModeEdition = true;
  this.devisExistantId = devis.id;
}
```

### Bandeau visuel mode édition

En haut de la page `/optimisation` quand `?devis_id=X` :

```tsx
{isModeEdition && (
  <div className="bg-gradient-to-r from-[var(--accent-soft)] to-[var(--gold-soft)] 
                  border-l-4 border-[var(--accent)] p-4 rounded-md">
    <p className="font-semibold text-[var(--accent)]">
      ✎ Tu modifies le devis <code>{devisExistant.numero}</code>
    </p>
    <p className="text-sm text-[var(--ink-soft)]">
      Toutes les étapes sont pré-remplies. Ajuste ce qui doit changer et clique sur 
      "Mettre à jour le devis" en bas de l'étape 4.
    </p>
  </div>
)}
```

---

## 6. Fix #3 — Bouton "Modifie ton devis" redirige `/optimisation?devis_id=X`

```tsx
// frontend/src/components/devis/DevisResultMultiLots.tsx

<Button
  size="lg"
  variant="primary"
  onClick={() => router.push(`/optimisation?devis_id=${devis.id}`)}
  className="bg-gradient-to-r from-[var(--accent)] to-[var(--gold)] text-white font-semibold px-8 py-4"
>
  ✎ Modifie ton devis
</Button>
```

Retrait du routage actuel vers `/devis/[id]/edit` (brief #32). La page `/devis/[id]/edit` reste accessible pour les **devis mono-config legacy**.

---

## 7. Fix #4 — Backend PUT `/api/devis/{id}` payload optim complet

### Endpoint étendu

```python
@router.put("/devis/{id}", response_model=DevisOut)
def modifier_devis(id: int, payload: DevisUpdate, db, user):
    devis = get_or_404_scoped(Devis, id, user.entreprise_id)
    
    # 1. Si payload contient des lots → remplacer + recalculer cost_engine
    if payload.lots is not None:
        # Supprimer anciens lots (cascade)
        db.query(LotProduction).filter(LotProduction.devis_id == id).delete()
        
        # Insérer nouveaux lots
        nouveaux_lots = [
            LotProduction(
                devis_id=id,
                entreprise_id=user.entreprise_id,
                ordre=idx + 1,
                **lot_payload.dict()
            )
            for idx, lot_payload in enumerate(payload.lots)
        ]
        db.add_all(nouveaux_lots)
        db.flush()
        
        # Recalcul cost_engine_aggregator avec options globales
        devis_inputs = [
            construire_devis_input_depuis_lot(lot, devis, payload.options or [])
            for lot in nouveaux_lots
        ]
        cout_agrege = cost_engine_aggregator.calculer_devis_multilots(devis_inputs)
        
        devis.payload_output = {
            "mode": "multi-lots",
            "prix_vente_ht_eur": float(cout_agrege.cout_total_ht),
            "details_par_lot": [...],
        }
        
        for lot, cl in zip(nouveaux_lots, cout_agrege.details_par_lot):
            lot.cout_lot_ht = cl.cout_ht
    
    # 2. Update options globales
    if payload.options is not None:
        devis.payload_input = {**(devis.payload_input or {}), "options": payload.options}
    
    # 3. Update marge override
    if payload.pct_marge_override is not None:
        devis.payload_input = {**(devis.payload_input or {}), "pct_marge_override": payload.pct_marge_override}
    
    # 4. Update réduction commerciale
    if payload.reduction_pct is not None:
        devis.reduction_pct = payload.reduction_pct
    
    db.commit()
    return devis
```

### Sacred preserved

- ✅ `cost_engine` logique inchangée
- ✅ Valeurs EXACT V1a/V1b/V7a/V8a-e préservées (recalcul via aggregator)
- ✅ Multi-tenant strict (`get_or_404_scoped`)
- ✅ Cascade lots gérée (suppression douce pas nécessaire car on remplace tout l'état)

---

## 8. Fix #5 — Intégration `SchemaImplantation` par lot dans `DevisResultMultiLots`

Dette technique du brief #32 enfin résolue.

### Mapping props

Pour chaque lot affiché dans `DevisResultMultiLots`, fetcher les données visuelles via l'endpoint existant `GET /api/optimisation/candidats/{id}/visuel` ou bien stocker les data dans le LotProduction lors de la création/mise à jour.

**Option simple** : stocker `visuel_data` dans `LotProduction.payload_visuel` (JSONB) au moment de la création/PUT, calculé une fois.

```python
# Lors POST/PUT devis
for lot in lots:
    lot.payload_visuel = {
        "rotation_vue_a_deg": ...,  # depuis rotation_se.py SACRED
        "rotation_vue_c_deg": ...,
        "positions_a": [...],
        "sens_enroulement": lot.sens_enroulement,
        "laize_papier": ...,
        "liner_mm": ...,
        "ml_total": ...,
    }
```

### UI

```tsx
function LotCard({ lot, index }: { lot: LotProductionOut, index: number }) {
  const colorIndex = (index - 1) % 3;  // bleu, or, vert rotatif
  const borderColors = ["var(--accent)", "var(--gold)", "var(--green)"];
  
  return (
    <Card 
      className="hover:shadow-lg transition-shadow"
      style={{ borderLeft: `4px solid ${borderColors[colorIndex]}` }}
    >
      <CardHeader>
        <span className="text-2xl mr-2">{["🔵", "🟡", "🟢"][colorIndex]}</span>
        LOT {index}
      </CardHeader>
      <CardContent>
        <div>Cyl {lot.cylindre_nb_dents} dents · {lot.machine_nom}</div>
        <div>{lot.nb_poses_dev}×{lot.nb_poses_laize}={lot.nb_poses_dev*lot.nb_poses_laize} poses</div>
        <div>Sens {lot.sens_enroulement} · {lot.quantite} étiquettes</div>
        <div>Matière : {lot.matiere_nom}</div>
        
        {/* SchemaImplantation SACRED réutilisé tel quel */}
        <div className="bg-[var(--bg)] p-4 rounded-lg mt-4">
          <SchemaImplantation {...lot.payload_visuel} />
        </div>
        
        <div className="text-lg font-bold text-[var(--accent)] mt-4 pt-4 border-t">
          Coût lot HT · {lot.cout_lot_ht.toFixed(2)} €
        </div>
      </CardContent>
    </Card>
  );
}
```

### Sacred preserved

- ✅ Composant `SchemaImplantation` Vue A/B/C : **réutilisé tel quel**, aucune modification du rendu

---

## 9. Design joyeux — guidelines (NON NÉGOCIABLE)

Cohérence avec briefs #29/#30/#32. Étape 4 nouvelle doit respecter :

### Palette CSS variables

```css
--bg: #fef8ea          /* fond chaleureux */
--accent: #1a52a3      /* bleu profond */
--gold: #c79a3a        /* or */
--green: #2d7a4f       /* vert */
--ink: #1a2238         /* texte */
```

### Patterns à appliquer Étape 4

| Élément | Design |
|---|---|
| Header étape 4 | Gradient subtle + titre Fraunces avec emoji 💰 |
| Card "Options de fabrication" | Border-left 4px bleu accent + fond gradient subtle + checkboxes avec labels colorés |
| Card "Marge & réduction" | Border-left 4px or + microcopie tutoyée |
| Card hero coût total | **Gradient bleu→or prominent**, valeur en Fraunces XL bold, séparateur ornemental entre brut/réduction/net |
| Bouton "Créer/Mettre à jour" | Gradient bleu→or rempli, taille `lg`, icône ✓ |
| Bouton retour étape 3 | Secondary outlined coloré (pas gris) |
| Bandeau mode édition | Gradient bleu→ambre, icône ✎, microcopie tutoyée |
| Loading recalcul live | Skeleton coloré accent (pas gris) |
| Toast succès création/maj | Vert + ✅ |

### Microcopie tutoyée

- "Crée ton devis" / "Mets à jour ton devis"
- "Ajuste ta marge" pas "Modifier la marge"
- "Ta réduction" pas "Réduction"
- "Brut" / "Net" en termes simples (pas "TVA incluse" complexes)

---

## 10. Plan commits (7 commits cohérents)

```bash
git checkout main && git pull
git checkout -b feat/optimisation-edition-mode-et-etape4-chiffrage

# Commit 1 — Backend PUT recalcul + endpoint preview-couts
feat(devis/api): PUT /api/devis/{id} accepte payload optim complet + recalcul cost_engine_aggregator + endpoint preview-couts pour live update

# Commit 2 — Composant Étape 4 OptimisationChiffrage
feat(optim/ui): étape 4 chiffrage NEW (options globales, marge, réduction, récap hero gradient bleu→or, recalcul live)

# Commit 3 — Mode édition /optimisation?devis_id=X
feat(optim/ui): détection mode édition via ?devis_id=X, hydraterDepuisDevis pré-remplit étapes 1-4, bandeau visuel mode édition

# Commit 4 — Bouton "Modifie ton devis" redirige optim
feat(devis/ui): bouton "Modifie ton devis" sur DevisResultMultiLots redirige /optimisation?devis_id=X

# Commit 5 — SchemaImplantation par lot (dette tech #32)
feat(devis/ui): intégration SchemaImplantation Vue A/B/C par lot dans DevisResultMultiLots (composant SACRED réutilisé)

# Commit 6 — Design joyeux étape 4 + cohérence
feat(optim/ui): polish design étape 4 (gradients, cards bordées, microcopie tutoyée, animations transition)

# Commit 7 — Tests E2E création + édition
test(optim): 8 nouveaux tests E2E création multi-lots avec options + édition complète multi-lots

# Pas de Co-Authored-By
# pytest vert à chaque commit
# Pas de push avant validation chat
```

---

## 11. SACRED Invariants — INTOUCHABLES

- ❌ Logique `cost_engine` (V1a/V1b/V7a/V8a-e préservés, appelé via aggregator existant)
- ❌ Mapping rotation `rotation_se.py`
- ❌ Composant `SchemaImplantation` Vue A/B/C : réutilisé tel quel dans LotCard
- ❌ Étapes 1-3 du workflow `/optimisation` : aucune modification (pré-remplissage seulement)
- ❌ Page `/devis/[id]/edit` legacy mono-config : intacte
- ❌ Composant `DevisResult` legacy : intact
- ❌ Modèle `Cylindre`, `LotProduction`, `Devis` : pas de modif schéma (juste utilisation)
- ❌ Auth JWT + multi-tenant strict (`get_or_404_scoped`)
- ❌ Compte `entreprise_id=1` : 21 cyl actifs préservés

---

## 12. Hors-scope explicite

- ❌ Options de fabrication PAR LOT (toutes les options restent globales au devis)
- ❌ Édition simultanée concurrente (lock / WebSocket)
- ❌ Historique des modifications (audit log)
- ❌ Génération PDF devis pro (Sprint 17)
- ❌ Validation/envoi du devis au client (Sprint 17+)
- ❌ Duplication d'un devis avec modifications (bouton "Dupliquer" existe déjà en l'état)
- ❌ Modifier la page `/devis/[id]/edit` legacy pour multi-lots (on bypass via redirection vers optim)
- ❌ Refonte UI étapes 1-3 (SACRED)

---

## 13. Antipatterns à éviter

- ❌ Modifier les valeurs EXACT V1a/V1b/V7a/V8a-e
- ❌ Casser le mode mono-config legacy (`/devis/[id]/edit` doit rester fonctionnel)
- ❌ Réécrire `SchemaImplantation`
- ❌ Modifier les étapes 1-3 du workflow optim
- ❌ Recalcul cost_engine côté front (toujours côté back via endpoints)
- ❌ Pré-remplissage partiel : si on entre en mode édition, TOUTES les étapes doivent être pré-remplies correctement
- ❌ Boutons gris ternes (toujours primary remplis gradients sur les CTA)
- ❌ Suppression dure d'un devis lors de l'édition (PUT remplace, pas DELETE + POST)
- ❌ Co-Authored-By dans un commit

---

## 14. Critères d'acceptation

1. **Création** : workflow `/optimisation` étapes 1→4 complète, l'étape 4 affiche options/marge/réduction, recalcul live à chaque toggle, "Créer le devis" → POST → redirect `/devis/{id}`
2. **Édition** : depuis `/devis/{id}` → "Modifie ton devis" → `/optimisation?devis_id=X` → toutes les étapes pré-remplies, l'étape 4 ouverte par défaut, "Mettre à jour" → PUT → redirect `/devis/{id}`
3. Mode édition affiche un bandeau visuel "Tu modifies le devis DEV-XXXX"
4. Backend PUT `/api/devis/{id}` accepte payload optim complet (lots + options + marge + réduction) + recalcul cost_engine_aggregator
5. Endpoint `POST /api/devis/preview-couts` fonctionne pour live update sans persister
6. `SchemaImplantation` Vue A/B/C affiché par lot dans `DevisResultMultiLots` (dette tech #32 résolue)
7. Mono-config legacy intact : `/devis/[id]/edit` fonctionne toujours pour les devis créés via `/calculer-un-devis` historique
8. Design joyeux : gradients sur boutons, cards colorées, microcopie tutoyée, état édition visuellement distinct
9. pytest baseline + 8 nouveaux = cible 752+ passed
10. TypeScript `tsc` clean
11. Vercel deploy preview review OK
12. SACRED tous préservés
13. Pas de mention nominative dans tout le code/commits/docs

---

## 15. Démarrage

```bash
cd ~/projets/devis-flexo
git checkout main && git pull
git checkout -b feat/optimisation-edition-mode-et-etape4-chiffrage

# Copier ce brief dans docs/
cp ~/Downloads/Brief_CC_33_Optim_Edition_Etape4_Chiffrage.md docs/
git add docs/Brief_CC_33_Optim_Edition_Etape4_Chiffrage.md
git commit -m "docs: ajout brief #33 optim édition mode + étape 4 chiffrage"

# Démarrer par commit 1 (backend) car débloque le reste
# Puis 2 → 7 dans l'ordre
# pytest vert à chaque commit
# Pas de push avant validation chat

# Si edge case bloquant pendant l'exécution (SACRED en risque, refonte
# cost_engine nécessaire, etc.) → STOP et flag en chat.
```

---

**Brief #33 — ~13-15h dev solo · 7 commits · 1 PR · page optim = source unique vérité · SACRED préservés**
