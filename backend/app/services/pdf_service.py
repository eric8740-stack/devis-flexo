"""Génération PDF des devis (Sprint 4 Lot 4e).

Pipeline : Jinja2 (template HTML) → weasyprint (HTML+CSS → PDF bytes).

Le template lit les champs dénormalisés du modèle Devis ET les données
détaillées du payload_output (postes, cout_revient, marge, prix_au_mille)
en s'adaptant au mode :
  - mode 'manuel'   → champs directs au top du payload_output
  - mode 'matching' → champs portés par le candidat sélectionné
                      (cylindre_choisi_z + cylindre_choisi_nb_etiq)

Si le mode est matching mais qu'aucun cylindre n'a été sélectionné
(devis_choisi_z is None), on prend le 1er candidat (HT identique entre
candidats Sprint 7 V2 — les postes ne dépendent pas du cylindre).
"""
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.models import Client, Devis, Machine

# weasyprint est importé lazy (à l'intérieur de generate_devis_pdf) pour
# que ce module soit importable même quand les libs natives GTK/Cairo/Pango
# ne sont pas installées (cas Windows local). Sur Linux/Docker prod elles
# sont installées via Dockerfile et le import lazy se fait sans erreur.

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _resolve_calc_fields(devis: Devis) -> dict:
    """Extrait postes / cout_revient / marge / prix_au_mille selon le mode.

    Returns dict avec les clés : postes, cout_revient (Decimal),
    marge_pct (Decimal), prix_au_mille (Decimal).
    """
    output = devis.payload_output or {}
    if devis.mode_calcul == "matching":
        candidats = output.get("candidats") or []
        if not candidats:
            raise ValueError(
                f"Devis {devis.numero} mode matching sans candidats"
            )
        # Cherche le candidat sélectionné, sinon prend le 1er.
        chosen = candidats[0]
        if devis.cylindre_choisi_z is not None:
            for c in candidats:
                if c.get("z") == devis.cylindre_choisi_z and c.get(
                    "nb_etiq_par_tour"
                ) == devis.cylindre_choisi_nb_etiq:
                    chosen = c
                    break
        return {
            "postes": chosen.get("postes", []),
            "cout_revient": Decimal(str(chosen.get("cout_revient_eur", "0"))),
            "marge_pct": Decimal(str(chosen.get("pct_marge_appliquee", "0"))),
            "prix_au_mille": Decimal(str(chosen.get("prix_au_mille_eur", "0"))),
        }
    return {
        "postes": output.get("postes", []),
        "cout_revient": Decimal(str(output.get("cout_revient_eur", "0"))),
        "marge_pct": Decimal(str(output.get("pct_marge_appliquee", "0"))),
        "prix_au_mille": Decimal(str(output.get("prix_au_mille_eur", "0"))),
    }


def generate_devis_pdf(devis: Devis, db: Session) -> bytes:
    """Génère le PDF d'un devis, retourne les bytes.

    Lookup machine + client par id (relations non chargées par défaut sur
    le modèle Devis Lot 4a — on ne paie pas le coût d'un eager join sur
    la liste).
    """
    # Import lazy : weasyprint charge gobject à l'import, qui crash sur
    # Windows sans GTK runtime. Importé ici, l'erreur ne survient qu'à
    # l'appel effectif de la génération PDF (Linux/Docker prod = OK).
    from weasyprint import HTML

    template = _env.get_template("devis_pdf.html")

    machine = db.get(Machine, devis.machine_id)
    machine_nom = machine.nom if machine else "—"
    client_nom: str | None = None
    if devis.client_id is not None:
        client = db.get(Client, devis.client_id)
        client_nom = client.raison_sociale if client else None

    calc = _resolve_calc_fields(devis)
    html_content = template.render(
        devis=devis,
        machine_nom=machine_nom,
        client_nom=client_nom,
        postes=calc["postes"],
        cout_revient=calc["cout_revient"],
        marge_pct=calc["marge_pct"],
        prix_au_mille=calc["prix_au_mille"],
        now=datetime.now(),
    )
    return HTML(string=html_content).write_pdf()
