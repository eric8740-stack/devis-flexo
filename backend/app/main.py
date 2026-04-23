from fastapi import FastAPI

app = FastAPI(title="devis-flexo")


@app.get("/")
def read_root():
    return {"status": "ok", "app": "devis-flexo"}
