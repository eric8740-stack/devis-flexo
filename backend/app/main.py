import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import client, entreprise, fournisseur

app = FastAPI(title="devis-flexo")

# CORS : liste d'origines autorisées, séparées par des virgules.
# Local dev par défaut : http://localhost:3000.
# Prod (Railway) : ajouter l'URL Vercel via la variable CORS_ORIGINS.
# Ex: CORS_ORIGINS="https://devis-flexo.vercel.app,http://localhost:3000"
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entreprise.router)
app.include_router(client.router)
app.include_router(fournisseur.router)


@app.get("/")
def read_root():
    return {"status": "ok", "app": "devis-flexo"}
