"""P1+P2 — Unify Machine <-> MachineImprimerie.

Convergence option B etape finale (post-B1/B2/B3a/B3b + P0a/P0b) :
fusion definitive du parc machine sur `Machine` (Sprint 2). La table
`machine_imprimerie` (Sprint 13.B) et la table morte `configuration_pose`
(jamais peuplee en prod) sont supprimees.

DECISION Eric (cf brief P1+P2) :
  - Parc Machine cible = jusqu'a 4 presses : Mark Andy P5 (existe deja,
    id=1, laize 330) + 3 recreees depuis machine_imprimerie en copiant
    leurs laizes : Mark Andy 2200 (320), OMET XFlex 330 (330),
    Nilpeter FA-22 (330). Si MI ne contient pas ces 3 noms (ex. dev
    locale post-cleanup MI), aucune presse n'est inseree -- la migration
    reste idempotente.
  - 2 Mark Andy = presses DISTINCTES (P5 conservee, 2200 ajoutee a cote).
  - **AUCUNE suppression de fiche Machine existante** (correction Eric
    P1+P2). Daco D250 + Atelier 2 (Machine id=2/3 du seed legacy)
    restent intactes ; cleanup eventuel = decision metier separee.
  - Finition/rebobineuse (MachineRebobineuse) = hors scope, intact.
  - Principe VALUE-NEUTRAL : chaque presse garde sa laize -> tripwire
    P0b (704,07 EUR) reste EXACT (Mark Andy 2200 a toujours laize=320
    cote Machine apres migration).

Mapping champs MI -> Machine (NOT NULL Machine sans equivalent MI :
defauts surs documentes) :
  - laize_max_mm        <- MI.laize_totale_mm
  - laize_utile_mm      <- MI.laize_utile_mm
  - vitesse_max_m_min   <- MI.vitesse_nominale_constructeur_m_min
  - vitesse_moyenne_m_h <- MI.vitesse_pratique_m_min * 60 (m/min -> m/h)
  - nb_groupes_couleurs <- MI.nb_groupes_couleurs
  - nb_postes_decoupe   <- MI.nb_postes_decoupe (NOT NULL, defaut 1)
  - cout_horaire_eur    <- MI.cout_horaire_eur
  - options             <- MI.options (JSON list)
  - actif               <- MI.actif (NOT NULL, default True)
  - duree_calage_h      <- NULL (pas dans MI)
  - largeur_max_mm      <- NULL (pas dans MI)
  - commentaire         <- NULL (pas dans MI)

Apres migration :
  - lot_production.machine_id + porte_cliche.machine_id -> remappes via
    mapping mi.id -> new machine.id ET FK realtoutees vers machine.id.
  - machine_imprimerie + configuration_pose : tables droppees.

Downgrade BEST-EFFORT :
  - Recree tables machine_imprimerie + configuration_pose VIDES.
  - Restauration data legacy partielle : pour chaque Machine connue du
    catalogue (Mark Andy 2200/OMET/Nilpeter), recree une row MI avec
    les memes valeurs (perte du nb_pc_pXX/options/etc. specifiques MI
    non documente).
  - Ré-établit les FK lot_production/porte_cliche vers
    machine_imprimerie.id via mapping inverse.
  - DELETE des Machine inserees au upgrade (ceux qui n'existaient pas
    avant -- detecte par nom = catalogue type).
  Limite : si l'utilisateur a edite les Machines apres P1 (ex. ajoute
  des options custom), ces editions sont PERDUES au downgrade. C'est
  un compromis acceptable d'un downgrade de fusion.

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Noms catalogue Mark Andy 2200 / OMET XFlex 330 / Nilpeter FA-22 -- utilises
# pour la restauration downgrade (best-effort) : on detecte par nom les
# Machines qui ont ete inserees par upgrade pour les recreer en MI au
# downgrade et les supprimer cote Machine.
_NOMS_CATALOGUE_MI = ("Mark Andy 2200", "OMET XFlex 330", "Nilpeter FA-22")


def upgrade() -> None:
    bind = op.get_bind()

    # === 1. INSERT machines depuis machine_imprimerie ========================
    # Idempotent : si une Machine du meme nom + tenant existe deja, on la
    # reutilise (cas Mark Andy P5 demo : presente dans Machine seed mais
    # PAS dans MI catalogue -> pas de doublon).
    mi_rows = bind.execute(
        text(
            "SELECT id, entreprise_id, nom, laize_totale_mm, laize_utile_mm, "
            "nb_groupes_couleurs, nb_postes_decoupe, vitesse_pratique_m_min, "
            "vitesse_nominale_constructeur_m_min, cout_horaire_eur, "
            "options, actif "
            "FROM machine_imprimerie"
        )
    ).fetchall()

    mi_to_machine_id: dict[int, int] = {}
    for mi in mi_rows:
        existing = bind.execute(
            text(
                "SELECT id FROM machine "
                "WHERE nom = :nom AND entreprise_id = :eid"
            ),
            {"nom": mi.nom, "eid": mi.entreprise_id},
        ).first()
        if existing:
            mi_to_machine_id[mi.id] = existing.id
            continue

        vitesse_moyenne_m_h = (
            mi.vitesse_pratique_m_min * 60
            if mi.vitesse_pratique_m_min is not None
            else None
        )
        options_value = mi.options if mi.options is not None else "[]"

        bind.execute(
            text(
                "INSERT INTO machine ("
                "entreprise_id, nom, laize_max_mm, laize_utile_mm, "
                "vitesse_max_m_min, vitesse_moyenne_m_h, "
                "nb_groupes_couleurs, nb_postes_decoupe, cout_horaire_eur, "
                "options, actif"
                ") VALUES ("
                ":entreprise_id, :nom, :laize_max_mm, :laize_utile_mm, "
                ":vitesse_max_m_min, :vitesse_moyenne_m_h, "
                ":nb_groupes_couleurs, :nb_postes_decoupe, :cout_horaire_eur, "
                ":options, :actif"
                ")"
            ),
            {
                "entreprise_id": mi.entreprise_id,
                "nom": mi.nom,
                "laize_max_mm": float(mi.laize_totale_mm),
                "laize_utile_mm": float(mi.laize_utile_mm),
                "vitesse_max_m_min": mi.vitesse_nominale_constructeur_m_min,
                "vitesse_moyenne_m_h": vitesse_moyenne_m_h,
                "nb_groupes_couleurs": mi.nb_groupes_couleurs,
                "nb_postes_decoupe": mi.nb_postes_decoupe or 1,
                "cout_horaire_eur": (
                    float(mi.cout_horaire_eur)
                    if mi.cout_horaire_eur is not None
                    else None
                ),
                "options": options_value,
                "actif": bool(mi.actif),
            },
        )
        new_id = bind.execute(
            text(
                "SELECT id FROM machine "
                "WHERE nom = :nom AND entreprise_id = :eid"
            ),
            {"nom": mi.nom, "eid": mi.entreprise_id},
        ).scalar()
        mi_to_machine_id[mi.id] = new_id

    # === 2-3. DROP FK MI -> UPDATE remap -> CREATE FK Machine ================
    # SQLite : PRAGMA foreign_keys=OFF pendant l'UPDATE pour eviter le
    # rejet de la FK MI (qui pointe encore vers MI.id pendant la transition).
    # Postgres : drop_constraint natif AVANT l'UPDATE.
    is_sqlite = bind.dialect.name == "sqlite"
    if is_sqlite:
        bind.execute(text("PRAGMA foreign_keys = OFF"))
    else:
        op.drop_constraint(
            "lot_production_machine_id_fkey",
            "lot_production",
            type_="foreignkey",
        )
        op.drop_constraint(
            "porte_cliche_machine_id_fkey",
            "porte_cliche",
            type_="foreignkey",
        )

    # Remap data (FK temporairement absente / desactivee).
    for mi_id, new_machine_id in mi_to_machine_id.items():
        bind.execute(
            text(
                "UPDATE lot_production SET machine_id = :new "
                "WHERE machine_id = :old"
            ),
            {"new": new_machine_id, "old": mi_id},
        )
        bind.execute(
            text(
                "UPDATE porte_cliche SET machine_id = :new "
                "WHERE machine_id = :old"
            ),
            {"new": new_machine_id, "old": mi_id},
        )

    # Re-create FK vers machine.id
    if is_sqlite:
        # Bug constate en CI : sur SQLite, batch.create_foreign_key AJOUTE
        # une FK mais l'ancienne (-> machine_imprimerie.id) reste presente
        # dans la table reconstruite par batch (qui reflete les FK existantes).
        # Quand machine_imprimerie est droppee juste apres, la FK orpheline
        # rend toute operation SQL sur lot_production impossible :
        # OperationalError "no such table: main.machine_imprimerie".
        # Fix : `copy_from=Table_cible` pour forcer la reconstruction avec
        # uniquement la nouvelle FK -> machine.id (l'ancienne disparait).
        # Postgres : `op.drop_constraint` natif au-dessus a deja vire la FK.
        target_meta = sa.MetaData()
        lot_target = sa.Table(
            "lot_production",
            target_meta,
            sa.Column(
                "id", sa.Integer, primary_key=True, autoincrement=True
            ),
            sa.Column(
                "devis_id",
                sa.Integer,
                sa.ForeignKey("devis.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "entreprise_id",
                sa.Integer,
                sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("ordre", sa.Integer, nullable=False),
            sa.Column(
                "cylindre_id",
                sa.Integer,
                sa.ForeignKey("cylindre_magnetique.id"),
                nullable=False,
            ),
            sa.Column(
                "machine_id",
                sa.Integer,
                sa.ForeignKey(
                    "machine.id", name="lot_production_machine_id_fkey"
                ),
                nullable=False,
            ),
            sa.Column("nb_poses_dev", sa.Integer, nullable=False),
            sa.Column("nb_poses_laize", sa.Integer, nullable=False),
            sa.Column("sens_enroulement", sa.Integer, nullable=False),
            sa.Column("quantite", sa.Integer, nullable=False),
            sa.Column(
                "matiere_id",
                sa.Integer,
                sa.ForeignKey("matiere.id"),
                nullable=False,
            ),
            sa.Column(
                "intervalle_dev_reel_mm", sa.Numeric(5, 2), nullable=True
            ),
            sa.Column(
                "intervalle_laize_reel_mm", sa.Numeric(5, 2), nullable=True
            ),
            sa.Column("largeur_plaque_mm", sa.Numeric(6, 2), nullable=True),
            sa.Column("score_optim", sa.Float, nullable=True),
            sa.Column("cout_lot_ht_eur", sa.Numeric(10, 2), nullable=True),
            sa.Column("payload_visuel", sa.JSON, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "devis_id", "ordre", name="uq_lot_production_devis_ordre"
            ),
        )
        pc_target = sa.Table(
            "porte_cliche",
            target_meta,
            sa.Column(
                "id", sa.Integer, primary_key=True, autoincrement=True
            ),
            sa.Column(
                "entreprise_id",
                sa.Integer,
                sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "machine_id",
                sa.Integer,
                sa.ForeignKey(
                    "machine.id", name="porte_cliche_machine_id_fkey"
                ),
                nullable=False,
            ),
            sa.Column(
                "cylindre_id",
                sa.Integer,
                sa.ForeignKey("cylindre_magnetique.id"),
                nullable=False,
            ),
            sa.Column("quantite", sa.Integer, nullable=False),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column(
                "actif",
                sa.Boolean,
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "entreprise_id",
                "machine_id",
                "cylindre_id",
                name="uq_porte_cliche_entreprise_machine_cyl",
            ),
            sa.CheckConstraint(
                "quantite >= 0", name="ck_porte_cliche_quantite_positive"
            ),
        )
        # recreate="always" force la reconstruction meme sans op destructive
        # dans le batch (sinon copy_from est ignore et la FK orpheline reste).
        with op.batch_alter_table(
            "lot_production",
            schema=None,
            copy_from=lot_target,
            recreate="always",
        ):
            pass
        with op.batch_alter_table(
            "porte_cliche",
            schema=None,
            copy_from=pc_target,
            recreate="always",
        ):
            pass
        bind.execute(text("PRAGMA foreign_keys = ON"))
    else:
        op.create_foreign_key(
            "lot_production_machine_id_fkey",
            "lot_production",
            "machine",
            ["machine_id"],
            ["id"],
        )
        op.create_foreign_key(
            "porte_cliche_machine_id_fkey",
            "porte_cliche",
            "machine",
            ["machine_id"],
            ["id"],
        )

    # === 4. (retire) suppression Daco/Atelier 2 -- correction Eric P1+P2 ===
    # La migration NE touche AUCUNE fiche Machine existante : Daco D250 et
    # Atelier 2 (Machine id=2/3 du seed legacy Sprint 2) restent intactes.
    # Cleanup eventuel de ces machines : decision metier separee, hors P1+P2.

    # === 5. DROP TABLE configuration_pose + machine_imprimerie ==============
    # configuration_pose : table jamais peuplee en prod (cf audit P1+P2).
    # machine_imprimerie : tous les usages ont ete repointes (lot_production
    # + porte_cliche FK migrees ci-dessus ; crud/devis.py lit Machine depuis
    # ce commit).
    op.drop_table("configuration_pose")
    op.drop_table("machine_imprimerie")


def downgrade() -> None:
    """Best-effort. Recree les tables vides + restauration legacy partielle.

    Limite assumee : si l'utilisateur a edite les Machines inserees au
    upgrade APRES la migration, ces editions sont PERDUES (les MI
    restaurees prennent les valeurs catalogue d'origine via une re-lecture
    des Machine actuelles).
    """
    bind = op.get_bind()

    # === 1. Recree configuration_pose (vide, identique au schema Sprint 13) =
    op.create_table(
        "configuration_pose",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entreprise_id", sa.Integer(), nullable=False),
        sa.Column(
            "machine_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("nb_postes_x", sa.Integer(), nullable=False),
        sa.Column("nb_postes_y", sa.Integer(), nullable=False),
        sa.Column("date_creation", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["entreprise_id"], ["entreprise.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # === 2. Recree machine_imprimerie (vide, schema Sprint 13.B) ============
    op.create_table(
        "machine_imprimerie",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entreprise_id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("marque", sa.String(length=50), nullable=True),
        sa.Column("modele", sa.String(length=50), nullable=True),
        sa.Column("repere_court", sa.String(length=20), nullable=True),
        sa.Column("laize_totale_mm", sa.Numeric(6, 2), nullable=False),
        sa.Column("laize_utile_mm", sa.Numeric(6, 2), nullable=False),
        sa.Column("nb_groupes_couleurs", sa.Integer(), nullable=True),
        sa.Column(
            "nb_postes_decoupe",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "vitesse_nominale_constructeur_m_min",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column("vitesse_pratique_m_min", sa.Integer(), nullable=False),
        sa.Column("vitesse_par_matiere", sa.JSON(), nullable=True),
        sa.Column("vitesse_max_tours_h", sa.Integer(), nullable=True),
        sa.Column("cout_horaire_eur", sa.Numeric(8, 2), nullable=True),
        sa.Column("cylindres_compatibles", sa.JSON(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("type_encre_supportee", sa.JSON(), nullable=True),
        sa.Column(
            "actif", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("date_acquisition", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("date_creation", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entreprise_id"], ["entreprise.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_machine_imprimerie_entreprise_id",
        "machine_imprimerie",
        ["entreprise_id"],
    )

    # === 3. Re-INSERT machine_imprimerie depuis Machines catalogue ==========
    # Mapping inverse : pour chaque Machine dont le nom correspond au
    # catalogue MI (Mark Andy 2200/OMET/Nilpeter), recree une MI miroir.
    machines_cat = bind.execute(
        text(
            "SELECT id, entreprise_id, nom, laize_max_mm, laize_utile_mm, "
            "vitesse_max_m_min, vitesse_moyenne_m_h, nb_groupes_couleurs, "
            "nb_postes_decoupe, cout_horaire_eur, options, actif "
            "FROM machine WHERE nom IN :noms"
        ).bindparams(sa.bindparam("noms", expanding=True)),
        {"noms": list(_NOMS_CATALOGUE_MI)},
    ).fetchall()

    machine_to_mi_id: dict[int, int] = {}
    for m in machines_cat:
        vitesse_pratique_m_min = (
            int(m.vitesse_moyenne_m_h / 60)
            if m.vitesse_moyenne_m_h is not None and m.vitesse_moyenne_m_h > 0
            else 60  # NOT NULL default minimal sur MI legacy
        )
        bind.execute(
            text(
                "INSERT INTO machine_imprimerie ("
                "entreprise_id, nom, laize_totale_mm, laize_utile_mm, "
                "vitesse_nominale_constructeur_m_min, vitesse_pratique_m_min, "
                "nb_groupes_couleurs, nb_postes_decoupe, cout_horaire_eur, "
                "options, actif, date_creation"
                ") VALUES ("
                ":entreprise_id, :nom, :laize_totale_mm, :laize_utile_mm, "
                ":vit_nom, :vit_prat, "
                ":nb_groupes_couleurs, :nb_postes_decoupe, :cout_horaire_eur, "
                ":options, :actif, CURRENT_TIMESTAMP"
                ")"
            ),
            {
                "entreprise_id": m.entreprise_id,
                "nom": m.nom,
                "laize_totale_mm": float(m.laize_max_mm),
                "laize_utile_mm": float(m.laize_utile_mm or m.laize_max_mm),
                "vit_nom": m.vitesse_max_m_min,
                "vit_prat": vitesse_pratique_m_min,
                "nb_groupes_couleurs": m.nb_groupes_couleurs,
                "nb_postes_decoupe": m.nb_postes_decoupe or 1,
                "cout_horaire_eur": (
                    float(m.cout_horaire_eur)
                    if m.cout_horaire_eur is not None
                    else None
                ),
                "options": m.options if m.options is not None else "[]",
                "actif": bool(m.actif),
            },
        )
        new_mi_id = bind.execute(
            text(
                "SELECT id FROM machine_imprimerie "
                "WHERE nom = :nom AND entreprise_id = :eid"
            ),
            {"nom": m.nom, "eid": m.entreprise_id},
        ).scalar()
        machine_to_mi_id[m.id] = new_mi_id

    # === 4-5. DROP FK Machine -> UPDATE inverse -> CREATE FK MI ==============
    # Meme pattern qu'upgrade : FK off pendant remap pour eviter IntegrityError
    # transitoire (le mapping bouge les ids).
    is_sqlite = bind.dialect.name == "sqlite"
    if is_sqlite:
        bind.execute(text("PRAGMA foreign_keys = OFF"))
    else:
        op.drop_constraint(
            "lot_production_machine_id_fkey",
            "lot_production",
            type_="foreignkey",
        )
        op.drop_constraint(
            "porte_cliche_machine_id_fkey",
            "porte_cliche",
            type_="foreignkey",
        )

    for machine_id, new_mi_id in machine_to_mi_id.items():
        bind.execute(
            text(
                "UPDATE lot_production SET machine_id = :new "
                "WHERE machine_id = :old"
            ),
            {"new": new_mi_id, "old": machine_id},
        )
        bind.execute(
            text(
                "UPDATE porte_cliche SET machine_id = :new "
                "WHERE machine_id = :old"
            ),
            {"new": new_mi_id, "old": machine_id},
        )

    if is_sqlite:
        with op.batch_alter_table("lot_production", schema=None) as batch:
            batch.create_foreign_key(
                "lot_production_machine_id_fkey",
                "machine_imprimerie",
                ["machine_id"],
                ["id"],
            )
        with op.batch_alter_table("porte_cliche", schema=None) as batch:
            batch.create_foreign_key(
                "porte_cliche_machine_id_fkey",
                "machine_imprimerie",
                ["machine_id"],
                ["id"],
            )
        bind.execute(text("PRAGMA foreign_keys = ON"))
    else:
        op.create_foreign_key(
            "lot_production_machine_id_fkey",
            "lot_production",
            "machine_imprimerie",
            ["machine_id"],
            ["id"],
        )
        op.create_foreign_key(
            "porte_cliche_machine_id_fkey",
            "porte_cliche",
            "machine_imprimerie",
            ["machine_id"],
            ["id"],
        )

    # === 6. DELETE des Machine inserees au upgrade (best-effort) ============
    # Tout Machine dont le nom appartient au catalogue MI ET qui n'a pas
    # de FK externe -> supposee inseree par upgrade, on la supprime pour
    # restituer l'etat pre-upgrade.
    for nom in _NOMS_CATALOGUE_MI:
        machines = bind.execute(
            text("SELECT id FROM machine WHERE nom = :nom"),
            {"nom": nom},
        ).fetchall()
        for m in machines:
            refs_devis = bind.execute(
                text("SELECT COUNT(*) FROM devis WHERE machine_id = :id"),
                {"id": m.id},
            ).scalar()
            refs_catalogue = bind.execute(
                text("SELECT COUNT(*) FROM catalogue WHERE machine_id = :id"),
                {"id": m.id},
            ).scalar()
            if (refs_devis or 0) == 0 and (refs_catalogue or 0) == 0:
                bind.execute(
                    text("DELETE FROM machine WHERE id = :id"),
                    {"id": m.id},
                )
