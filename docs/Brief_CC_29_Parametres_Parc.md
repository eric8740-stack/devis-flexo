# Brief CC #29 — Paramètres parc cylindres + porte-clichés

> Sprint 13 avenant · CRUD multi-tenant · UX simple + colorée · ~12-14h · 1 PR

**Repo** : `devis-flexo` (cwd local)
**Branche** : `feat/parametres-parc-cylindres-porte-cliches` depuis `main = bcc8380`
**Référence** : Brief #28 mergé (parc compte demo seedé 21 cyl actifs)

---

## 1. Philosophie UX — non négociable

**Cible utilisateur** : imprimeur flexo qui lance un devis en 30 sec sans lire de doc. Pas un ingénieur. Pas un power user.

### Principes

1. **Pré-rempli, jamais bloqué** : un nouveau compte hérite d'un parc démo prêt à l'emploi. L'utilisateur n'EST PAS obligé de configurer quoi que ce soit avant de lancer un devis.
2. **CRUD parc = option, pas obligation** : aucune entrée "Cylindres" ou "Porte-clichés" en sidebar principale. Accès via `Paramètres → Mon parc` (lien discret).
3. **Couleurs joyeuses, pas austère B2B** : palette projet existante (beige crème + bleu profond + or + verts/oranges), illustrations engageantes, microcopie humaine. Pas Excel-like.
4. **Pas faire peur** : zéro jargon technique en surface, pas d'icônes industrielles. Le ton est "ton atelier, tes outils".

### Références ton

| ❌ À éviter | ✅ Cible |
|---|---|
| "Liste des cylindres" | "Tes cylindres" |
| "Créer un porte-cliché" | "Ajouter un porte-cliché" |
| "Statut: actif/inactif" | Toggle visuel coloré "Utilisé · Non utilisé" |
| "Aucun résultat trouvé" | "Pas encore de porte-cliché — ajoutes-en un en 30 secondes" |
| Tableau dense Excel | Cards aérées + tableau compact en alternative |

---

## 2. Périmètre — 6 livrables en 1 PR

| # | Livrable | Charge |
|---|---|---|
| 1 | Modèle `PorteCliche` + migration Alembic | 1-1.5h |
| 2 | Endpoints REST `/api/cylindres` (CRUD + toggle actif) | 2h |
| 3 | Endpoints REST `/api/porte-cliches` (CRUD + toggle actif) | 1.5h |
| 4 | Page `/parametres/mon-parc` (hub avec 2 onglets : Cylindres / Porte-clichés) | 4-5h |
| 5 | Composants UI shadcn customisés (cards, dialog ajout/modif, toggle actif coloré) | 2h |
| 6 | Tests CRUD + multi-tenant + soft delete | 2h |
| **Total** | | **~13h** |

---

## 3. Modèle `PorteCliche` — proposé

> Sémantique métier : un porte-cliché (sleeve / plate mounting cylinder) est le support physique monté sur le cylindre porteur machine. Il porte le cliché flexo. Distinct du `Cylindre` (qui dans la DB représente le développé/nb_dents, équivalent métier au sleeve dans les ateliers modernes). Le `PorteCliche` ici = support physique réutilisable, indépendant du développé.

```python
# backend/app/models/porte_cliche.py

class PorteCliche(Base):
    __tablename__ = "porte_cliches"

    id = Column(Integer, primary_key=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)

    reference = Column(String(50), nullable=False)        # ex "PC-01", "Sleeve-200mm"
    marque = Column(String(80), nullable=True)            # ex "Rotec", "DuPont", "Flint"
    modele = Column(String(80), nullable=True)            # ex "Cyrel Fast"

    laize_utile_mm = Column(Numeric(6, 2), nullable=False)  # largeur utile cliché
    diametre_interieur_mm = Column(Numeric(6, 2), nullable=True)  # mandrin compatible

    matiere = Column(String(40), nullable=True)            # acier / polyuréthane / carbone / autre
    notes = Column(Text, nullable=True)

    actif = Column(Boolean, nullable=False, default=True, server_default="true")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entreprise = relationship("Entreprise", back_populates="porte_cliches")

    __table_args__ = (
        UniqueConstraint("entreprise_id", "reference", name="uq_porte_cliche_ref_entreprise"),
        Index("ix_porte_cliches_entreprise", "entreprise_id"),
    )
```

### Seed compte demo (entreprise_id=1)

3-5 porte-clichés exemples pour que le compte demo soit "prêt à l'emploi" :

| reference | marque | laize_utile_mm | matiere |
|---|---|---|---|
| PC-220 | Rotec | 220 | polyuréthane |
| PC-330 | DuPont Cyrel | 330 | polyuréthane |
| PC-410 | Flint | 410 | carbone |

À voir avec toi si tu veux des valeurs précises ou si je laisse CC mettre des exemples génériques.

---

## 4. Endpoints REST

### `/api/cylindres` — NEW (création complète du router)

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/cylindres` | Liste paginée des cyl de l'entreprise (query `?actif=true` filtre par défaut) |
| POST | `/api/cylindres` | Crée un cyl (validation nb_dents > 0, unicité par entreprise) |
| GET | `/api/cylindres/{id}` | Détail (multi-tenant scope strict) |
| PATCH | `/api/cylindres/{id}` | Modifie (champs partiels) |
| DELETE | `/api/cylindres/{id}` | **Soft delete** → passe `actif=false` (FK historique préservée) |
| POST | `/api/cylindres/{id}/toggle-actif` | Bascule actif/inactif (alternative au DELETE) |

### `/api/porte-cliches` — NEW

Mêmes patterns que `/api/cylindres`.

### Pydantic schemas

```python
class CylindreCreate(BaseModel):
    nb_dents: int = Field(ge=20, le=300)  # bornes raisonnables flexo
    actif: bool = True
    notes: Optional[str] = None

class CylindreUpdate(BaseModel):
    nb_dents: Optional[int] = Field(None, ge=20, le=300)
    actif: Optional[bool] = None
    notes: Optional[str] = None

class CylindreOut(BaseModel):
    id: int
    nb_dents: int
    developpe_mm: Decimal  # auto-calculé nb_dents * 3.175
    actif: bool
    created_at: datetime
    # … pas d'entreprise_id exposé (info interne multi-tenant)
```

Multi-tenant strict : `get_or_404_scoped(Cylindre, entreprise_id=current_user.entreprise_id)` sur toutes les routes (sauf liste qui filtre direct par entreprise).

---

## 5. UI — Pages `/parametres/mon-parc`

### Navigation

Ajouter dans la page `/parametres/` existante une **card cliquable joyeuse** "Mon parc" qui mène à `/parametres/mon-parc`. Pas d'entrée sidebar séparée.

Sur la page `/parametres/mon-parc` : 2 onglets shadcn (`Tabs`) :
- 🎯 **Mes cylindres** (default)
- 🎯 **Mes porte-clichés**

### Onglet "Mes cylindres" — wireframe esprit

```
┌─────────────────────────────────────────────────────────────┐
│ 🔧 Mes cylindres                          [+ Ajouter]       │
│ Les cylindres que tu utilises sur tes machines flexo        │
│                                                             │
│ [Toggle: ✓ Voir uniquement actifs]   [Recherche...]        │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 104 dents · Z = 330,2 mm                       [●━━━]   │ │
│ │ Utilisé sur Mark Andy 2200, OMET XFlex 330              │ │
│ │                                       [Modifier]  [⋯]   │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 132 dents · Z = 419,1 mm                       [●━━━]   │ │
│ │ ...                                  [Modifier]  [⋯]    │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 80 dents · Z = 254 mm  ℹ Petit cylindre        [●━━━]   │ │
│ │ ...                                  [Modifier]  [⋯]    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 21 cylindres actifs · 3 désactivés [Voir tout]              │
└─────────────────────────────────────────────────────────────┘
```

### Composants UI

- **Cards aérées** (pas tableau dense). Border-radius doux. Shadow légère.
- **Toggle actif coloré** (vert quand actif, gris doux quand inactif). Animation transition fluide.
- **Bouton "+ Ajouter"** primaire, couleur accent (bleu profond ou or). Visible, accueillant.
- **Menu `[⋯]`** : Modifier · Désactiver/Réactiver · Voir l'historique des devis (futur)
- **Dialog ajout/modif** : shadcn `Dialog`, champs minimaux (nb_dents + notes), validation inline.
- **État vide joyeux** : illustration SVG simple + "Tu n'as pas encore de cylindre — ajoutes-en un en 30 secondes" + CTA gros bouton.
- **Badge "ℹ Petit cylindre"** sur lignes ≤ 80 dents (réutilise composant Sprint #28).

### Onglet "Mes porte-clichés"

Même UX que cylindres, adapté au modèle PorteCliche :

```
┌─────────────────────────────────────────────────────────────┐
│ 📐 Mes porte-clichés                       [+ Ajouter]      │
│ Les sleeves / supports que tu utilises pour monter tes clichés │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ PC-220 · Rotec · 220 mm utiles                 [●━━━]   │ │
│ │ Polyuréthane · Mandrin 76 mm                            │ │
│ │                                       [Modifier]  [⋯]   │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ...                                                         │
└─────────────────────────────────────────────────────────────┘
```

### Palette + ton — guidelines design

Réutilise les CSS variables du projet :

```css
--bg: #fef8ea          /* fond chaleureux beige crème */
--accent: #1a52a3      /* bleu profond — boutons primaires */
--gold: #c79a3a        /* or — accents premium */
--green: #2d7a4f       /* vert — état actif, succès */
--ink: #1a2238         /* texte principal */
--ink-soft: #3a4458    /* texte secondaire */
```

**Style général** : font Atkinson Hyperlegible + Fraunces pour titres (déjà en place). Beaucoup d'espace blanc. Coins arrondis 8-12px sur cards. Hover states subtils. Transitions 200ms.

**Microcopie** : tutoiement systématique. Phrases courtes. Encouragement plutôt qu'instruction. Émojis discrets autorisés en titres de sections (🔧 📐 🎯) — pas dans le corps.

---

## 6. Tests

Baseline cible : **719 + 12 nouveaux ≈ 731 passed**

```python
# backend/tests/

test_porte_cliche_model.py
  - test_creation_porte_cliche
  - test_unique_ref_par_entreprise
  - test_soft_delete_via_actif_false

test_porte_cliche_api.py
  - test_crud_complet
  - test_multi_tenant_strict (user entreprise A ne voit pas porte-clichés entreprise B)
  - test_toggle_actif_endpoint

test_cylindre_api.py
  - test_crud_complet
  - test_multi_tenant_strict
  - test_soft_delete_preserve_fk_devis_historique
  - test_validation_nb_dents_bornes

test_parametres_mon_parc_e2e.py  # optionnel si infra Playwright
  - test_navigation_paragraphe_vers_mon_parc
  - test_ajout_cylindre_et_disponibilite_dans_optim
```

---

## 7. Plan commits (6 commits cohérents)

```bash
git checkout main && git pull
git checkout -b feat/parametres-parc-cylindres-porte-cliches

# Commit 1 — Modèle PorteCliche + migration
feat(porte-cliche): modèle + migration Alembic + seed compte demo (3-5 porte-clichés)

# Commit 2 — Endpoints REST cylindres
feat(cylindres/api): CRUD complet + toggle actif + multi-tenant strict

# Commit 3 — Endpoints REST porte-clichés
feat(porte-cliches/api): CRUD complet + toggle actif + multi-tenant strict

# Commit 4 — Page /parametres/mon-parc (UI)
feat(parametres/ui): page Mon Parc avec onglets Cylindres + Porte-clichés (cards aérées, UX joyeuse)

# Commit 5 — Card d'accès depuis /parametres
feat(parametres/ui): card cliquable Mon Parc dans page Paramètres (pas d'ajout sidebar)

# Commit 6 — Tests
test(parc): 12 nouveaux tests CRUD + multi-tenant + soft delete

# Pas de Co-Authored-By
# pytest vert à chaque commit
# Pas de push avant validation du responsable produit
```

---

## 8. SACRED Invariants — INTOUCHABLES

- ❌ Logique `cost_engine` (aucune modif, les valeurs EXACT V1a/V1b/V7a/V8a-e préservées)
- ❌ Composant visuel `SchemaImplantation` (Vue A/B/C) — réutilisé tel quel
- ❌ Mapping rotation `rotation_se.py`
- ❌ Modèle `Cylindre` côté SQLAlchemy (juste ajout de routes REST, pas de modif schéma)
- ❌ Compte demo `entreprise_id=1` : 21 cyl actifs préservés, ajout porte-clichés en seed
- ❌ Auth JWT + multi-tenant strict (`get_or_404_scoped`)

---

## 9. Hors-scope explicite

- ❌ Wizard / assistant de configuration parc (zéro friction = pré-rempli)
- ❌ Import CSV de parc (Sprint 17 import tarifs / data)
- ❌ Page admin globale (route reste `/parametres/...`, pas `/admin/...`)
- ❌ Ajout de menus sidebar pour cylindres ou porte-clichés
- ❌ Permissions granulaires (tout user de l'entreprise peut CRUD son parc)
- ❌ Historique d'audit (créé_par, modifié_par) — défendabilité plus tard
- ❌ Liaison directe `Cylindre ↔ PorteCliche` (pas obligatoire à ce stade)
- ❌ Refonte écran optimisation (déjà mergé en #28)

---

## 10. Antipatterns à éviter

- ❌ Mettre "Cylindres" ou "Porte-clichés" en entrée sidebar
- ❌ Forcer l'utilisateur à configurer son parc avant le premier devis
- ❌ Style austère gris/blanc B2B SaaS (Stripe/Linear/Notion comme référence visuelle, pas SAP/Oracle)
- ❌ Tableau dense Excel-like par défaut (cards d'abord, option tableau compact en toggle si besoin)
- ❌ Jargon technique en surface ("référence interne", "identifiant unique") → microcopie humaine
- ❌ Suppression dure (toujours soft delete via `actif=false`)
- ❌ Oublier le scope multi-tenant sur une route
- ❌ Co-Authored-By dans un commit
- ❌ Refacto "bonus" hors scope

---

## 11. Critères d'acceptation

1. Modèle `PorteCliche` créé en DB avec migration Alembic réversible
2. 3-5 porte-clichés seedés en compte demo (entreprise_id=1)
3. `/api/cylindres` CRUD complet fonctionnel + multi-tenant strict testé
4. `/api/porte-cliches` CRUD complet fonctionnel + multi-tenant strict testé
5. Page `/parametres/mon-parc` accessible via card depuis `/parametres`
6. **AUCUNE entrée sidebar pour cylindres ou porte-clichés**
7. Onglets Cylindres + Porte-clichés fonctionnels avec cards aérées + toggle actif coloré
8. Dialog ajout/modif fonctionne, validation inline, microcopie tutoyée
9. État vide accueillant (illustration + CTA)
10. Soft delete : un cylindre désactivé reste en DB, FK des devis historiques préservées
11. Badge "ℹ Petit cylindre" affiché sur cylindres ≤ 80 dents
12. pytest vert (731+ minimum), 0 failed
13. TypeScript `tsc` clean
14. Pas de régression Sprint 1-13 (les 21 cyl actifs compte demo + 3 désactivés intacts)
15. Vercel deploy preview review OK avant merge

---

## 12. Démarrage

```bash
cd ~/projets/devis-flexo
git checkout main && git pull
git checkout -b feat/parametres-parc-cylindres-porte-cliches

# Copier ce brief dans docs/
cp ~/Downloads/Brief_CC_29_Parametres_Parc.md docs/
git add docs/Brief_CC_29_Parametres_Parc.md
git commit -m "docs: ajout brief #29 paramètres parc cylindres + porte-clichés"

# Démarrer commit 1 (modèle PorteCliche)
# Puis suivre l'ordre 1 → 6
# pytest vert à chaque commit
# Pas de push avant validation du responsable produit
```

---

**Brief #29 — ~13h dev solo · 6 commits · 1 PR · UX simple + joyeuse · SACRED préservés**
