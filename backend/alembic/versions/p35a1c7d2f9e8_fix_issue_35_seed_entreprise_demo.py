"""Fix Issue #35 — INSERT stub entreprise id=1 si manquant, avant Sprint 12.

Contexte du bug
---------------

Au déploiement Railway preview (DB PostgreSQL vierge), la migration
Sprint 12 multi-tenant (`3f8a1e2c5b94`) plante à l'étape
`ADD CONSTRAINT fk_tarif_poste_entreprise FOREIGN KEY(entreprise_id)
REFERENCES entreprise (id) ON DELETE CASCADE` avec
`ForeignKeyViolation: Key (entreprise_id)=(1) is not present in
table "entreprise"`.

Cause racine identifiée (cf. Issue #35) :

1. La migration Sprint 9 v2 (`5a1e9b20c4f8`) fait un INSERT data-only
   de 3 lignes sur `tarif_poste` (`outil_base_eur`,
   `outil_par_trace_eur`, `surcout_forme_speciale_pct`) à un moment
   où la table est mono-tenant (pas de colonne `entreprise_id`).
2. La migration Sprint 12 (`3f8a1e2c5b94`) :
   - ADD COLUMN `entreprise_id` nullable
   - UPDATE `tarif_poste` SET entreprise_id = 1 (backfill des 3 lignes
     précédentes + toutes les rows héritées des autres tables)
   - ALTER COLUMN entreprise_id SET NOT NULL
   - ADD CONSTRAINT FK CASCADE → **crash si entreprise.id=1 n'existe pas.**
3. La row `entreprise(id=1)` n'est créée par AUCUNE migration : seul
   `scripts/seed.py` la crée, lancé manuellement post-`alembic upgrade
   head`. En prod historique, le seed avait été lancé au Sprint 0/1,
   donc entreprise id=1 existait avant l'application de S12. Sur tout
   environnement Postgres fresh (preview Railway, future restauration
   depuis backup pré-S12, autre clone), la condition n'est plus
   satisfaite.
4. SQLite (dev / CI GitHub Actions) ne révèle pas le bug : la
   migration S12 fait `PRAGMA foreign_keys=OFF` pendant ses
   batch_alter_table puis remet `ON` à la fin, et SQLite ne re-vérifie
   pas les FK existantes au PRAGMA ON.

Stratégie de correction (option C retenue par Eric)
---------------------------------------------------

Cette migration corrective est insérée **entre `7c2e4d1f9a3b` (head
mini-sprint bornes, juste avant S12) et `3f8a1e2c5b94` (S12)**. La
modification du `down_revision` de S12 est faite dans le même commit
(voir [backend/alembic/versions/3f8a1e2c5b94_sprint_12_multi_tenant.py]).

L'INSERT utilise `ON CONFLICT (id) DO NOTHING` (syntaxe commune
PostgreSQL natif et SQLite 3.24+) :

- **En prod existante** : `alembic_version` est déjà à head Sprint 15,
  cette migration ne s'exécute jamais. **No-op total, sacré préservé.**
- **Sur DB Postgres fresh** (preview Railway, restauration backup) :
  alembic applique TOUTES les migrations dans l'ordre. Cette migration
  s'exécute après `7c2e4d1f9a3b`, crée le stub entreprise id=1 (les 3
  colonnes NOT NULL à ce point de la chaîne : `id`, `raison_sociale`,
  `siret`). Puis S12 applique son backfill `entreprise_id = 1` et son
  ADD CONSTRAINT FK sans plantage car la row référencée existe.
- **Si une DB historique (sans l'historique de cette migration)
  applique cette migration en rattrapage** : entreprise id=1 existe
  déjà → `ON CONFLICT DO NOTHING` → no-op.

Valeurs du stub
---------------

Alignées sur `seeds/entreprise.csv` (Paysant & Fils Étiquettes,
SIRET 12345678901234) pour rester cohérent avec un seed manuel
ultérieur — pas de conflit `UNIQUE siret` si `python -m scripts.seed`
tourne après. Les colonnes nullable (adresse, ville, etc.) restent
NULL côté stub, le seed les complète quand il tourne.

Idempotence stricte
-------------------

Aucun UPDATE, aucun DELETE. **L'entreprise id=1 et ses 114+ records
seedés en prod sont SACRÉS** — cette migration ne fait QUE l'INSERT
défensif `ON CONFLICT DO NOTHING`. Aucune autre modification de table.

Revision ID: p35a1c7d2f9e8
Revises: 7c2e4d1f9a3b
Create Date: 2026-05-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "p35a1c7d2f9e8"
down_revision: Union[str, Sequence[str], None] = "7c2e4d1f9a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Valeurs du stub — alignées sur seeds/entreprise.csv (compte demo
# Paysant & Fils Étiquettes). Aucune des colonnes ajoutées plus tard
# dans la chaîne (is_demo Sprint 12, paramètres BAT PR #9.1) n'est
# référencée ici : à ce point de la chaîne, elles n'existent pas
# encore comme colonnes de la table entreprise.
DEMO_ENTREPRISE_ID = 1
DEMO_RAISON_SOCIALE = "Paysant & Fils Étiquettes"
DEMO_SIRET = "12345678901234"


def upgrade() -> None:
    """INSERT idempotent du stub entreprise(id=1) si absent.

    Syntaxe `ON CONFLICT (id) DO NOTHING` supportée par :
    - PostgreSQL 9.5+ (prod Railway)
    - SQLite 3.24+ (dev local et CI GitHub Actions, Python 3.13
      embarque SQLite >= 3.40)
    """
    op.execute(
        sa.text(
            """
            INSERT INTO entreprise (id, raison_sociale, siret)
            VALUES (:eid, :raison_sociale, :siret)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(
            eid=DEMO_ENTREPRISE_ID,
            raison_sociale=DEMO_RAISON_SOCIALE,
            siret=DEMO_SIRET,
        )
    )


def downgrade() -> None:
    """Pas de DELETE.

    Le downgrade est un **no-op volontaire**. Raisons :

    1. Sur prod, l'entreprise id=1 contient 114+ records seedés
       cascade-FK (clients, machines, complexes, devis, tarif_poste,
       etc.). Un DELETE déclencherait une cascade catastrophique.
    2. Le stub a la même identité que ce qui serait recréé par
       `scripts/seed.py` — il n'y a aucun écart à réconcilier.
    3. Le downgrade complet de la chaîne (de l'historique alembic
       jusqu'à `base`) drop la table entreprise elle-même via la
       migration `1e63afce3438`, donc le stub disparaît avec la table.

    Si un dev veut vraiment retirer le stub seul (cas théorique
    inexistant dans les workflows projets), il peut le faire via SQL
    direct en assumant les conséquences de cascade.
    """
    pass
