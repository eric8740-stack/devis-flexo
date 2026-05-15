"""Tests smoke des 2 tables traçabilité Sprint 13 Lot S13.F.

Vérifie pour chaque table :
  - La table est créée (CREATE TABLE de la migration tient)
  - Les contraintes essentielles tiennent (NOT NULL, types Decimal/JSON,
    FK CASCADE / SET NULL)
  - L'objet se persiste et se relit avec les mêmes valeurs

Pas de tests de workflow ici (workflows API + génération PDF + IA
= Sprint 14/15), juste l'intégrité du schéma.

Multi-tenancy = un test global qui vérifie que la suppression d'une
entreprise CASCADE bien sur rapport + photos rattachés.
"""
from datetime import datetime, timezone
from decimal import Decimal

from app.db import SessionLocal
from app.models import (
    PHOTO_TYPE_ETAPES,
    Entreprise,
    PhotoProduction,
    RapportQualiteProduction,
)
from app.models.devis import Devis
from app.models.machine import Machine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_entreprise_for_test(entreprise_id: int, label: str) -> int:
    """Crée (idempotent) une entreprise dédiée test. Renvoie son id.
    On n'utilise PAS l'entreprise demo (id=1) pour éviter de polluer
    les invariants sacrés EXACT.
    """
    db = SessionLocal()
    try:
        existing = db.query(Entreprise).filter(Entreprise.id == entreprise_id).first()
        if existing is not None:
            return existing.id
        ent = Entreprise(
            id=entreprise_id,
            raison_sociale=f"Test S13.F {label}",
            siret=f"{entreprise_id:014d}",
            email=f"test-{entreprise_id}@s13f.fr",
            is_demo=False,
        )
        db.add(ent)
        db.commit()
        return ent.id
    finally:
        db.close()


def _ensure_devis_for_test(entreprise_id: int, numero: str) -> int:
    """Crée (idempotent) un devis minimal pour satisfaire la FK NOT NULL.
    Réutilise machine id=1 (Mark Andy P5, présente après seed).
    """
    db = SessionLocal()
    try:
        existing = db.query(Devis).filter(Devis.numero == numero).first()
        if existing is not None:
            return existing.id
        # Sanity : machine 1 existe (seedée depuis machine.csv)
        machine = db.query(Machine).filter(Machine.id == 1).first()
        assert machine is not None, "Machine id=1 introuvable — seed cassé ?"
        devis = Devis(
            entreprise_id=entreprise_id,
            numero=numero,
            payload_input={"placeholder": True},
            payload_output={"placeholder": True},
            mode_calcul="V1a",
            ht_total_eur=Decimal("0.00"),
            format_h_mm=Decimal("100.00"),
            format_l_mm=Decimal("100.00"),
            machine_id=1,
        )
        db.add(devis)
        db.commit()
        return devis.id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tests rapport_qualite_production
# ---------------------------------------------------------------------------


def test_rapport_qualite_production_minimal():
    ent_id = _ensure_entreprise_for_test(200, "rapport-mini")
    devis_id = _ensure_devis_for_test(ent_id, "DEV-S13F-MINI-001")
    db = SessionLocal()
    try:
        rap = RapportQualiteProduction(
            entreprise_id=ent_id,
            devis_id=devis_id,
            statut="en_construction",
        )
        db.add(rap)
        db.commit()
        db.refresh(rap)
        assert rap.id is not None
        assert rap.statut == "en_construction"
        # Défaut serveur : 5 ans de conservation
        assert rap.duree_conservation_ans == 5
        assert rap.created_at is not None
        # Tous les champs nullables le sont bien
        assert rap.pdf_url is None
        assert rap.pdf_hash_sha256 is None
        assert rap.duree_totale_chaine_min is None
    finally:
        db.close()


def test_rapport_qualite_production_full_fields_roundtrip():
    """Crée un rapport avec un maximum de champs renseignés et vérifie
    le round-trip (write → refresh → assert valeurs identiques).
    """
    ent_id = _ensure_entreprise_for_test(201, "rapport-full")
    devis_id = _ensure_devis_for_test(ent_id, "DEV-S13F-FULL-001")
    db = SessionLocal()
    try:
        debut = datetime(2026, 5, 15, 8, 30, tzinfo=timezone.utc)
        fin = datetime(2026, 5, 15, 13, 22, tzinfo=timezone.utc)
        rap = RapportQualiteProduction(
            entreprise_id=ent_id,
            devis_id=devis_id,
            statut="finalise",
            pdf_url="https://blob.vercel-storage.com/rapport-xyz.pdf",
            pdf_genere_at=fin,
            pdf_hash_sha256="a" * 64,
            production_debut_at=debut,
            production_fin_at=fin,
            duree_production_min=292,
            duree_estimee_min=270,
            ecart_temps_estime_pct=Decimal("8.15"),
            mode_diffusion="lien_validation",
            lien_public_token="tok_" + "x" * 80,
            nb_controles_total=12,
            nb_ecarts_majeurs=0,
            nb_ecarts_mineurs=2,
            nb_retirages_necessaires=0,
            score_moyen_conformite=Decimal("97.50"),
            validation_finale="valide",
            duree_conservation_ans=10,
            # Extension par étape
            impression_debut_at=debut,
            duree_impression_min=148,
            duree_finition_min=45,
            duree_rebobinage_min=72,
            duree_conditionnement_min=27,
            duree_totale_chaine_min=292,
            nb_palettes_total=3,
            nb_palettes_validees=3,
            etape_la_plus_longue="impression",
        )
        db.add(rap)
        db.commit()
        db.refresh(rap)

        assert rap.statut == "finalise"
        assert rap.pdf_hash_sha256 == "a" * 64
        assert rap.duree_production_min == 292
        assert rap.ecart_temps_estime_pct == Decimal("8.15")
        assert rap.score_moyen_conformite == Decimal("97.50")
        assert rap.duree_conservation_ans == 10
        assert rap.nb_palettes_validees == 3
        assert rap.etape_la_plus_longue == "impression"
        # Champs jamais renseignés restent NULL
        assert rap.archive_at is None
        assert rap.email_client_envoye_at is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tests photo_production
# ---------------------------------------------------------------------------


def test_photo_production_type_etape_and_json_fields():
    """Création photo standard + vérif JSON ecarts_detectes round-trip."""
    ent_id = _ensure_entreprise_for_test(202, "photo-controle")
    devis_id = _ensure_devis_for_test(ent_id, "DEV-S13F-PHOTO-001")
    db = SessionLocal()
    try:
        ts = datetime(2026, 5, 15, 9, 12, tzinfo=timezone.utc)
        photo = PhotoProduction(
            entreprise_id=ent_id,
            devis_id=devis_id,
            rapport_qualite_id=None,  # peut être nulle au début
            type_etape="controle_continu",
            photo_url="https://blob.vercel-storage.com/p123.jpg",
            photo_timestamp=ts,
            reference_url="https://blob.vercel-storage.com/bat-ref.pdf",
            resultats_analyse_ia={
                "couleurs_ok": True,
                "registre_max_mm": 0.12,
                "score": 98.4,
            },
            score_conformite=Decimal("98.40"),
            ecarts_detectes=[
                {"type": "registre", "valeur_mm": 0.12, "tolerance_mm": 0.15},
            ],
            decision_finale="valide",
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
        assert photo.id is not None
        assert photo.type_etape == "controle_continu"
        assert photo.type_etape in PHOTO_TYPE_ETAPES
        assert photo.score_conformite == Decimal("98.40")
        assert photo.resultats_analyse_ia["registre_max_mm"] == 0.12
        assert photo.ecarts_detectes[0]["type"] == "registre"
        assert photo.decision_finale == "valide"
    finally:
        db.close()


def test_photo_production_palette_fields():
    """Une photo type palette utilise les champs numero_palette / poids /
    etiquette_palette_data (JSON) — round-trip vérifié.
    """
    ent_id = _ensure_entreprise_for_test(203, "photo-palette")
    devis_id = _ensure_devis_for_test(ent_id, "DEV-S13F-PALETTE-001")
    db = SessionLocal()
    try:
        ts = datetime(2026, 5, 15, 13, 18, tzinfo=timezone.utc)
        photo = PhotoProduction(
            entreprise_id=ent_id,
            devis_id=devis_id,
            type_etape="palette_face",
            photo_url="https://blob.vercel-storage.com/palette-2.jpg",
            photo_timestamp=ts,
            numero_palette=2,
            nb_bobines_palette=18,
            poids_palette_kg=Decimal("412.50"),
            etiquette_palette_data={
                "n_lot": "LOT-2026-05-15-A",
                "sscc": "001234567890123456",
                "ean": "3700000000017",
                "date": "2026-05-15",
            },
            decision_finale="valide",
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
        assert photo.numero_palette == 2
        assert photo.nb_bobines_palette == 18
        assert photo.poids_palette_kg == Decimal("412.50")
        assert photo.etiquette_palette_data["sscc"] == "001234567890123456"
        # operateur_id et rapport_qualite_id restent NULL — valides
        assert photo.operateur_id is None
        assert photo.rapport_qualite_id is None
    finally:
        db.close()


def test_photo_rattachee_a_rapport_qualite():
    """Une photo rattachée à un rapport (FK rapport_qualite_id NOT NULL).
    Vérifie aussi le SET NULL au drop du rapport.
    """
    ent_id = _ensure_entreprise_for_test(204, "photo-lien-rapport")
    devis_id = _ensure_devis_for_test(ent_id, "DEV-S13F-LIEN-001")
    db = SessionLocal()
    try:
        rap = RapportQualiteProduction(
            entreprise_id=ent_id,
            devis_id=devis_id,
            statut="finalise",
        )
        db.add(rap)
        db.commit()
        db.refresh(rap)

        photo = PhotoProduction(
            entreprise_id=ent_id,
            devis_id=devis_id,
            rapport_qualite_id=rap.id,
            type_etape="bobine_finie",
            photo_url="https://blob.vercel-storage.com/bobine.jpg",
            photo_timestamp=datetime.now(timezone.utc),
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
        photo_id = photo.id
        assert photo.rapport_qualite_id == rap.id

        # Drop du rapport → la photo doit survivre avec rapport_qualite_id=NULL
        db.delete(rap)
        db.commit()
        photo_reloaded = (
            db.query(PhotoProduction).filter(PhotoProduction.id == photo_id).first()
        )
        assert photo_reloaded is not None
        assert photo_reloaded.rapport_qualite_id is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Test global multi-tenant : CASCADE entreprise → rapport + photos
# ---------------------------------------------------------------------------


def test_cascade_delete_entreprise_removes_rapports_and_photos():
    """Suppression d'une entreprise → CASCADE sur rapport_qualite_production
    + photo_production (les deux ont entreprise_id NOT NULL FK CASCADE).

    Le devis est lui-même supprimé par le CASCADE de Sprint 12, donc on
    n'a pas besoin de le supprimer explicitement.
    """
    db = SessionLocal()
    try:
        # Cleanup idempotent : seed re-seede l'entreprise demo + reset
        # tables existantes, mais ne touche PAS aux 2 nouvelles tables
        # S13.F. Un run précédent peut avoir laissé une entreprise avec
        # siret 99999999000206 — on la supprime au début pour repartir
        # propre.
        prev = (
            db.query(Entreprise).filter(Entreprise.siret == "99999999000206").first()
        )
        if prev is not None:
            db.delete(prev)
            db.commit()

        ent = Entreprise(
            raison_sociale="Cascade Test S13.F",
            siret="99999999000206",
            email="cascade@s13f.fr",
            is_demo=False,
        )
        db.add(ent)
        db.commit()
        ent_id = ent.id

        # Devis ad hoc pour rattachement FK
        machine = db.query(Machine).filter(Machine.id == 1).first()
        assert machine is not None
        devis = Devis(
            entreprise_id=ent_id,
            numero="DEV-S13F-CASCADE-001",
            payload_input={"placeholder": True},
            payload_output={"placeholder": True},
            mode_calcul="V1a",
            ht_total_eur=Decimal("0.00"),
            format_h_mm=Decimal("100.00"),
            format_l_mm=Decimal("100.00"),
            machine_id=1,
        )
        db.add(devis)
        db.commit()

        rap = RapportQualiteProduction(
            entreprise_id=ent_id, devis_id=devis.id, statut="finalise"
        )
        db.add(rap)
        db.commit()

        photo = PhotoProduction(
            entreprise_id=ent_id,
            devis_id=devis.id,
            rapport_qualite_id=rap.id,
            type_etape="1er_tirage",
            photo_url="https://blob.vercel-storage.com/cascade.jpg",
            photo_timestamp=datetime.now(timezone.utc),
        )
        db.add(photo)
        db.commit()

        # Sanity
        assert (
            db.query(RapportQualiteProduction)
            .filter_by(entreprise_id=ent_id)
            .count()
            == 1
        )
        assert (
            db.query(PhotoProduction).filter_by(entreprise_id=ent_id).count() == 1
        )

        # Suppression entreprise → CASCADE
        db.delete(ent)
        db.commit()

        assert (
            db.query(RapportQualiteProduction)
            .filter_by(entreprise_id=ent_id)
            .count()
            == 0
        )
        assert (
            db.query(PhotoProduction).filter_by(entreprise_id=ent_id).count() == 0
        )
    finally:
        db.close()
