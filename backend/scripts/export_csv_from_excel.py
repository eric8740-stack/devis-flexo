"""Exporte les onglets entreprise/client/fournisseur du template Excel en CSV prets pour le seed.

Sortie : backend/seeds/{entreprise,client,fournisseur}.csv
  - UTF-8 sans BOM
  - Separateur virgule
  - Dates au format ISO YYYY-MM-DD
  - SIRET conserve en chaine de 14 chiffres
  - Lignes de note / commentaires filtrees (id non numerique)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent.parent
SEEDS_DIR = BACKEND_DIR / "seeds"

SHEETS = ("entreprise", "client", "fournisseur")
DATE_COLUMNS = {"date_creation"}
SIRET_COLUMNS = {"siret"}


def find_excel() -> Path:
    candidates = sorted(
        p
        for p in PROJECT_ROOT.glob("Donnees_Fictives_TPE_Flexo_v3*.xlsx")
        if not p.name.startswith("~$")
    )
    if not candidates:
        raise FileNotFoundError(
            f"Aucun fichier 'Donnees_Fictives_TPE_Flexo_v3*.xlsx' trouve dans {PROJECT_ROOT}"
        )
    return candidates[0]


def is_valid_id(value: object) -> bool:
    """True si la valeur peut etre interpretee comme un id entier positif."""
    if value is None:
        return False
    if isinstance(value, bool):
        return False
    if isinstance(value, (int,)):
        return value > 0
    if isinstance(value, float):
        if pd.isna(value):
            return False
        return value.is_integer() and value > 0
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return False
        try:
            return int(s) > 0
        except ValueError:
            return False
    return False


def normalize_id(value: object) -> str:
    if isinstance(value, float):
        return str(int(value))
    return str(value).strip()


def normalize_siret(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, float):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def normalize_date(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    if not s:
        return ""
    if ISO_DATE_RE.match(s):
        return s
    try:
        ts = pd.to_datetime(s, dayfirst=True, errors="raise")
        return ts.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return s


def clean_sheet(df: pd.DataFrame) -> pd.DataFrame:
    if "id" not in df.columns:
        raise ValueError("Colonne 'id' manquante")

    mask = df["id"].map(is_valid_id)
    df = df.loc[mask].copy()

    df["id"] = df["id"].map(normalize_id)

    for col in df.columns:
        if col in SIRET_COLUMNS:
            df[col] = df[col].map(normalize_siret)
        elif col in DATE_COLUMNS:
            df[col] = df[col].map(normalize_date)
        else:
            df[col] = df[col].map(
                lambda v: "" if (v is None or (isinstance(v, float) and pd.isna(v))) else v
            )

    return df.reset_index(drop=True)


def export() -> dict[str, int]:
    xlsx = find_excel()
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    for sheet in SHEETS:
        df = pd.read_excel(xlsx, sheet_name=sheet, engine="openpyxl", dtype=object)
        df = clean_sheet(df)
        out = SEEDS_DIR / f"{sheet}.csv"
        df.to_csv(
            out,
            index=False,
            encoding="utf-8",
            sep=",",
            lineterminator="\n",
        )
        counts[sheet] = len(df)
        print(f"  ecrit {out.relative_to(BACKEND_DIR)} ({len(df)} lignes de donnees)")
    return counts


def main() -> int:
    try:
        counts = export()
    except Exception as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 1

    print("\nResume :")
    for sheet, n in counts.items():
        print(f"  - {sheet}.csv : {n} lignes de donnees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
