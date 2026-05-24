"""Module de cohérence sens d'enroulement — Sprint 15 Lot 4 (FlexoCheck).

Diagnostique l'écart entre le sens d'enroulement observé par l'IA sur le
1er tirage et le sens demandé (LotProduction du devis ou paramètre
opérateur). Construit le triplet (`coherence_sens`, `action_correction_sens`,
`message_alerte`) à partir de la convention SE1-SE8 verrouillée.

**Sacred** : ce module est consommateur lecture seule de
`app/services/rotation_se.py`. Aucun import ne touche au mapping SE
canonique.

Règles métier (flexographie, brief Lot 4) :

  - Info manquante (1 des deux sens absent) → coherence=None, pas d'action,
    pas d'alerte (l'opérateur valide à l'œil sans aide IA).
  - Identique → coherence=True, pas d'action, pas d'alerte (vert).
  - Différent + niveau_confiance IA = "faible" → confirmation_client.
    L'IA n'est pas fiable, on demande à un humain (chef d'atelier ou
    client) de trancher.
  - Différent + face opposée (paires SE1↔SE5, SE2↔SE6, SE3↔SE7, SE4↔SE8)
    → inversion_cliche. Le cliché est physiquement posé à l'envers
    (face extérieur vs intérieur) : seule l'inversion du cliché remet
    l'orientation correcte.
  - Différent + même face, rotation différente → ajustement_rebobineuse.
    L'orientation peut être rattrapée en reconfigurant la rebobineuse,
    sans démonter le cliché.
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.services.rotation_se import get_libelle_officiel


# SE1-SE4 = face Extérieur (cliché posé endroit, à l'extérieur du rouleau).
# SE5-SE8 = face Intérieur (cliché posé mirror, à l'intérieur du rouleau).
# Convention métier verrouillée 18/05/2026 (cf. rotation_se.py).
FACE_EXTERIEUR = "ext"
FACE_INTERIEUR = "int"

_PATTERN_SE = re.compile(r"^SE([1-8])$", re.IGNORECASE)


def parse_se(label: str | None) -> int | None:
    """Parse `"SE1"` … `"SE8"` en int 1..8. Renvoie None pour tout autre input.

    Tolère casse / espaces : "se3", " SE7 ", "SE8" sont tous acceptés.
    """
    if not label:
        return None
    match = _PATTERN_SE.match(label.strip())
    if match is None:
        return None
    return int(match.group(1))


def face_du_sens(sens: int) -> str:
    """Renvoie "ext" pour SE1-SE4, "int" pour SE5-SE8.

    Pas de validation de borne ici — on assume `sens` ∈ [1, 8]. Le parsing
    parse_se() reste responsable de la validation amont.
    """
    return FACE_EXTERIEUR if 1 <= sens <= 4 else FACE_INTERIEUR


def diagnostiquer_coherence(
    sens_demande: str | None,
    sens_detecte: str | None,
    niveau_confiance: str | None,
) -> dict[str, Any]:
    """Renvoie le diagnostic structuré.

    Returns:
      dict avec clés :
        - coherence_sens : bool | None
        - action_correction_sens : str | None
          (`inversion_cliche` / `ajustement_rebobineuse` / `confirmation_client`)
        - message_alerte : str | None (message UI quand alerte)
    """
    se_demande = parse_se(sens_demande)
    se_detecte = parse_se(sens_detecte)

    if se_demande is None or se_detecte is None:
        return {
            "coherence_sens": None,
            "action_correction_sens": None,
            "message_alerte": None,
        }

    if se_demande == se_detecte:
        return {
            "coherence_sens": True,
            "action_correction_sens": None,
            "message_alerte": None,
        }

    # Incohérence détectée — on construit un message qui rappelle la
    # convention pour aider l'opérateur à comprendre le diagnostic.
    libelle_demande = get_libelle_officiel(se_demande)
    libelle_detecte = get_libelle_officiel(se_detecte)
    base = (
        f"Sens détecté SE{se_detecte} ({libelle_detecte}) "
        f"ne correspond pas au sens demandé SE{se_demande} ({libelle_demande})."
    )

    # Règle 1 : confiance IA faible → demande humain (prime sur tout).
    if niveau_confiance == "faible":
        return {
            "coherence_sens": False,
            "action_correction_sens": "confirmation_client",
            "message_alerte": (
                f"{base} L'analyse IA n'est pas fiable "
                f"(niveau de confiance faible) — confirmation client recommandée."
            ),
        }

    # Règle 2 : face opposée → cliché posé à l'envers (mirror).
    if face_du_sens(se_demande) != face_du_sens(se_detecte):
        return {
            "coherence_sens": False,
            "action_correction_sens": "inversion_cliche",
            "message_alerte": (
                f"{base} Face cliché opposée (paires SE1↔SE5, SE2↔SE6, "
                f"SE3↔SE7, SE4↔SE8) — cliché posé à l'envers, inversion requise."
            ),
        }

    # Règle 3 : même face, rotation différente → rebobineuse.
    return {
        "coherence_sens": False,
        "action_correction_sens": "ajustement_rebobineuse",
        "message_alerte": (
            f"{base} Même face cliché, rotation différente — "
            f"ajustement rebobineuse possible sans démontage du cliché."
        ),
    }


def sens_demande_du_devis(db: Session, devis_id: int) -> str | None:
    """Fallback : sens du 1er lot du devis (ordre minimal).

    Si l'opérateur n'a pas explicitement fourni `sens_demande` au moment
    du POST /controle-bat/, on prend le `sens_enroulement` du 1er lot de
    production rattaché au devis. Renvoie None s'il n'y a pas de lot
    (devis legacy mono-config pré-multi-lots) ou si la valeur est hors
    plage [1, 8].

    Import lazy de LotProduction pour éviter une dépendance circulaire
    entre services et models au boot.
    """
    from app.models import LotProduction

    lot = (
        db.query(LotProduction)
        .filter_by(devis_id=devis_id)
        .order_by(LotProduction.ordre.asc())
        .first()
    )
    if lot is None:
        return None
    if not (1 <= lot.sens_enroulement <= 8):
        return None
    return f"SE{lot.sens_enroulement}"
