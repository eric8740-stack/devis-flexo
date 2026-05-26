"""Tests modèle Client — extension profil rebobinage Sprint 16.

Couvre les 9 colonnes ajoutées par la migration `s3h5c7d9f4e1` :

  - 4 Integer nullable (diametre_mandrin_mm, diametre_max_bobine_mm,
    sens_enroulement, nb_etiq_par_bobine_fixe) → None par défaut sur
    les clients seedés (CSV n'en contient pas).
  - 3 Boolean NOT NULL (marquage_bobine_requis, mandrin_fourni_par_client,
    film_protection_requis) → False par défaut sur les clients seedés
    (server_default `sa.false()` appliqué au upgrade).
  - 2 String nullable (marquage_bobine_format, conditionnement_souhaite)
    → None par défaut sur les clients seedés.

Setter via ORM : les 9 colonnes acceptent leurs valeurs métier typiques
(diamètre mandrin 76 mm, sens enroulement SE1, etc.).
"""
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Client


def _first_client_demo(db: Session) -> Client:
    """1er client seedé pour entreprise_id=1 (compte demo Paysant)."""
    client = (
        db.query(Client)
        .filter_by(entreprise_id=1)
        .order_by(Client.id)
        .first()
    )
    assert client is not None, "Client demo absent — seed cassé ?"
    return client


# ---------------------------------------------------------------------------
# Defaults sur les clients seedés (rétro-compat ~20 records compte demo)
# ---------------------------------------------------------------------------


def test_client_seede_3_booleens_default_false():
    """Les 3 Boolean NOT NULL sont à False sur les clients existants
    grâce au `server_default sa.false()` appliqué au upgrade migration."""
    with SessionLocal() as db:
        client = _first_client_demo(db)
        assert client.marquage_bobine_requis is False
        assert client.mandrin_fourni_par_client is False
        assert client.film_protection_requis is False


def test_client_seede_6_nullables_default_null():
    """Les 6 colonnes Integer/String nullable restent None pour les
    clients seedés depuis CSV (le CSV n'a pas ces colonnes)."""
    with SessionLocal() as db:
        client = _first_client_demo(db)
        assert client.diametre_mandrin_mm is None
        assert client.diametre_max_bobine_mm is None
        assert client.sens_enroulement is None
        assert client.nb_etiq_par_bobine_fixe is None
        assert client.marquage_bobine_format is None
        assert client.conditionnement_souhaite is None


def test_client_nouveau_via_orm_3_booleens_default_false():
    """Un Client créé via l'ORM sans préciser les Boolean reçoit False
    (default Python `default=False` côté `mapped_column`)."""
    with SessionLocal() as db:
        nv = Client(
            entreprise_id=1,
            raison_sociale="TEST nouveau client rebobinage",
        )
        db.add(nv)
        db.commit()
        db.refresh(nv)
        assert nv.marquage_bobine_requis is False
        assert nv.mandrin_fourni_par_client is False
        assert nv.film_protection_requis is False


# ---------------------------------------------------------------------------
# Setter — les 9 colonnes acceptent leurs valeurs métier
# ---------------------------------------------------------------------------


def test_client_setter_9_champs_rebobinage_persiste():
    """Update + commit + refresh : les 9 colonnes persistent leurs
    valeurs métier typiques (diamètre mandrin 76 mm, SE1, etc.)."""
    with SessionLocal() as db:
        client = _first_client_demo(db)
        client.diametre_mandrin_mm = 76
        client.diametre_max_bobine_mm = 300
        client.sens_enroulement = 1
        client.nb_etiq_par_bobine_fixe = 1000
        client.marquage_bobine_requis = True
        client.marquage_bobine_format = "lot/date/qté"
        client.mandrin_fourni_par_client = True
        client.film_protection_requis = True
        client.conditionnement_souhaite = "Palette filmée 80×120"
        db.commit()
        db.refresh(client)

        assert client.diametre_mandrin_mm == 76
        assert client.diametre_max_bobine_mm == 300
        assert client.sens_enroulement == 1
        assert client.nb_etiq_par_bobine_fixe == 1000
        assert client.marquage_bobine_requis is True
        assert client.marquage_bobine_format == "lot/date/qté"
        assert client.mandrin_fourni_par_client is True
        assert client.film_protection_requis is True
        assert client.conditionnement_souhaite == "Palette filmée 80×120"


def test_client_setter_sens_enroulement_se1_a_se8_accepte():
    """sens_enroulement accepte 1..8 (convention SE1-SE8, cf. rotation_se).

    On stocke l'entier ; la validation métier (plage [1,8]) est
    déléguée au consommateur (moteur cohérence sens — hors scope ici).
    """
    with SessionLocal() as db:
        client = _first_client_demo(db)
        for sens in (1, 2, 3, 4, 5, 6, 7, 8):
            client.sens_enroulement = sens
            db.commit()
            db.refresh(client)
            assert client.sens_enroulement == sens
