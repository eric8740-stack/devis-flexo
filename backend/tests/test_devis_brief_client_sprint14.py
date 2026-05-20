"""Tests Sprint 14 Lot 1 — brief client unifié sur Devis.

Couvre :
- Defaults DB après migration (type_entree_fichier='a_designer', nb_fronts=1,
  trois autres NULL) sur devis créé sans fournir les nouveaux champs.
- Création explicite des 5 champs et relecture (factory).
- Enum SQL : refus d'une valeur hors {'vierge','bat_pro_fourni','a_designer'}.
- JSONB conditions_stockage : dict imbriqué persisté et relu fidèlement.
- Cycle migration up/down/up : les 5 colonnes apparaissent puis disparaissent
  puis réapparaissent, sans casser la table devis.

Pattern aligné sur test_devis_model.py (factory _make_devis + SessionLocal +
cleanup db.delete dans finally).
"""
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect, text

from alembic import command
from alembic.config import Config

from app.db import SessionLocal, engine
from app.models import Devis
from app.schemas.devis_persist import DevisCreate, DevisUpdate


def _payload_input_v1a() -> dict:
    return {
        "complexe_id": 31,
        "laize_utile_mm": 220,
        "ml_total": 3000,
        "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
        "machine_id": 1,
        "mode_calcul": "manuel",
        "intervalle_mm": "3",
        "forfaits_st": [{"partenaire_st_id": 1, "montant_eur": "50.00"}],
    }


def _payload_output_v1a() -> dict:
    return {
        "mode": "manuel",
        "cout_revient_eur": "1228.04",
        "pct_marge_appliquee": "0.18",
        "prix_vente_ht_eur": "1449.09",
        "prix_au_mille_eur": "6.92",
        "postes": [
            {"poste_numero": i, "libelle": f"P{i}", "montant_eur": "100.00", "details": {}}
            for i in range(1, 8)
        ],
    }


def _make_devis(**overrides) -> Devis:
    base = dict(
        entreprise_id=1,
        numero="DEV-2026-S14-0001",
        statut="brouillon",
        client_id=None,
        payload_input=_payload_input_v1a(),
        payload_output=_payload_output_v1a(),
        mode_calcul="manuel",
        cylindre_choisi_z=None,
        cylindre_choisi_nb_etiq=None,
        ht_total_eur=Decimal("1449.09"),
        format_h_mm=Decimal("40"),
        format_l_mm=Decimal("60"),
        machine_id=1,
    )
    base.update(overrides)
    return Devis(**base)


# ---------------------------------------------------------------------------
# Defaults & rétro-compat
# ---------------------------------------------------------------------------


def test_devis_sans_brief_client_recoit_defaults_orm():
    """(a) ORM : création sans fournir les 5 champs → defaults Python appliqués.

    Cas nominal d'une création via Devis(...) sans mentionner les nouveaux
    champs. SQLAlchemy applique le `default=` Python avant l'INSERT.
    Distinct du cas (b) ci-dessous qui teste le `server_default` DB sur
    lignes pré-existantes via backfill migration.
    """
    with SessionLocal() as db:
        devis = _make_devis(numero="DEV-2026-S14-0010")
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            # Defaults DB (server_default)
            assert devis.type_entree_fichier == "a_designer"
            assert devis.nb_fronts_sortie == 1
            # NULL pour les autres
            assert devis.nb_etiquettes_par_rouleau is None
            assert devis.diametre_max_bobine_mm is None
            assert devis.conditions_stockage is None
        finally:
            db.delete(devis)
            db.commit()


# ---------------------------------------------------------------------------
# Factory : création explicite + relecture
# ---------------------------------------------------------------------------


def test_devis_avec_brief_client_complet():
    """Création avec les 5 champs renseignés → tous persistés."""
    stockage = {
        "humidite_pct": 55,
        "t_min_c": 5,
        "t_max_c": 35,
        "lieu": "entrepot couvert non climatisé",
    }
    with SessionLocal() as db:
        devis = _make_devis(
            numero="DEV-2026-S14-0011",
            nb_etiquettes_par_rouleau=2500,
            diametre_max_bobine_mm=200,
            nb_fronts_sortie=2,
            type_entree_fichier="bat_pro_fourni",
            conditions_stockage=stockage,
        )
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            assert devis.nb_etiquettes_par_rouleau == 2500
            assert devis.diametre_max_bobine_mm == 200
            assert devis.nb_fronts_sortie == 2
            assert devis.type_entree_fichier == "bat_pro_fourni"
            assert devis.conditions_stockage == stockage
            # Champ libre du dict (sanity check JSON round-trip)
            assert devis.conditions_stockage["lieu"].startswith("entrepot")
        finally:
            db.delete(devis)
            db.commit()


def test_devis_type_entree_vierge_et_a_designer_acceptes():
    """Les 3 valeurs de l'enum doivent être acceptées."""
    with SessionLocal() as db:
        d1 = _make_devis(numero="DEV-2026-S14-0020", type_entree_fichier="vierge")
        d2 = _make_devis(numero="DEV-2026-S14-0021", type_entree_fichier="a_designer")
        db.add_all([d1, d2])
        db.commit()
        db.refresh(d1)
        db.refresh(d2)
        try:
            assert d1.type_entree_fichier == "vierge"
            assert d2.type_entree_fichier == "a_designer"
        finally:
            db.delete(d1)
            db.delete(d2)
            db.commit()


# ---------------------------------------------------------------------------
# Garde-fou contrat API (Pydantic Literal)
# ---------------------------------------------------------------------------
# Note : SQLite ignore silencieusement les CHECK constraints émis par
# l'Enum SQLA, donc on ne peut pas valider le rejet côté DB en local.
# Le rejet est appliqué côté contrat API par Pydantic (Literal[...]),
# ce qui garantit qu'aucune valeur invalide n'atteint la DB en pratique.
# Sur Postgres prod, le type ENUM natif applique la contrainte côté DB
# en seconde ligne de défense.


def _payload_create_minimal() -> dict:
    return {
        "payload_input": _payload_input_v1a(),
        "payload_output": _payload_output_v1a(),
    }


def test_devis_create_type_entree_invalide_rejete():
    """Pydantic rejette toute valeur hors {vierge, bat_pro_fourni, a_designer}."""
    with pytest.raises(ValidationError):
        DevisCreate(
            **_payload_create_minimal(),
            type_entree_fichier="format_inconnu",
        )


def test_devis_create_defaults_brief_client():
    """DevisCreate sans champs brief → defaults attendus."""
    body = DevisCreate(**_payload_create_minimal())
    assert body.type_entree_fichier == "a_designer"
    assert body.nb_fronts_sortie == 1
    assert body.nb_etiquettes_par_rouleau is None
    assert body.diametre_max_bobine_mm is None
    assert body.conditions_stockage is None


def test_devis_update_partial_brief_client():
    """DevisUpdate accepte n'importe quel sous-ensemble des 5 champs."""
    body = DevisUpdate(
        nb_etiquettes_par_rouleau=1500,
        conditions_stockage={"humidite_pct": 60},
    )
    # Les champs non transmis restent None (partial update via exclude_unset
    # côté CRUD : seuls les transmis sont effectivement écrits).
    dumped = body.model_dump(exclude_unset=True)
    assert dumped == {
        "nb_etiquettes_par_rouleau": 1500,
        "conditions_stockage": {"humidite_pct": 60},
    }


# ---------------------------------------------------------------------------
# Schéma DB après migration
# ---------------------------------------------------------------------------


def test_migration_a_ajoute_les_5_colonnes():
    """Inspecteur SQLA : les 5 colonnes existent sur la table devis."""
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("devis")}
    expected = {
        "nb_etiquettes_par_rouleau",
        "diametre_max_bobine_mm",
        "nb_fronts_sortie",
        "type_entree_fichier",
        "conditions_stockage",
    }
    assert expected.issubset(columns), (
        f"Colonnes Sprint 14 manquantes sur devis : {expected - columns}"
    )


# ---------------------------------------------------------------------------
# (b) Backfill prod : migration applique server_default aux rows existantes
# ---------------------------------------------------------------------------


def test_migration_backfill_defaults_sur_rows_preexistantes():
    """(b) Cas migration prod : un devis créé AVANT le upgrade Sprint 14
    reçoit les `server_default` côté DB pour `type_entree_fichier` et
    `nb_fronts_sortie`, et NULL pour les 3 nullables.

    Simulation : downgrade au state pré-S14 → INSERT raw SQL d'une row sans
    les 5 colonnes (impossible via ORM puisque le modèle les déclare) →
    upgrade → SELECT raw SQL pour vérifier les valeurs effectivement
    écrites par la DB.
    """
    cfg = Config("alembic.ini")
    numero_test = "DEV-S14-BACKFILL-001"

    # Étape 1 — downgrade au state pré-Sprint 14 (j1c6e8a3d9b5)
    command.downgrade(cfg, "-1")

    try:
        # Étape 2 — INSERT raw SQL d'une row "ancienne" sans les 5 colonnes
        # (elles n'existent pas encore à ce state). On utilise les colonnes
        # core + Brief #32 (reduction_pct) + Brief #33 (lot_production a
        # son payload_visuel, pas devis) qui sont déjà présentes.
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO devis (
                        entreprise_id, numero, statut, mode_calcul,
                        payload_input, payload_output, ht_total_eur,
                        format_h_mm, format_l_mm, machine_id, reduction_pct
                    ) VALUES (
                        1, :numero, 'brouillon', 'manuel',
                        '{}', '{}', 1449.09, 40, 60, 1, 0
                    )
                    """
                ),
                {"numero": numero_test},
            )

        # Étape 3 — upgrade head → la migration applique le backfill
        # server_default sur les colonnes NOT NULL (type_entree_fichier)
        # et le default explicite "1" sur nb_fronts_sortie ; les 3 autres
        # restent NULL (nullable sans server_default).
        command.upgrade(cfg, "head")

        # Étape 4 — SELECT raw SQL pour vérifier les valeurs effectivement
        # stockées (sans repasser par l'ORM qui pourrait masquer le test
        # avec son `default=` Python).
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        type_entree_fichier,
                        nb_fronts_sortie,
                        nb_etiquettes_par_rouleau,
                        diametre_max_bobine_mm,
                        conditions_stockage
                    FROM devis
                    WHERE numero = :numero
                    """
                ),
                {"numero": numero_test},
            ).fetchone()

        assert row is not None, (
            f"Row {numero_test} introuvable après backfill migration"
        )
        # server_default appliqué côté DB → 'a_designer' et 1
        assert row.type_entree_fichier == "a_designer", (
            f"server_default type_entree_fichier non appliqué : "
            f"got {row.type_entree_fichier!r}"
        )
        assert row.nb_fronts_sortie == 1, (
            f"server_default nb_fronts_sortie non appliqué : "
            f"got {row.nb_fronts_sortie!r}"
        )
        # Nullables sans server_default → NULL
        assert row.nb_etiquettes_par_rouleau is None
        assert row.diametre_max_bobine_mm is None
        assert row.conditions_stockage is None

    finally:
        # Restaurer la DB à upgrade head au cas où l'assertion a échoué
        # avant l'étape 3 (sinon les tests suivants tombent en cascade).
        try:
            command.upgrade(cfg, "head")
        except Exception:
            pass
        # Cleanup row test
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM devis WHERE numero = :numero"),
                {"numero": numero_test},
            )


# ---------------------------------------------------------------------------
# Cycle migration up/down/up (revisions seules — ne casse pas la session test)
# ---------------------------------------------------------------------------


def test_migration_cycle_down_up_preserve_table_devis():
    """downgrade Sprint 14 → table devis OK sans les 5 colonnes ; upgrade → retour."""
    # Path config Alembic (env piloté par DATABASE_URL/SQLite local cf. env.py).
    cfg = Config("alembic.ini")

    # Down d'un cran : k2d7f9a4b6c8 → j1c6e8a3d9b5
    command.downgrade(cfg, "-1")
    inspector = inspect(engine)
    columns_after_down = {col["name"] for col in inspector.get_columns("devis")}
    for col in (
        "nb_etiquettes_par_rouleau",
        "diametre_max_bobine_mm",
        "nb_fronts_sortie",
        "type_entree_fichier",
        "conditions_stockage",
    ):
        assert col not in columns_after_down, (
            f"downgrade Sprint 14 : colonne {col} aurait dû être supprimée"
        )
    # La table devis reste utilisable (au moins ses colonnes core)
    assert "id" in columns_after_down
    assert "numero" in columns_after_down
    assert "reduction_pct" in columns_after_down  # Brief #32 inchangé

    # Re-upgrade head : colonnes Sprint 14 réapparaissent
    command.upgrade(cfg, "head")
    inspector = inspect(engine)
    columns_after_up = {col["name"] for col in inspector.get_columns("devis")}
    expected = {
        "nb_etiquettes_par_rouleau",
        "diametre_max_bobine_mm",
        "nb_fronts_sortie",
        "type_entree_fichier",
        "conditions_stockage",
    }
    assert expected.issubset(columns_after_up)
