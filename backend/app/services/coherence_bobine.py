"""Évaluation de la cohérence Ø extérieur ↔ nb étiquettes par bobine.

Orchestre les helpers `bat_calculs` (SSOT mm — mêmes formules que la
VUE B / le 242 mm visible côté UI) pour produire une alerte
non bloquante destinée au formulaire brief client.

Deux checks indépendants :

1. **Cohérence géométrique (saisi vs saisi)** — nb étiquettes saisi
   tient-il dans le Ø extérieur saisi, à mandrin et épaisseur donnés ?
     - nb > nb_max × (1 + tol) → ⚠️ « warning » (sous-dimensionné)
     - nb < nb_max × (1 − tol) → ℹ️ « info » (bobine non pleine)
     - sinon                   → ✅ « ok » (silencieux)
2. **Fit physique (saisi vs profil client)** — Ø saisi > Ø max bobine
   acceptée par la machine de pose du client ? Si oui → ⚠️ « fit ».

Souveraineté commerciale : alerte JAMAIS bloquante, le commercial
peut forcer. UX : alerte sous le champ, color-codée, mobile-first.

Épaisseur matière : si le catalogue ne porte pas la valeur, fallback
sur `EPAISSEUR_FALLBACK_UM` (150 µm, cohérent avec le défaut
`OptimisationCalculerRequest.epaisseur_matiere_um`). Source remontée
dans la réponse pour transparence.
"""
from dataclasses import dataclass
from typing import Literal

from app.services.optimisation.bat_calculs import (
    calcul_diametre_requis_pour_nb_etiq,
    calcul_nb_max_etiq_pour_diametre,
)

# Tolérance de cohérence par défaut (3 %). À terme : param entreprise.
TOLERANCE_PCT_DEFAULT: float = 3.0

# Épaisseur de matière par défaut quand le catalogue ne la porte pas.
# Aligné sur `OptimisationCalculerRequest.epaisseur_matiere_um` (150 µm).
EPAISSEUR_FALLBACK_UM: float = 150.0


Severity = Literal["ok", "info", "warning"]
EpaisseurSource = Literal["catalogue", "fallback"]


@dataclass(frozen=True)
class CoherenceBobineResult:
    """Résultat agrégé du check de cohérence (toujours renvoyé, même OK)."""

    # Check 1 — cohérence géométrique saisi vs saisi.
    severity: Severity
    message: str  # "" si severity = "ok"
    nb_max: int  # nb max d'étiq physiquement enroulables dans Ø saisi
    diametre_requis_mm: int  # Ø ext requis pour caser nb saisi

    # Check 2 — fit machine de pose client (optionnel, None si pas de profil).
    fit_severity: Severity | None
    fit_message: str | None

    # Transparence sur l'épaisseur utilisée.
    epaisseur_appliquee_um: float
    epaisseur_source: EpaisseurSource


def _resoudre_epaisseur(
    epaisseur_catalogue_um: float | None,
) -> tuple[float, EpaisseurSource]:
    """Fallback : si le catalogue ne porte pas d'épaisseur, défaut 150 µm."""
    if epaisseur_catalogue_um is not None and epaisseur_catalogue_um > 0:
        return float(epaisseur_catalogue_um), "catalogue"
    return EPAISSEUR_FALLBACK_UM, "fallback"


def evaluer_coherence_bobine(
    *,
    diametre_ext_saisi_mm: float,
    nb_etiq_saisi: int,
    mandrin_mm: int,
    pas_mm: float,
    epaisseur_catalogue_um: float | None,
    diametre_max_client_mm: float | None = None,
    tolerance_pct: float = TOLERANCE_PCT_DEFAULT,
) -> CoherenceBobineResult:
    """Évalue la cohérence Ø ↔ nb étiq et le fit machine client.

    Tous les calculs passent par les helpers `bat_calculs` (SSOT mm) :
    aucune formule n'est dupliquée dans ce module, ni côté frontend.
    """
    epaisseur_um, source = _resoudre_epaisseur(epaisseur_catalogue_um)

    # Check 1 — cohérence géométrique.
    nb_max = calcul_nb_max_etiq_pour_diametre(
        diametre_ext_mm=diametre_ext_saisi_mm,
        mandrin_mm=mandrin_mm,
        epaisseur_matiere_um=epaisseur_um,
        pas_mm=pas_mm,
    )
    diametre_requis_mm = calcul_diametre_requis_pour_nb_etiq(
        nb_etiq=nb_etiq_saisi,
        mandrin_mm=mandrin_mm,
        epaisseur_matiere_um=epaisseur_um,
        pas_mm=pas_mm,
    )
    tol = tolerance_pct / 100.0
    if nb_max <= 0:
        severity: Severity = "warning"
        message = (
            f"Ø {diametre_ext_saisi_mm:g} mm incompatible avec mandrin "
            f"{mandrin_mm} mm — aucune étiquette ne peut être enroulée. "
            f"Ø requis ≈ {diametre_requis_mm} mm pour {nb_etiq_saisi} étiq."
        )
    elif nb_etiq_saisi > nb_max * (1 + tol):
        severity = "warning"
        message = (
            f"Ø {diametre_ext_saisi_mm:g} mm permet ≈ {nb_max} étiq. "
            f"Tu en as saisi {nb_etiq_saisi}. "
            f"Ø requis ≈ {diametre_requis_mm} mm."
        )
    elif nb_etiq_saisi < nb_max * (1 - tol):
        severity = "info"
        message = (
            f"Ø {diametre_ext_saisi_mm:g} mm permet jusqu'à {nb_max} étiq "
            f"— bobine non pleine ({nb_etiq_saisi})."
        )
    else:
        severity = "ok"
        message = ""

    # Check 2 — fit machine de pose client (séparé, indépendant).
    fit_severity: Severity | None = None
    fit_message: str | None = None
    if diametre_max_client_mm is not None and diametre_max_client_mm > 0:
        if diametre_ext_saisi_mm > diametre_max_client_mm:
            fit_severity = "warning"
            fit_message = (
                f"Ø {diametre_ext_saisi_mm:g} mm > Ø max machine de pose "
                f"({diametre_max_client_mm:g} mm) : la bobine ne rentre pas."
            )
        else:
            fit_severity = "ok"
            fit_message = None

    return CoherenceBobineResult(
        severity=severity,
        message=message,
        nb_max=nb_max,
        diametre_requis_mm=diametre_requis_mm,
        fit_severity=fit_severity,
        fit_message=fit_message,
        epaisseur_appliquee_um=epaisseur_um,
        epaisseur_source=source,
    )
