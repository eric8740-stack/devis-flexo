import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.routers import (
    catalogue,
    charge_mensuelle,
    client,
    complexe,
    entreprise,
    fournisseur,
    machine,
    operation_finition,
    partenaire_st,
)

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

# Sprint 0-1
app.include_router(entreprise.router)
app.include_router(client.router)
app.include_router(fournisseur.router)
# Sprint 2
app.include_router(machine.router)
app.include_router(operation_finition.router)
app.include_router(partenaire_st.router)
app.include_router(charge_mensuelle.router)
app.include_router(complexe.router)
app.include_router(catalogue.router)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Convertit les violations de contraintes DB (UNIQUE, FK, NOT NULL)
    en réponse HTTP 409 Conflict propre — évite les 500 bruts côté client."""
    return JSONResponse(
        status_code=409,
        content={
            "detail": (
                "Violation de contrainte d'intégrité "
                "(doublon, clé étrangère invalide ou champ obligatoire manquant)."
            )
        },
    )


@app.get("/")
def read_root():
    return {"status": "ok", "app": "devis-flexo"}
