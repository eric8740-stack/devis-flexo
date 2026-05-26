import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.routers import (
    admin,
    admin_audit,
    auth,
    catalogue,
    charge_mensuelle,
    client,
    complexe,
    cost,
    cylindre,
    devis,
    entreprise,
    flexocheck,
    fournisseur,
    ia,
    machine,
    matiere,
    onboarding,
    operation_finition,
    optimisation,
    outil_decoupe,
    parametres_options,
    partenaire_st,
    porte_cliche,
    rebobinage,
    tarif_poste,
)
from app.services.cost_engine import CostEngineError

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
# Sprint 3 Lot 3f
app.include_router(cost.router)
# Sprint 5 Lot 5b
app.include_router(outil_decoupe.router)
# Sprint 4 Lot 4b — persistance devis
app.include_router(devis.router)
# Sprint 9 v2 Lot 9c — paramétrabilité tarifs
app.include_router(tarif_poste.router)
# Sprint 12 Lot S12-B — auth multi-tenant
app.include_router(auth.router)
# Sprint 12 Lot S12-D — admin endpoints (Eric only)
app.include_router(admin.router)
# Sprint 13 Lot S13.C — onboarding express (catalogues pré-remplis)
app.include_router(onboarding.router)
# Sprint 13 Lot S13.D — moteur d'optimisation (7 règles + endpoint /calculer)
app.include_router(optimisation.router)
# Sprint 13 Lot S13.E — POC IA analyse photo étiquette (FlexoCheck)
app.include_router(ia.router)
# Sprint 15 Lot 3 — Contrôle BAT IA (FlexoCheck) — 7 endpoints + serve blob
app.include_router(flexocheck.router)
# Sprint 13 post — Paramètres > Options de fabrication (CRUD tenant)
app.include_router(parametres_options.router)
# PR souveraineté commerciale — catalogue matières scopé tenant
app.include_router(matiere.router)
app.include_router(cylindre.router)  # Brief #29 — CRUD parc cylindres
app.include_router(porte_cliche.router)  # Brief #29 — CRUD porte-clichés
# Sprint 16 Lot C — Module Rebobinage (preview + apply/retire sur devis)
app.include_router(rebobinage.router)
# 2026-05-16 TEMPORAIRE — endpoint audit prod seeds. À retirer après diagnostic.
app.include_router(admin_audit.router)


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


@app.exception_handler(CostEngineError)
async def cost_engine_error_handler(request: Request, exc: CostEngineError):
    """Convertit les erreurs métier du moteur de coût en HTTP 422.

    Levée par les calculateurs ou l'orchestrateur quand une donnée requise
    est manquante/incohérente (tarif inconnu, complexe sans grammage,
    type d'encre inexistant, machine sans vitesse_moyenne_m_h, ...).
    """
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/")
def read_root():
    return {"status": "ok", "app": "devis-flexo"}
