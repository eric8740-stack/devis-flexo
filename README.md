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

**9 tables** · **44 endpoints REST** · **69 tests pytest verts**

| Domaine | Tables | Sprint |
|---|---|---|
| Référentiels | `entreprise` (singleton), `client` (20 seedés, 7 segments), `fournisseur` (5 seedés) | S0-S1 |
| Ressources prod | `machine` (3 seedées), `operation_finition` (5), `partenaire_st` (4) | S2 |
| Coûts | `charge_mensuelle` (6 seedées, total 12 650 €/mois) | S2 |
| Catalogue | `complexe` (30 matières adhésives, prix €/m²), `catalogue` (5 produits récurrents) | S2 |

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

## Structure

```
devis-flexo/
├── backend/             # FastAPI
│   ├── app/
│   │   ├── main.py            # CORS + include routers + handler IntegrityError → 409
│   │   ├── db.py              # engine SQLAlchemy + Base + get_db (rollback on error)
│   │   ├── models/            # 9 modèles (S0-S1: entreprise/client/fournisseur · S2: machine/operation_finition/partenaire_st/charge_mensuelle/complexe/catalogue)
│   │   ├── schemas/           # Pydantic v2 Read/Create/Update + enums Literal
│   │   ├── crud/              # logique métier DB
│   │   └── routers/           # 44 endpoints REST
│   ├── alembic/               # migrations versionnées (2 migrations : S0-S1 + S2)
│   ├── seeds/                 # CSV sources (9 fichiers, 79 lignes au total)
│   ├── scripts/               # seed.py (idempotent) + export Excel→CSV
│   ├── tests/                 # pytest (69 tests, autouse fixture seed_db_before_each_test)
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
