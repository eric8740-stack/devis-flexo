# Image backend devis-flexo pour Railway.
# - Python 3.13 slim (image officielle, ~50 Mo)
# - install des deps en couche séparée pour profiter du cache Docker
# - au démarrage : alembic upgrade head puis uvicorn sur $PORT (Railway impose la variable)

FROM python:3.13-slim

# Évite les fichiers .pyc et bufferise les logs Python (utile pour Railway logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Layer cache : install des deps avant de copier le code
COPY requirements.txt .
RUN pip install -r requirements.txt

# Code applicatif (.dockerignore exclut venv, __pycache__, *.db, etc.)
COPY . .

# Railway fournit $PORT ; fallback 8000 pour `docker run` local
ENV PORT=8000
EXPOSE 8000

# `sh -c` nécessaire pour expansion de ${PORT}.
# alembic upgrade head s'exécute à chaque démarrage : idempotent (no-op si à jour).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
