"""Feat historique analyses : ajout champs photo persistante.

Ajoute 3 colonnes à `analyse_photo_etiquette` pour stocker les métadonnées
de la photo sauvegardée sur disque (Railway Volume monté sur
/mnt/uploads/photos, configurable via PHOTO_UPLOAD_DIR) :

  - image_filename      : nom d'origine côté client (affichage UI)
  - image_key           : nom du fichier sur disque, "{uuid}.{ext}", UNIQUE
                          (sert de clé GET /api/photos/{key})
  - image_size_bytes    : taille brute du fichier sauvé

Tous nullables car :
  - Rétro-compat : les analyses créées avant ce feat (Sprint 13.E.3)
    n'ont pas de photo physique persistée.
  - Mode dégradé : si le Volume n'est pas monté en prod, l'analyse
    persiste quand même (juste sans photo). image_size_bytes=0 dans ce cas.

Revision ID: f6b3c8e4d712
Revises: e4a7b9c2d6f1 (Sprint 13 S13.E.2 — table analyse_photo_etiquette)
Create Date: 2026-05-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f6b3c8e4d712"
down_revision: Union[str, Sequence[str], None] = "e4a7b9c2d6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analyse_photo_etiquette",
        sa.Column("image_filename", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "analyse_photo_etiquette",
        sa.Column("image_key", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "analyse_photo_etiquette",
        sa.Column("image_size_bytes", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_analyse_photo_etiquette_image_key",
        "analyse_photo_etiquette",
        ["image_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_analyse_photo_etiquette_image_key",
        "analyse_photo_etiquette",
        type_="unique",
    )
    op.drop_column("analyse_photo_etiquette", "image_size_bytes")
    op.drop_column("analyse_photo_etiquette", "image_key")
    op.drop_column("analyse_photo_etiquette", "image_filename")
