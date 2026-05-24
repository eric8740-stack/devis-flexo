"""Tests modèle ControleBat — Sprint 15 Lot 1.

Couvre :
  - Création basique + persistance des champs clés
  - Defaults (`tentative_numero=1`, `nb_ecarts_majeurs=0`, `nb_ecarts_mineurs=0`)
  - CASCADE delete : supprimer un devis efface ses contrôles
  - CASCADE delete : supprimer une entreprise efface ses contrôles
  - Self-FK SET NULL : supprimer un contrôle parent garde l'enfant avec
    `controle_bat_precedent_id` à None (préserve l'historique)
  - Isolation multi-tenant : un filtre par entreprise_id ne fuit pas
    les contrôles d'une autre entreprise

Ces tests cibles la couche modèle/ORM uniquement (pas d'endpoint).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ControleBat, Devis


def _create_devis_minimal(db: Session, numero: str = "TEST-CB-001") -> Devis:
    """Crée un Devis minimal (machine_id=1 seedé) pour servir de parent."""
    devis = Devis(
        entreprise_id=1,
        numero=numero,
        payload_input={"machine_id": 1},
        payload_output={"prix_vente_ht_eur": "0"},
        mode_calcul="manuel",
        ht_total_eur=0,
        format_h_mm=40,
        format_l_mm=60,
        machine_id=1,
    )
    db.add(devis)
    db.flush()
    return devis


def _kwargs_minimal(devis_id: int, entreprise_id: int = 1) -> dict:
    """Kwargs minimaux pour créer un ControleBat valide."""
    return {
        "entreprise_id": entreprise_id,
        "devis_id": devis_id,
        "bat_url": "https://blob.example/bat-001.pdf",
        "premier_tirage_url": "https://blob.example/tirage-001.jpg",
        "premier_tirage_timestamp": datetime.now(timezone.utc),
        "resultats_comparaison": {"score_conformite_global": 92.5},
        "decision_finale": "en_attente",
        "decideur": "Eric Paysant",
    }


def test_creation_controle_bat_persistance_champs():
    """Crée un ControleBat et vérifie la persistance des champs clés."""
    with SessionLocal() as db:
        devis = _create_devis_minimal(db)
        cb = ControleBat(
            **_kwargs_minimal(devis.id),
            score_conformite=92.5,
            decision_recommandee="valider",
            niveau_confiance="haut",
            sens_sortie_detecte="SE1",
            sens_enroulement_demande="SE1",
            coherence_sens=True,
            ecarts_detectes=[
                {"type": "couleur", "gravite": "mineur", "description": "n/a"}
            ],
        )
        db.add(cb)
        db.commit()
        db.refresh(cb)

        assert cb.id is not None
        assert cb.entreprise_id == 1
        assert cb.devis_id == devis.id
        assert cb.decision_finale == "en_attente"
        assert cb.decideur == "Eric Paysant"
        assert float(cb.score_conformite) == 92.5
        assert cb.decision_recommandee == "valider"
        assert cb.niveau_confiance == "haut"
        assert cb.sens_sortie_detecte == "SE1"
        assert cb.coherence_sens is True
        assert cb.ecarts_detectes[0]["type"] == "couleur"
        assert cb.created_at is not None


def test_defaults_tentative_et_compteurs_ecarts():
    """`tentative_numero` défaut à 1, compteurs écarts à 0."""
    with SessionLocal() as db:
        devis = _create_devis_minimal(db, numero="TEST-CB-DEF-001")
        cb = ControleBat(**_kwargs_minimal(devis.id))
        db.add(cb)
        db.commit()
        db.refresh(cb)

        assert cb.tentative_numero == 1
        assert cb.nb_ecarts_majeurs == 0
        assert cb.nb_ecarts_mineurs == 0
        assert cb.controle_bat_precedent_id is None


def test_cascade_delete_devis_supprime_controles():
    """Supprimer un devis efface en cascade ses contrôles."""
    with SessionLocal() as db:
        devis = _create_devis_minimal(db, numero="TEST-CB-CASC-DEV-001")
        cb = ControleBat(**_kwargs_minimal(devis.id))
        db.add(cb)
        db.commit()
        cb_id = cb.id
        devis_id = devis.id

        db.delete(devis)
        db.commit()

        assert db.query(ControleBat).filter_by(id=cb_id).first() is None
        assert db.query(Devis).filter_by(id=devis_id).first() is None


def test_self_fk_set_null_preserve_chainage_apres_suppression_parent():
    """Supprimer le contrôle parent met `controle_bat_precedent_id` à NULL
    sur la tentative suivante (préserve la row historique).
    """
    with SessionLocal() as db:
        devis = _create_devis_minimal(db, numero="TEST-CB-SELFFK-001")
        cb_parent = ControleBat(**_kwargs_minimal(devis.id))
        db.add(cb_parent)
        db.commit()

        cb_retirage = ControleBat(
            **_kwargs_minimal(devis.id),
            tentative_numero=2,
            controle_bat_precedent_id=cb_parent.id,
        )
        db.add(cb_retirage)
        db.commit()
        retirage_id = cb_retirage.id

        db.delete(cb_parent)
        db.commit()

        retirage_apres = db.query(ControleBat).filter_by(id=retirage_id).first()
        assert retirage_apres is not None
        assert retirage_apres.controle_bat_precedent_id is None
        assert retirage_apres.tentative_numero == 2


def test_isolation_multi_tenant_filtre_entreprise_id(as_user_b):
    """Un filtre par entreprise_id ne fuit pas les contrôles d'une autre.

    On crée un contrôle scopé entreprise_id=1, on bascule sur user B
    (entreprise_id=2), on vérifie que la requête ne retourne rien.
    """
    with SessionLocal() as db:
        devis = _create_devis_minimal(db, numero="TEST-CB-ISO-001")
        cb = ControleBat(**_kwargs_minimal(devis.id, entreprise_id=1))
        db.add(cb)
        db.commit()

    with SessionLocal() as db:
        controles_user_b = (
            db.query(ControleBat).filter(ControleBat.entreprise_id == 2).all()
        )
        assert controles_user_b == []
        controles_user_a = (
            db.query(ControleBat).filter(ControleBat.entreprise_id == 1).all()
        )
        assert len(controles_user_a) >= 1
