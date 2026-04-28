# devis-flexo

[![backend](https://github.com/eric8740-stack/devis-flexo/actions/workflows/backend.yml/badge.svg)](https://github.com/eric8740-stack/devis-flexo/actions/workflows/backend.yml)
[![frontend](https://github.com/eric8740-stack/devis-flexo/actions/workflows/frontend.yml/badge.svg)](https://github.com/eric8740-stack/devis-flexo/actions/workflows/frontend.yml)

## 🚀 Démo en ligne

- **Application** : https://devis-flexo.vercel.app
- **API (Swagger)** : https://devis-flexo-production.up.railway.app/docs
- **Healthcheck backend** : https://devis-flexo-production.up.railway.app

Application de devis pour TPE flexographie d'étiquettes.

Projet vitrine d'Eric Paysant (ERP Conseil) — modèle de coût industriel à 7 postes appliqué au métier de la flexo, exposé dans une stack data moderne.

## Production

- **Frontend** : https://devis-flexo.vercel.app
- **Backend** : https://devis-flexo-production.up.railway.app
- **API docs** : https://devis-flexo-production.up.railway.app/docs

## Stack

- **Backend** : Python 3.13 + FastAPI + Uvicorn + SQLAlchemy + Alembic + Pydantic + pytest
- **Frontend** : Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui (App Router)
- **Base de données** : SQLite (dev local) → PostgreSQL (prod Railway)
- **Déploiement** : Vercel (front) + Railway (back + Postgres)
- **CI** : GitHub Actions (pytest + npm build/lint)

## Périmètre actuel

**14 tables** · **45 endpoints REST** · **136 tests pytest verts**

| Domaine | Tables | Sprint |
|---|---|---|
| Référentiels | `entreprise` (singleton), `client` (20 seedés, 7 segments), `fournisseur` (5 seedés) | S0-S1 |
| Ressources prod | `machine` (3 seedées), `operation_finition` (5), `partenaire_st` (4) | S2 |
| Coûts | `charge_mensuelle` (6 seedées, total 12 650 €/mois) | S2 |
| Catalogue | `complexe` (31 matières adhésives, prix €/m²), `catalogue` (5 produits récurrents) | S2 + S3 |
| Moteur de coût v2 | `tarif_poste` (7 clés symboliques), `tarif_encre` (5 types), `temps_operation_standard` (15 ops), `correspondance_laize_metrage` (33 lignes), `charge_machine_mensuelle` (1 exemple, hook `before_insert`) | S3 |

## Démarrage local

### Backend (port 8000)

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Vérifier : http://localhost:8000/ doit retourner `{"status":"ok","app":"devis-flexo"}`.

### Frontend (port 3000)

Dans un autre terminal :

```bash
cd frontend
npm install
npm run dev
```

Vérifier : http://localhost:3000 affiche la page d'accueil.

## Tests

```bash
cd backend
pytest
```

## Variables d'environnement

### Backend (`.env` ou env Railway)

| Variable | Dev | Prod (Railway) |
|---|---|---|
| `DATABASE_URL` | non défini → SQLite local `devis_flexo.db` | `postgresql://...` (auto via add-on Postgres) |
| `CORS_ORIGINS` | non défini → `http://localhost:3000` | URL Vercel + localhost (séparés par `,`) |
| `PORT` | non défini → 8000 | injecté par Railway |

### Frontend (`.env.local` ou env Vercel)

| Variable | Dev | Prod (Vercel) |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | non défini → `http://localhost:8000` | URL backend Railway |

## Déploiement et re-seed Railway

Le backend Railway redéploie automatiquement à chaque `push` sur `main` :
le `Dockerfile` exécute `alembic upgrade head` au démarrage du conteneur,
donc **le schéma Postgres est toujours à jour**. En revanche, **les
données seedées (référentiels, tarifs, complexes, etc.) ne sont jamais
re-exécutées automatiquement** — il faut lancer `scripts/seed.py`
manuellement contre la prod après chaque modification d'un CSV ou ajout
de nouvelles tables seedées.

### Quand re-seeder ?

- ✅ Après une migration de schéma sur `main` qui ajoute / supprime des
  tables seedées (ex. ajout des 5 tables paramétriques moteur v2 en S3)
- ✅ Après modification d'un seed CSV en local (ex. ajout d'une ligne dans
  `complexe.csv`, ajustement d'un prix dans `tarif_poste.csv`)
- ❌ Pas après chaque commit. Uniquement quand les seeds ou le schéma
  changent.

### Pré-requis (à vérifier UNE fois)

1. **Public Networking activé** sur le service Postgres Railway :
   dashboard Railway → service `Postgres` → onglet `Settings` → `Public
   Networking` → vérifier que `TCP Proxy` est activé. Si pas, l'activer.
   Railway génère alors un domaine public type `crossover.proxy.rlwy.net`
   et la variable `DATABASE_PUBLIC_URL`.
2. **Venv backend activé** localement (`backend/venv`).

### Procédure de re-seed (PowerShell, Windows)

```powershell
# 1. Récupérer DATABASE_PUBLIC_URL depuis Railway dashboard :
#    service "Postgres" → onglet "Variables" → DATABASE_PUBLIC_URL
#    Format : postgresql://postgres:XXX@crossover.proxy.rlwy.net:PORT/railway

# 2. Activer le venv backend
cd backend
.\venv\Scripts\Activate.ps1

# 3. Pointer la variable DATABASE_URL sur la prod
#    (guillemets simples obligatoires : le password contient $/%/&)
$env:DATABASE_URL = 'postgresql://postgres:XXX@crossover.proxy.rlwy.net:PORT/railway?sslmode=require'

# 4. Lancer le seed (DELETE descendant + INSERT ascendant, idempotent)
python -m scripts.seed

# 5. ⚠️ ÉTAPE CRITIQUE — nettoyer la variable d'environnement
#    Sans ça, les prochains `python -m scripts.seed` locaux pointeraient
#    encore sur la prod et écraseraient les données par erreur.
Remove-Item Env:DATABASE_URL
```

> **⚠️ Sécurité — étape 5 obligatoire**
>
> Si vous oubliez `Remove-Item Env:DATABASE_URL` à l'étape 5, **toute
> commande `python` lancée dans ce terminal pointera encore sur la prod**
> jusqu'à fermeture du terminal. Si vous lancez `pytest` ou `python -m
> scripts.seed` à nouveau "pour tester en local", vous écraserez la prod.
>
> Bonne pratique : ouvrir un nouveau terminal après le re-seed, ou
> vérifier `echo $env:DATABASE_URL` qui doit être vide.

> **🔐 Mot de passe Postgres**
>
> Le mot de passe `XXX` se récupère **uniquement** sur Railway dashboard
> (variable `DATABASE_PUBLIC_URL`). **Jamais commité dans le repo** : ce
> projet est public, des bots scannent GitHub pour les credentials leakés
> (exploitation en moins de 5 minutes en moyenne).

### Vérification post-seed (optionnel mais recommandé)

```powershell
# Re-pointer temporairement (oui, on refait le set + remove)
$env:DATABASE_URL = 'postgresql://postgres:XXX@crossover.proxy.rlwy.net:PORT/railway?sslmode=require'

python -c "from app.db import SessionLocal; from app.models import Complexe, TarifPoste, Machine; from sqlalchemy import func; s = SessionLocal(); print('complexes:', s.query(func.count(Complexe.id)).scalar()); print('tarifs_poste:', s.query(func.count(TarifPoste.id)).scalar()); m = s.query(Machine).filter(Machine.id == 1).first(); print(f'Mark Andy P5 calage = {m.duree_calage_h} h')"

Remove-Item Env:DATABASE_URL
```

Sortie attendue (S3 Lot 3f) :
```
complexes: 31
tarifs_poste: 7
Mark Andy P5 calage = 1.00 h
```

### Test du moteur de coût en prod

Après re-seed, valider via Swagger sur l'URL Railway
(`/docs` → `POST /api/cost/calculer`) avec le payload du cas-test médian
V1 (cf. `tests/test_cost_engine_benchmark.py`). Total HT attendu :
**1449.09 €**.

## Structure

```
devis-flexo/
├── backend/             # FastAPI
│   ├── app/
│   │   ├── main.py            # CORS + include routers + handlers IntegrityError → 409, CostEngineError → 422
│   │   ├── db.py              # engine SQLAlchemy + Base + get_db (rollback on error)
│   │   ├── models/            # 14 modèles (S0-S1: 3 référentiels · S2: 6 tables ressources/coûts/catalogue · S3: 5 tables moteur de coût v2)
│   │   ├── schemas/           # Pydantic v2 Read/Create/Update + enums Literal + DevisInput/Output + PosteResult
│   │   ├── crud/              # logique métier DB (incluant get_by_cle, get_by_type_encre)
│   │   ├── routers/           # 45 endpoints REST (44 CRUD + POST /api/cost/calculer)
│   │   └── services/cost_engine/  # 7 calculateurs poste_X_xxx.py + orchestrator MoteurDevis (S3 Lot 3d)
│   ├── alembic/               # migrations versionnées (6 migrations : S0-S1 + S2 + 4 × S3)
│   ├── seeds/                 # CSV sources (14 fichiers, 141 lignes au total)
│   ├── scripts/               # seed.py (idempotent) + export Excel→CSV
│   ├── tests/                 # pytest (136 tests, autouse fixture seed_db_before_each_test)
│   ├── Dockerfile             # image Railway
│   └── requirements.txt
├── frontend/            # Next.js 14
│   └── src/
│       ├── app/               # 22 routes (parametres + 8 entités × 3 pages list/[id]/nouveau)
│       ├── components/        # DataTable + 7 forms + Header + ui shadcn
│       └── lib/api.ts         # helpers fetch typés end-to-end
├── .github/workflows/   # CI backend (pytest + alembic upgrade) + frontend (build + lint)
└── README.md
```
