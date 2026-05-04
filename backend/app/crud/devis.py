"""CRUD Devis (Sprint 4 Lot 4b) — persistance + dénormalisation auto.

Lors d'un POST, on extrait du payload_input/payload_output les champs
dénormalisés (mode, format, machine_id, ht_total) pour permettre à la
liste paginée d'éviter le parsing JSON ligne par ligne.

Lors d'un duplicate, on copie le devis source en forçant statut='brouillon'
et en générant un nouveau numéro via numero_devis_service.
"""
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Client, Devis, Machine
from app.schemas.devis_persist import DevisCreate, DevisUpdate
from app.services.numero_devis_service import generate_next_numero


# ---------------------------------------------------------------------------
# Extraction des dénormalisés depuis payload_input / payload_output
# ---------------------------------------------------------------------------


def _extract_denormalised_fields(
    payload_input: dict, payload_output: dict
) -> dict:
    """Lit les champs nécessaires à la liste paginée depuis les payloads.

    Sources :
      mode_calcul, machine_id, format_h_mm, format_l_mm : payload_input
      ht_total_eur : payload_output (manuel direct, matching = 1er candidat
                     car HT identique entre candidats — postes ne dépendent
                     pas du cylindre dans le moteur Sprint 7 V2)
    """
    mode = payload_input.get("mode_calcul", "manuel")
    machine_id = payload_input["machine_id"]
    format_h = Decimal(str(payload_input["format_etiquette_hauteur_mm"]))
    format_l = Decimal(str(payload_input["format_etiquette_largeur_mm"]))

    if mode == "matching":
        candidats = payload_output.get("candidats") or []
        if not candidats:
            raise ValueError(
                "payload_output mode 'matching' doit contenir au moins 1 candidat"
            )
        ht = Decimal(str(candidats[0]["prix_vente_ht_eur"]))
    else:
        ht = Decimal(str(payload_output["prix_vente_ht_eur"]))

    return {
        "mode_calcul": mode,
        "machine_id": machine_id,
        "format_h_mm": format_h,
        "format_l_mm": format_l,
        "ht_total_eur": ht,
    }


# ---------------------------------------------------------------------------
# Helpers d'enrichissement (client_nom + machine_nom) pour les schémas Read
# ---------------------------------------------------------------------------


def _attach_relation_names(devis: Devis, db: Session) -> Devis:
    """Pose des attributs dynamiques `client_nom` / `machine_nom` sur le
    Devis avant sérialisation Pydantic from_attributes.
    """
    machine = db.get(Machine, devis.machine_id)
    setattr(devis, "machine_nom", machine.nom if machine else "")
    if devis.client_id is not None:
        client = db.get(Client, devis.client_id)
        setattr(
            devis,
            "client_nom",
            client.raison_sociale if client else None,
        )
    else:
        setattr(devis, "client_nom", None)
    return devis


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


SORT_MAP = {
    "date_desc": Devis.date_creation.desc(),
    "date_asc": Devis.date_creation.asc(),
    "numero_asc": Devis.numero.asc(),
    "ht_desc": Devis.ht_total_eur.desc(),
}


def list_devis(
    db: Session,
    entreprise_id: int,
    page: int = 1,
    per_page: int = 25,
    search: str | None = None,
    statut: str | None = None,
    sort: str = "date_desc",
) -> tuple[list[Devis], int]:
    """Liste paginée + tri + recherche scopée par entreprise (S12-C).

    Retourne (items_de_la_page, total_count).
    """
    query = (
        db.query(Devis)
        .outerjoin(Client, Devis.client_id == Client.id)
        .filter(Devis.entreprise_id == entreprise_id)
    )

    if statut:
        query = query.filter(Devis.statut == statut)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Devis.numero.ilike(like), Client.raison_sociale.ilike(like))
        )

    total = query.count()
    order_by = SORT_MAP.get(sort, SORT_MAP["date_desc"])
    items = (
        query.order_by(order_by)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    for d in items:
        _attach_relation_names(d, db)
    return items, total


def get_devis(db: Session, devis_id: int) -> Devis | None:
    devis = db.get(Devis, devis_id)
    if devis is None:
        return None
    return _attach_relation_names(devis, db)


def create_devis(
    db: Session, data: DevisCreate, entreprise_id: int
) -> Devis:
    """Crée un devis : génère numero auto + extrait dénormalisés.

    S12-C : `entreprise_id` injecté par le router via user.entreprise_id.
    """
    denorm = _extract_denormalised_fields(data.payload_input, data.payload_output)
    numero = generate_next_numero(db)
    devis = Devis(
        # S12-C : entreprise_id passé en paramètre par le router (user.entreprise_id)
        entreprise_id=entreprise_id,
        numero=numero,
        statut=data.statut,
        client_id=data.client_id,
        payload_input=data.payload_input,
        payload_output=data.payload_output,
        cylindre_choisi_z=data.cylindre_choisi_z,
        cylindre_choisi_nb_etiq=data.cylindre_choisi_nb_etiq,
        **denorm,
    )
    db.add(devis)
    db.commit()
    db.refresh(devis)
    return _attach_relation_names(devis, db)


def update_devis(
    db: Session, devis_id: int, data: DevisUpdate
) -> Devis | None:
    devis = db.get(Devis, devis_id)
    if devis is None:
        return None
    fields = data.model_dump(exclude_unset=True)
    # Si payload_input ou payload_output changent, on re-dérive dénormalisés.
    if "payload_input" in fields or "payload_output" in fields:
        new_input = fields.get("payload_input", devis.payload_input)
        new_output = fields.get("payload_output", devis.payload_output)
        denorm = _extract_denormalised_fields(new_input, new_output)
        fields.update(denorm)
    for field, value in fields.items():
        setattr(devis, field, value)
    db.commit()
    db.refresh(devis)
    return _attach_relation_names(devis, db)


def delete_devis(db: Session, devis_id: int) -> bool:
    devis = db.get(Devis, devis_id)
    if devis is None:
        return False
    db.delete(devis)
    db.commit()
    return True


def duplicate_devis(db: Session, devis_id: int) -> Devis | None:
    """Crée un nouveau devis à partir d'un existant.

    - Nouveau numéro
    - Statut forcé à 'brouillon'
    - payload_input / payload_output / client_id / cylindre / dénormalisés
      copiés
    """
    src = db.get(Devis, devis_id)
    if src is None:
        return None
    numero = generate_next_numero(db)
    nouveau = Devis(
        # S12-A : copie l'entreprise_id du devis source (préserve le scope tenant)
        entreprise_id=src.entreprise_id,
        numero=numero,
        statut="brouillon",
        client_id=src.client_id,
        payload_input=src.payload_input,
        payload_output=src.payload_output,
        mode_calcul=src.mode_calcul,
        cylindre_choisi_z=src.cylindre_choisi_z,
        cylindre_choisi_nb_etiq=src.cylindre_choisi_nb_etiq,
        ht_total_eur=src.ht_total_eur,
        format_h_mm=src.format_h_mm,
        format_l_mm=src.format_l_mm,
        machine_id=src.machine_id,
    )
    db.add(nouveau)
    db.commit()
    db.refresh(nouveau)
    return _attach_relation_names(nouveau, db)
