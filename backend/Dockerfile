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

# Sprint 4 Lot 4e — deps système weasyprint (génération PDF) :
# cairo + pango + harfbuzz + gdk-pixbuf + fonts liberation (fallback Helvetica/Arial).
# Sans ces libs, weasyprint.HTML.write_pdf() lève OSError au runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

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
