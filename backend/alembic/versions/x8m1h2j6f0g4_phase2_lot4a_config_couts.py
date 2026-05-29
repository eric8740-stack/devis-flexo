"""Phase 2 / Lot 4a — sortie des 7 tarifs P1/P3/P4/P6 vers `config_couts`.

Migration additive et réversible. Sept colonnes scopées tenant
ajoutées à `config_couts` pour finir la sortie ICE des constantes
historiquement stockées sous forme de rows sur `tarif_poste` :

- marge_confort_roulage_mm        Integer        (P1 surface support)
- cliche_prix_couleur_eur         Numeric(8,2)   (P3a clichés)
- outil_base_eur                  Numeric(10,2)  (P3b outil neuf — base)
- outil_par_trace_eur             Numeric(8,2)   (P3b outil neuf — par trace)
- surcout_forme_speciale_facteur  Numeric(4,2)   (P3b multiplicateur ; rename
                                                  depuis `_pct` : c'EST un
                                                  multiplicateur 1.0..2.0)
- calage_forfait_eur              Numeric(10,2)  (P4)
- finitions_prix_m2_eur           Numeric(8,4)   (P6)

Pattern (cf Lot 3 / Phase 1 socle) :
- `nullable=False`, `server_default` = baseline marché agrégée (NE PAS
  inscrire les valeurs spécifiques au tenant démo en dur côté server_
  default — elles seraient propagées à TOUS les nouveaux tenants alors
  qu'elles reflètent la config d'UN imprimeur particulier).
- `upgrade()` réécrit ensuite les 7 colonnes UNIQUEMENT pour
  `entreprise_id=1` (démo) avec les valeurs historiques exactes
  (10 / 45.00 / 200.00 / 50.00 / 1.40 / 225.00 / 0.1250) → préserve
  V1a 1 449,09 par construction (benchmark figé `cost_engine`).

`tarif_poste` n'est PAS touché : les 7 rows restent en place mais les
consommateurs P1/P3/P4/P6 basculent vers `ConfigCouts` (cf. dépréciation
docstrings côté postes). Suppression colonne reportée à un futur lot
quand toutes les références code seront purgées (`matiere_prix_kg_defaut`
reste consommé par P1 fallback — hors scope ici).

Revision ID: x8m1h2j6f0g4
Revises: w7l9g1e5d3f8
Create Date: 2026-05-29
"""
from decimal import Decimal

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "x8m1h2j6f0g4"
down_revision = "w7l9g1e5d3f8"
branch_labels = None
depends_on = None


# Valeurs historiques EXACTES seedées sur entreprise_id=1 (démo) par la
# migration sprint 9 v2 (5a1e9b20c4f8) et constantes correspondantes du
# moteur. ÉCRITES IDENTIQUES au upgrade() pour préserver V1a 1 449,09.
_VALEURS_DEMO_ENTREPRISE_ID_1 = {
    "marge_confort_roulage_mm": 10,
    "cliche_prix_couleur_eur": Decimal("45.00"),
    "outil_base_eur": Decimal("200.00"),
    "outil_par_trace_eur": Decimal("50.00"),
    "surcout_forme_speciale_facteur": Decimal("1.40"),
    "calage_forfait_eur": Decimal("225.00"),
    "finitions_prix_m2_eur": Decimal("0.1250"),
}


def upgrade() -> None:
    """Schema : 7 colonnes additives nullable=False + server_default neutre.

    server_default = baseline marché agrégée (≠ valeurs démo). Le
    upgrade() UPDATE ensuite SPÉCIFIQUEMENT entreprise_id=1 aux
    valeurs démo historiques pour préserver le benchmark V1a.
    """
    # ------------------------------------------------------------
    # 1. Ajout des 7 colonnes — nullable=False + server_default marché.
    # ------------------------------------------------------------
    op.add_column(
        "config_couts",
        sa.Column(
            "marge_confort_roulage_mm",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("10"),  # constante physique typique
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "cliche_prix_couleur_eur",
            sa.Numeric(8, 2),
            nullable=False,
            server_default=sa.text("50.00"),
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "outil_base_eur",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("300.00"),
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "outil_par_trace_eur",
            sa.Numeric(8, 2),
            nullable=False,
            server_default=sa.text("60.00"),
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "surcout_forme_speciale_facteur",
            sa.Numeric(4, 2),
            nullable=False,
            server_default=sa.text("1.50"),
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "calage_forfait_eur",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("250.00"),
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "finitions_prix_m2_eur",
            sa.Numeric(8, 4),
            nullable=False,
            server_default=sa.text("0.1500"),
        ),
    )

    # ------------------------------------------------------------
    # 2. UPDATE entreprise_id=1 (démo) → valeurs historiques EXACTES.
    #    Préserve V1a 1 449,09 (benchmark figé `cost_engine`).
    #
    # NB : les valeurs sont inlinées dans le SQL (pas de bind) pour
    # éviter `sqlite3.ProgrammingError: type Decimal is not supported`
    # — le binding direct Python→sqlite ne couvre pas Decimal. Ce sont
    # des constantes contrôlées (cf. `_VALEURS_DEMO_ENTREPRISE_ID_1`
    # documenté ci-dessus), pas d'input externe → safe.
    # ------------------------------------------------------------
    v = _VALEURS_DEMO_ENTREPRISE_ID_1
    op.execute(
        f"""
        UPDATE config_couts SET
          marge_confort_roulage_mm        = {int(v["marge_confort_roulage_mm"])},
          cliche_prix_couleur_eur         = {v["cliche_prix_couleur_eur"]},
          outil_base_eur                  = {v["outil_base_eur"]},
          outil_par_trace_eur             = {v["outil_par_trace_eur"]},
          surcout_forme_speciale_facteur  = {v["surcout_forme_speciale_facteur"]},
          calage_forfait_eur              = {v["calage_forfait_eur"]},
          finitions_prix_m2_eur           = {v["finitions_prix_m2_eur"]}
        WHERE entreprise_id = 1
        """
    )


def downgrade() -> None:
    """Schema : drop des 7 colonnes (réversible)."""
    op.drop_column("config_couts", "finitions_prix_m2_eur")
    op.drop_column("config_couts", "calage_forfait_eur")
    op.drop_column("config_couts", "surcout_forme_speciale_facteur")
    op.drop_column("config_couts", "outil_par_trace_eur")
    op.drop_column("config_couts", "outil_base_eur")
    op.drop_column("config_couts", "cliche_prix_couleur_eur")
    op.drop_column("config_couts", "marge_confort_roulage_mm")
