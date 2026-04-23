from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import entreprise

app = FastAPI(title="devis-flexo")

# CORS : le frontend Next.js tourne sur :3000 et appelle l'API sur :8000.
# Sans cette autorisation, le navigateur bloque les requêtes cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entreprise.router)


@app.get("/")
def read_root():
    return {"status": "ok", "app": "devis-flexo"}
