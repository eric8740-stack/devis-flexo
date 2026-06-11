"""Service lien devis↔stock (Module Stock S3) — LECTURE SEULE côté devis.

Calcule le besoin matière d'un devis sauvegardé (réutilise le `ml_total` du
moteur, identique au calcul F `bobinage.ml_total`) et propose en FIFO les bobines
qui le couvrent. N'écrit rien (la consommation effective est faite par le routeur,
transactionnellement, via `MouvementStock`).

Le modèle Devis n'a pas de `matiere_id` direct : la matière vient de ses
`LotProduction`. FIFO = date d'entrée en stock croissante ; `Bobine.date_creation`
fait foi (une ligne bobine est créée à sa réception, cf. S1).
"""
from __future__ import annotations

from app.crud.devis import _construire_devis_input_pour_lot
from app.models import Bobine, Devis, MouvementStock, User
from app.services.scope_service import scope_to_entreprise
from sqlalchemy.orm import Session


def etat_consommation(
    db: Session, devis: Devis, user: User
) -> tuple[bool, int, list[MouvementStock]]:
    """`(deja_consomme, consomme_ml, mouvements)` du devis, déduit des mouvements.

    `consomme_ml` = NET encore consommé (Σ sortie − Σ entree d'annulation) pour ce
    `devis_id`. `deja_consomme` = `consomme_ml > 0`. Pas de flag sur Devis.
    """
    mvts = (
        scope_to_entreprise(db.query(MouvementStock), MouvementStock, user)
        .filter(MouvementStock.devis_id == devis.id)
        .order_by(MouvementStock.date_creation.asc(), MouvementStock.id.asc())
        .all()
    )
    net = sum((m.ml if m.type == "sortie" else -m.ml) for m in mvts)
    return net > 0, max(0, net), mvts


def besoin_consommation(db: Session, devis: Devis) -> tuple[int, int | None, float]:
    """`(ml_requis, matiere_id, laize_requise)` pour un devis sauvegardé.

    Somme le `ml_total` (calcul moteur = `bobinage.ml_total` du Lot F) sur les
    lots ; matière = 1er lot ; laize requise = max des laizes papier. Best-effort :
    un lot non chiffrable (onboarding incomplet) est ignoré.
    """
    ml_requis = 0
    matiere_id: int | None = None
    laize_requise = 0.0
    for lot in sorted(devis.lots_production, key=lambda lp: lp.ordre):
        try:
            di = _construire_devis_input_pour_lot(
                lot, devis.payload_input or {}, db, devis.entreprise_id
            )
        except (ValueError, ArithmeticError):
            continue
        ml_requis += int(di.ml_total)
        if matiere_id is None:
            matiere_id = lot.matiere_id
        laize_requise = max(laize_requise, float(di.laize_papier_mm or 0))
    return ml_requis, matiere_id, laize_requise


def proposition_fifo(db: Session, devis: Devis, user: User) -> dict:
    """Propose en FIFO les bobines couvrant le besoin du devis.

    Critères : `matiere_id` == matière du devis, `laize_mm >= laize_requise`,
    `statut == en_stock`, `ml_restant > 0`, triées par `date_creation` croissante.
    Allocation gloutonne jusqu'à couvrir `ml_requis`.
    """
    ml_requis, matiere_id, laize_requise = besoin_consommation(db, devis)
    deja_consomme, consomme_ml, mvts = etat_consommation(db, devis, user)
    lignes: list[dict] = []
    reste = ml_requis
    if matiere_id is not None and ml_requis > 0:
        bobines = (
            scope_to_entreprise(db.query(Bobine), Bobine, user)
            .filter(
                Bobine.matiere_id == matiere_id,
                Bobine.laize_mm >= laize_requise,
                Bobine.ml_restant > 0,
                Bobine.statut == "en_stock",
            )
            .order_by(Bobine.date_creation.asc(), Bobine.id.asc())
            .all()
        )
        for b in bobines:
            if reste <= 0:
                break
            propose = min(reste, b.ml_restant)
            lignes.append(
                {
                    "bobine_id": b.id,
                    "emplacement": f"{b.rangee}.{b.etage}.{b.position}",
                    "laize_mm": float(b.laize_mm),
                    "ml_restant": b.ml_restant,
                    "ml_propose": propose,
                }
            )
            reste -= propose
    return {
        "ml_requis": float(ml_requis),
        "lignes": lignes,
        "stock_suffisant": reste <= 0,
        "manque_ml": float(max(0, reste)),
        "deja_consomme": deja_consomme,
        "consomme_ml": float(consomme_ml),
        "mouvements": mvts,
    }
