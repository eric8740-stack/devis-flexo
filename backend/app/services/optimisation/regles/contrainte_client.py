"""Règle contrainte client Sprint 13 S13.D.6 — PLANCHER INTERVALLE DEV.

CdC § 786-841 : le client final a sa propre contrainte d'intervalle dev
imposée par sa machine d'étiquetage (cellule photoélectrique qui doit
distinguer chaque étiquette). Si l'écart est trop faible côté pose
client, la cellule confond deux étiquettes consécutives → pose ratée.

Règle : intervalle_dev_min_applique = MAX(min_imprimeur, min_client).

Pédagogie commerciale : si la contrainte vient du client, on affiche un
message qui explique pourquoi on n'a pas pu optimiser plus. Le PDF devis
peut mentionner explicitement "Intervalle requis par votre machine de
pose XYZ" pour préempter la question.
"""
from __future__ import annotations


def intervalle_dev_min_effectif(
    intervalle_min_imprimeur: float, intervalle_min_client: float
) -> dict:
    """Calcule l'intervalle dev minimum réellement applicable et trace
    si la contrainte vient du client.

    Args:
      intervalle_min_imprimeur : minimum technique imprimerie
        (typiquement 2 mm, paramètre entreprise).
      intervalle_min_client : minimum imposé par la machine de pose
        du client (0 si non renseigné).

    Returns:
      dict avec :
        - intervalle_dev_min_applique_mm (float) : MAX des deux.
        - est_contrainte_par_client (bool) : True si client > imprimeur.
        - message (str | None) : message pédagogique si contrainte
          client, sinon None.
    """
    applique = max(intervalle_min_imprimeur, intervalle_min_client)
    par_client = intervalle_min_client > intervalle_min_imprimeur

    message: str | None = None
    if par_client:
        message = (
            f"Intervalle {applique:.1f} mm imposé par votre machine "
            f"de pose. Sans cette contrainte, l'imprimeur pourrait "
            f"optimiser à {intervalle_min_imprimeur:.1f} mm."
        )

    return {
        "intervalle_dev_min_applique_mm": applique,
        "est_contrainte_par_client": par_client,
        "message": message,
    }
