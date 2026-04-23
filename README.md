# devis-flexo

Application de devis pour TPE flexographie d'étiquettes.

Projet vitrine d'Eric Paysant (ERP Conseil) — modèle de coût industriel à 7 postes appliqué au métier de la flexo, exposé dans une stack data moderne.

## Stack

- **Backend** : Python 3.13 + FastAPI + Uvicorn + SQLAlchemy + Alembic + Pydantic + pytest
- **Frontend** : Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui (App Router)
- **Base de données** : SQLite (dev local) → PostgreSQL (prod)

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

## Structure

```
devis-flexo/
├── backend/             # FastAPI
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py      # endpoint GET /
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_main.py
│   ├── requirements.txt
│   ├── pyproject.toml   # config pytest
│   └── .env.example
├── frontend/            # Next.js 14
│   └── src/app/
│       └── page.tsx
├── .gitignore
└── README.md
```
