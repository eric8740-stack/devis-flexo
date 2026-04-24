# devis-flexo

[![backend](https://github.com/eric8740-stack/devis-flexo/actions/workflows/backend.yml/badge.svg)](https://github.com/eric8740-stack/devis-flexo/actions/workflows/backend.yml)
[![frontend](https://github.com/eric8740-stack/devis-flexo/actions/workflows/frontend.yml/badge.svg)](https://github.com/eric8740-stack/devis-flexo/actions/workflows/frontend.yml)

Application de devis pour TPE flexographie d'étiquettes.

Projet vitrine d'Eric Paysant (ERP Conseil) — modèle de coût industriel à 7 postes appliqué au métier de la flexo, exposé dans une stack data moderne.

## Production

- **Frontend** : `https://<a renseigner>.vercel.app`
- **Backend** : `https://<a renseigner>.up.railway.app`
- **API docs** : `https://<a renseigner>.up.railway.app/docs`

## Stack

- **Backend** : Python 3.13 + FastAPI + Uvicorn + SQLAlchemy + Alembic + Pydantic + pytest
- **Frontend** : Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui (App Router)
- **Base de données** : SQLite (dev local) → PostgreSQL (prod Railway)
- **Déploiement** : Vercel (front) + Railway (back + Postgres)
- **CI** : GitHub Actions (pytest + npm build/lint)

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
│   │   ├── main.py            # CORS + include routers
│   │   ├── db.py              # engine SQLAlchemy + Base + get_db
│   │   ├── models/            # 3 modèles (entreprise, client, fournisseur)
│   │   ├── schemas/           # Pydantic Read/Create/Update
│   │   ├── crud/              # logique métier DB
│   │   └── routers/           # endpoints REST
│   ├── alembic/               # migrations versionnées
│   ├── seeds/                 # CSV sources (entreprise, client, fournisseur)
│   ├── scripts/               # seed.py + export Excel→CSV
│   ├── tests/                 # pytest (25 tests)
│   ├── Dockerfile             # image Railway
│   └── requirements.txt
├── frontend/            # Next.js 14
│   └── src/
│       ├── app/               # routes (parametres, clients, fournisseurs)
│       ├── components/        # DataTable, forms, Header, ui shadcn
│       └── lib/api.ts         # helpers fetch typés
├── .github/workflows/   # CI backend + frontend
└── README.md
```
