"""Blindage pilote (audit 05/07/2026 E2) — UNIQUE composites multi-tenant.

8 contraintes UNIQUE globales héritées du mono-tenant passent en composite
(entreprise_id, clé) :

  - machine.nom                          → uq_machine_entreprise_nom
  - tarif_encre.type_encre               → uq_tarif_encre_entreprise_type
  - tarif_poste.cle                      → uq_tarif_poste_entreprise_cle
  - complexe.reference                   → uq_complexe_entreprise_reference
  - operation_finition.nom               → uq_operation_finition_entreprise_nom
  - outil_decoupe.libelle                → uq_outil_decoupe_entreprise_libelle
  - partenaire_st.raison_sociale         → uq_partenaire_st_entreprise_rs
  - charge_machine_mensuelle(mois,annee) → uq_charge_machine_entreprise_mois_annee

Conséquences métier corrigées : le 2ᵉ tenant qui choisit la même machine à
l'onboarding prenait un 409 ; un seul tenant pouvait posséder les tarifs
encre `pantone`/`process_cmj` (le 2ᵉ recevait CostEngineError sans pouvoir
les créer). Sans impact V1a (aucune donnée modifiée, contrainte relâchée).

Gestion des deux dialectes :
  - PostgreSQL : 7 des 8 contraintes historiques sont ANONYMES dans les
    migrations d'origine (`sa.UniqueConstraint('nom')` sans name) → noms
    auto Postgres type `machine_nom_key`. On les retrouve par RÉFLEXION
    (jeu de colonnes exact) plutôt que de coder les noms en dur, puis
    DROP CONSTRAINT + CREATE composite.
  - SQLite : pas d'ALTER de contrainte → batch_alter_table (recréation de
    table). Les contraintes anonymes reçoivent un nom déterministe via
    `naming_convention` (recette Alembic officielle) pour être ciblables.

Pré-check doublons inutile : l'UNIQUE globale garantissait déjà l'unicité
sur la clé seule, donc a fortiori sur (entreprise_id, clé).

`correspondance_laize_metrage` (M3) volontairement HORS scope : table
globale sans entreprise_id, non exposée par aucun router, non lue par le
moteur — la scoper n'apporterait rien au pilote (cf. rapport audit).

Revision ID: r7t2u9w4x1z6
Revises: e6f8a0b2c4d6
Create Date: 2026-07-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "r7t2u9w4x1z6"
down_revision: Union[str, Sequence[str], None] = "e6f8a0b2c4d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, colonnes de l'UNIQUE globale historique, nom du composite cible)
_CIBLES: list[tuple[str, list[str], str]] = [
    ("machine", ["nom"], "uq_machine_entreprise_nom"),
    ("tarif_encre", ["type_encre"], "uq_tarif_encre_entreprise_type"),
    ("tarif_poste", ["cle"], "uq_tarif_poste_entreprise_cle"),
    ("complexe", ["reference"], "uq_complexe_entreprise_reference"),
    ("operation_finition", ["nom"], "uq_operation_finition_entreprise_nom"),
    ("outil_decoupe", ["libelle"], "uq_outil_decoupe_entreprise_libelle"),
    ("partenaire_st", ["raison_sociale"], "uq_partenaire_st_entreprise_rs"),
    (
        "charge_machine_mensuelle",
        ["mois", "annee"],
        "uq_charge_machine_entreprise_mois_annee",
    ),
]

# Recette Alembic pour SQLite : les contraintes UNIQUE anonymes reflétées
# reçoivent ce nom déterministe → ciblables par batch_op.drop_constraint.
# Les contraintes déjà nommées (uq_charge_machine_mois_annee) gardent leur nom.
_NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def _nom_unique_existante(
    insp: sa.Inspector, table: str, colonnes: list[str]
) -> tuple[bool, str | None]:
    """Retrouve l'UNIQUE globale par son jeu de colonnes exact.

    Retourne (trouvée, nom) — nom None si la contrainte est anonyme
    (SQLite autoindex). `trouvée=False` si aucune contrainte ne matche
    (base déjà migrée / replay) → on saute le DROP, on crée juste le
    composite.
    """
    for uc in insp.get_unique_constraints(table):
        if list(uc["column_names"]) == colonnes:
            return True, uc.get("name")
    return False, None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    dialecte = bind.dialect.name

    for table, colonnes, nom_composite in _CIBLES:
        trouvee, nom_existant = _nom_unique_existante(insp, table, colonnes)

        if dialecte == "postgresql":
            if trouvee and nom_existant:
                op.drop_constraint(nom_existant, table, type_="unique")
            op.create_unique_constraint(
                nom_composite, table, ["entreprise_id", *colonnes]
            )
        else:
            # SQLite — batch (recréation de table). Nom de la contrainte à
            # dropper : le vrai nom si elle en a un, sinon celui que la
            # naming_convention attribue aux anonymes reflétées.
            nom_a_dropper = nom_existant or f"uq_{table}_{colonnes[0]}"
            with op.batch_alter_table(
                table, naming_convention=_NAMING_CONVENTION
            ) as batch_op:
                if trouvee:
                    batch_op.drop_constraint(nom_a_dropper, type_="unique")
                batch_op.create_unique_constraint(
                    nom_composite, ["entreprise_id", *colonnes]
                )


def downgrade() -> None:
    """Sens inverse : composite → UNIQUE globale historique.

    Si deux tenants possèdent déjà la même clé (situation permise après
    upgrade), le downgrade échoue côté DB avec UniqueViolation — c'est le
    comportement attendu (pas de silent data loss), cf. y9n2i3g7d5f0.

    Postgres : contrainte recréée ANONYME (name=None) → nom auto
    `<table>_<col>_key`, identique à l'état d'origine.
    """
    bind = op.get_bind()
    dialecte = bind.dialect.name

    for table, colonnes, nom_composite in _CIBLES:
        # La contrainte d'origine de charge_machine_mensuelle était nommée.
        nom_origine = (
            "uq_charge_machine_mois_annee"
            if table == "charge_machine_mensuelle"
            else None
        )
        if dialecte == "postgresql":
            op.drop_constraint(nom_composite, table, type_="unique")
            op.create_unique_constraint(nom_origine, table, colonnes)
        else:
            nom_recree = nom_origine or f"uq_{table}_{colonnes[0]}"
            with op.batch_alter_table(
                table, naming_convention=_NAMING_CONVENTION
            ) as batch_op:
                batch_op.drop_constraint(nom_composite, type_="unique")
                batch_op.create_unique_constraint(nom_recree, colonnes)
