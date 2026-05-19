"""Tests métier critiques brief #28 (point ajouté par Eric).

Couvre :
  - Multi-laize même cylindre : 2 lots distincts du MÊME cylindre avec
    variantes laize/poses différentes peuvent coexister dans un devis.
  - Matière indépendante par lot : chaque lot a SA matière, pas de
    matière globale au niveau devis (LOT 1 PP, LOT 2 PET → OK).

Ces 2 propriétés sont fondamentales pour le workflow multi-lots flexo et
doivent rester verrouillées par tests dédiés.
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis, LotProduction
from tests.test_lot_production_model import (
    _get_fk_ids,
    _onboard_if_needed,
)

client = TestClient(app)


def _payload_devis_base() -> dict:
    return {
        "payload_input": {
            "machine_id": 1,
            "format_etiquette_hauteur_mm": 40,
            "format_etiquette_largeur_mm": 60,
            "mode_calcul": "manuel",
        },
        "payload_output": {"prix_vente_ht_eur": "0", "mode": "manuel"},
    }


def test_multi_laize_meme_cyl_cochables_simultanement():
    """Un user peut créer un devis avec 2 lots du MÊME cylindre mais
    variantes laize différentes (ex Cyl 104 dents en 2×3 ET en 1×3).
    Les lots sont distincts par (cylindre, nb_poses_laize, nb_poses_dev)
    et persistés indépendamment.
    """
    _onboard_if_needed()
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()
        cyl_id, mach_id, mat_id = _get_fk_ids(db)

    payload = _payload_devis_base()
    payload["payload_input"]["machine_id"] = mach_id
    payload["quantite_totale"] = 8000
    # Brief #28 critique : 2 lots du MÊME cylindre, variantes différentes.
    payload["lots"] = [
        {
            "cylindre_id": cyl_id,
            "machine_id": mach_id,
            "nb_poses_dev": 3,
            "nb_poses_laize": 2,
            "sens_enroulement": 1,
            "quantite": 5000,
            "matiere_id": mat_id,
        },
        {
            "cylindre_id": cyl_id,  # MÊME cyl
            "machine_id": mach_id,
            "nb_poses_dev": 3,
            "nb_poses_laize": 1,  # variante laize DIFFÉRENTE
            "sens_enroulement": 1,
            "quantite": 3000,
            "matiere_id": mat_id,
        },
    ]
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["lots_production"]) == 2
    # Les 2 lots partagent cylindre_id mais nb_poses_laize diffèrent.
    cyl_ids = {lot["cylindre_id"] for lot in body["lots_production"]}
    nb_poses_laize_vals = [lot["nb_poses_laize"] for lot in body["lots_production"]]
    assert cyl_ids == {cyl_id}, "Les 2 lots doivent référencer le même cylindre."
    assert sorted(nb_poses_laize_vals) == [1, 2], (
        "Les 2 lots doivent avoir des variantes laize différentes (1 et 2)."
    )

    # Vérif persistance DB
    with SessionLocal() as db:
        lots = db.query(LotProduction).filter_by(devis_id=body["id"]).all()
        assert len(lots) == 2
        assert {lot.cylindre_id for lot in lots} == {cyl_id}


def test_matiere_indep_par_lot():
    """Chaque lot a SA matière indépendamment des autres (FK NOT NULL par
    lot, pas de matière "globale" au niveau devis).

    On crée un devis avec 2 lots dont les matieres_id sont DIFFÉRENTS et
    on vérifie que chaque lot porte bien sa propre matière en DB.
    """
    _onboard_if_needed()
    # On s'assure d'avoir au moins 2 matières en DB pour ce test.
    with SessionLocal() as db:
        from app.models import Matiere
        existantes = db.query(Matiere).filter_by(entreprise_id=1).all()
        if len(existantes) < 2:
            db.add(
                Matiere(
                    entreprise_id=1,
                    code="test_pet_blanc_50",
                    libelle="Test PET blanc 50µ",
                    actif=True,
                )
            )
            db.commit()
        mat_a, mat_b = (
            db.query(Matiere).filter_by(entreprise_id=1).limit(2).all()
        )
        mat_a_id, mat_b_id = mat_a.id, mat_b.id
        assert mat_a_id != mat_b_id
        db.query(Devis).delete()
        db.commit()
        cyl_id, mach_id, _ = _get_fk_ids(db)

    payload = _payload_devis_base()
    payload["payload_input"]["machine_id"] = mach_id
    payload["quantite_totale"] = 10000
    payload["lots"] = [
        {
            "cylindre_id": cyl_id,
            "machine_id": mach_id,
            "nb_poses_dev": 2,
            "nb_poses_laize": 3,
            "sens_enroulement": 1,
            "quantite": 6000,
            "matiere_id": mat_a_id,
        },
        {
            "cylindre_id": cyl_id,
            "machine_id": mach_id,
            "nb_poses_dev": 2,
            "nb_poses_laize": 3,
            "sens_enroulement": 1,
            "quantite": 4000,
            "matiere_id": mat_b_id,  # matière DIFFÉRENTE
        },
    ]
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    matieres_par_lot = sorted([lot["matiere_id"] for lot in body["lots_production"]])
    assert matieres_par_lot == sorted([mat_a_id, mat_b_id]), (
        f"Chaque lot doit conserver SA matière indépendamment. "
        f"Attendu {sorted([mat_a_id, mat_b_id])}, obtenu {matieres_par_lot}."
    )
