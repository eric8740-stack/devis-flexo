"""Tests smoke du modèle AnalysePhotoEtiquette Sprint 13 S13.E.2.

Vérifie :
  - Création + relecture (JSON column round-trip)
  - Multi-tenant CASCADE sur entreprise
  - FK user.id et devis.id SET NULL (analyse survit aux suppressions)
"""
from datetime import datetime
from decimal import Decimal

from app.db import SessionLocal
from app.models import (
    AnalysePhotoEtiquette,
    Devis,
    Entreprise,
)
from app.models.machine import Machine


def _ensure_entreprise(entreprise_id: int, label: str) -> int:
    db = SessionLocal()
    try:
        ent = db.query(Entreprise).filter_by(id=entreprise_id).first()
        if ent is not None:
            return ent.id
        ent = Entreprise(
            id=entreprise_id,
            raison_sociale=f"Test S13.E {label}",
            siret=f"{entreprise_id:014d}",
            email=f"test-s13e-{entreprise_id}@test.fr",
            is_demo=False,
        )
        db.add(ent)
        db.commit()
        return ent.id
    finally:
        db.close()


def test_create_and_read_minimal():
    ent_id = _ensure_entreprise(300, "min")
    db = SessionLocal()
    try:
        # resultats_ia = JSON typique renvoyé par Claude
        resultats = {
            "couleurs_detectees": [
                {
                    "rgb_approximatif": "#A23B45",
                    "pantone_proche_estime": "186 C",
                    "surface_pct": 35,
                },
            ],
            "nombre_couleurs_distinctes": 4,
            "couleurs_min_technique": 4,
            "couleurs_max_technique": 5,
            "techniques_impression_estimees": ["CMJN"],
            "matiere_estimee": {
                "type": "papier",
                "couleur": "blanc",
                "finition_apparente": "mat",
            },
            "finitions_visibles": [],
            "presence_blanc_opaque": False,
            "niveau_confiance": "moyen",
            "limites_analyse": ["éclairage smartphone"],
        }
        analyse = AnalysePhotoEtiquette(
            entreprise_id=ent_id,
            resultats_ia=resultats,
            niveau_confiance="moyen",
            nombre_couleurs_distinctes=4,
            model_utilise="claude-sonnet-4-6",
            photo_mime_type="image/jpeg",
        )
        db.add(analyse)
        db.commit()
        db.refresh(analyse)
        assert analyse.id is not None
        assert isinstance(analyse.created_at, datetime)
        # Round-trip JSON
        assert (
            analyse.resultats_ia["matiere_estimee"]["type"] == "papier"
        )
        assert analyse.resultats_ia["couleurs_detectees"][0]["surface_pct"] == 35
        # Champs nullables OK
        assert analyse.user_id is None
        assert analyse.devis_id is None
        assert analyse.photo_url is None
        assert analyse.erreur is None
    finally:
        db.close()


def test_devis_id_set_null_quand_devis_supprime():
    """FK devis_id avec ON DELETE SET NULL : si le devis associé est
    supprimé, l'analyse survit avec devis_id=NULL."""
    ent_id = _ensure_entreprise(301, "fk")
    db = SessionLocal()
    try:
        # Crée un devis minimal (machine 1 est seedée)
        machine = db.query(Machine).filter_by(id=1).first()
        assert machine is not None
        devis = Devis(
            entreprise_id=ent_id,
            numero="DEV-S13E-FK-001",
            payload_input={"placeholder": True},
            payload_output={"placeholder": True},
            mode_calcul="V1a",
            ht_total_eur=Decimal("0.00"),
            format_h_mm=Decimal("50"),
            format_l_mm=Decimal("50"),
            machine_id=1,
        )
        db.add(devis)
        db.commit()

        analyse = AnalysePhotoEtiquette(
            entreprise_id=ent_id,
            devis_id=devis.id,
            resultats_ia={"niveau_confiance": "haut"},
        )
        db.add(analyse)
        db.commit()
        db.refresh(analyse)
        analyse_id = analyse.id
        assert analyse.devis_id == devis.id

        # Suppression du devis → analyse survit avec devis_id=NULL
        db.delete(devis)
        db.commit()
        relu = (
            db.query(AnalysePhotoEtiquette)
            .filter_by(id=analyse_id)
            .first()
        )
        assert relu is not None
        assert relu.devis_id is None
    finally:
        db.close()


def test_cascade_delete_entreprise_supprime_analyses():
    """Suppression entreprise → CASCADE sur analyses (multi-tenant cleanup)."""
    db = SessionLocal()
    try:
        # Cleanup idempotent d'un éventuel run précédent
        prev = (
            db.query(Entreprise).filter_by(siret="99999900000513").first()
        )
        if prev is not None:
            db.delete(prev)
            db.commit()

        ent = Entreprise(
            raison_sociale="Cascade S13.E",
            siret="99999900000513",
            email="cascade-s13e@test.fr",
            is_demo=False,
        )
        db.add(ent)
        db.commit()
        ent_id = ent.id

        db.add_all([
            AnalysePhotoEtiquette(
                entreprise_id=ent_id, resultats_ia={"niveau_confiance": "moyen"}
            ),
            AnalysePhotoEtiquette(
                entreprise_id=ent_id, resultats_ia={"niveau_confiance": "haut"}
            ),
        ])
        db.commit()
        assert (
            db.query(AnalysePhotoEtiquette).filter_by(entreprise_id=ent_id).count()
            == 2
        )

        db.delete(ent)
        db.commit()
        assert (
            db.query(AnalysePhotoEtiquette).filter_by(entreprise_id=ent_id).count()
            == 0
        )
    finally:
        db.close()
