"""Lot F2 back — nb bobines IMPOSÉ sur le bloc bobinage du POST /preview.

Couvre : `nb_bobines_impose` → ml/bobine DÉRIVÉ (ceil) + Ø recalculé dessus
(bat_calculs lecture pure) ; imposé + ml_par_bobine fournis ensemble →
l'imposé PRIME + alerte info (souveraineté non bloquante, jamais de 422) ;
alerte `depasse_max` fonctionnelle sur le ml dérivé ; granularité production
par paquets de n_laize (MÊME source que le planificateur #73 : poses en laize
post-optim, `nb_filles` en mode sans outil) → `nb_bobines_production` /
`surplus_bobines` ADDITIFS + alerte info si non multiple ; non-régression
Lot F stricte (sans imposé, bloc bobinage octet pour octet identique —
clés F2 ABSENTES). AUCUN chiffrage touché (cost_engine intouché).
"""
import math

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import CylindreMagnetique, Machine, Matiere
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _ids() -> tuple[int, int, int]:
    """(matiere_id, cylindre_id, presse_id) du tenant démo — cylindre + matière
    permettent au moteur de produire un `devis_input` (ml_total réel)."""
    _onboard_if_needed()
    with SessionLocal() as db:
        mat = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(Matiere.id)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(CylindreMagnetique.id)
            .first()
        )
        presse = (
            db.query(Machine)
            .filter_by(entreprise_id=1, actif=True, type_machine="presse")
            .order_by(Machine.id)
            .first()
        )
        return mat.id, cyl.id, presse.id


def _set_machine(presse_id: int, **cols) -> dict:
    """Mute la presse et renvoie les valeurs AVANT (pour restauration)."""
    with SessionLocal() as db:
        m = db.get(Machine, presse_id)
        avant = {k: getattr(m, k) for k in cols}
        for k, v in cols.items():
            setattr(m, k, v)
        db.commit()
        return avant


def _base(mat_id: int, cyl_id: int, **extra) -> dict:
    return {
        "laize": 50, "dev": 40, "quantite": 100_000,
        "cylindre_id": cyl_id, "matiere_id": mat_id, **extra,
    }


def _preview(payload: dict) -> dict:
    r = client.post("/api/devis/preview", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _bobinage(payload: dict) -> dict:
    return _preview(payload)["bobinage"]


def test_impose_derive_ml_par_bobine_et_diametre():
    """Imposé → nb_bobines = imposé, ml/bobine = ceil(ml_total / imposé), Ø
    recalculé sur le ml dérivé (identique à une requête explicite au même ml)."""
    mat_id, cyl_id, presse_id = _ids()
    _set_machine(presse_id, diametre_max_bobine_mm=1100)
    b = _bobinage(_base(mat_id, cyl_id, nb_bobines_impose=5))
    assert b is not None
    assert b["nb_bobines"] == 5
    assert b["ml_par_bobine"] == max(1, math.ceil(b["ml_total"] / 5))
    # Le dérivé couvre le métrage total (arrondi SUP, jamais tronqué).
    assert b["ml_par_bobine"] * 5 >= b["ml_total"]
    # Ø recalculé sur le ml dérivé : STRICTEMENT le même Ø qu'une requête
    # Lot F explicite avec ml_par_bobine = dérivé (même bat_calculs).
    b_equiv = _bobinage(_base(mat_id, cyl_id, ml_par_bobine=b["ml_par_bobine"]))
    assert b_equiv["diametre_bobine_mm"] == b["diametre_bobine_mm"]
    # Plus de bobines imposées → bobines plus courtes → Ø plus petit.
    b20 = _bobinage(_base(mat_id, cyl_id, nb_bobines_impose=20))
    assert b20["nb_bobines"] == 20
    assert b20["diametre_bobine_mm"] < b["diametre_bobine_mm"]


def test_impose_prime_sur_ml_par_bobine_avec_alerte_info():
    """Imposé + ml_par_bobine fournis ENSEMBLE → l'imposé prime (ml/bobine
    dérivé, pas le saisi) + alerte info tracée. Jamais de 422 (Règle 7)."""
    mat_id, cyl_id, _ = _ids()
    body = _preview(_base(mat_id, cyl_id, nb_bobines_impose=4, ml_par_bobine=700))
    b = body["bobinage"]
    assert b["nb_bobines"] == 4
    assert b["ml_par_bobine"] == max(1, math.ceil(b["ml_total"] / 4))
    assert any(
        a["niveau"] == "info" and "prime sur le ml/bobine" in a["message"]
        for a in body["alertes"]
    )


def test_depasse_max_fonctionne_sur_ml_derive():
    """L'alerte `depasse_max` existante reste fonctionnelle sur le ml DÉRIVÉ :
    1 grosse bobine imposée dépasse le Ø max, 30 petites non."""
    mat_id, cyl_id, presse_id = _ids()
    avant = _set_machine(presse_id, diametre_max_bobine_mm=5000)
    try:
        d1 = _bobinage(_base(mat_id, cyl_id, nb_bobines_impose=1))["diametre_bobine_mm"]
        d30 = _bobinage(_base(mat_id, cyl_id, nb_bobines_impose=30))["diametre_bobine_mm"]
        assert d30 < d1
        seuil = (d1 + d30) // 2
        _set_machine(presse_id, diametre_max_bobine_mm=seuil)
        body_1 = _preview(_base(mat_id, cyl_id, nb_bobines_impose=1))
        assert body_1["bobinage"]["depasse_max"] is True
        assert any("max presse" in a["message"] for a in body_1["alertes"])
        body_30 = _preview(_base(mat_id, cyl_id, nb_bobines_impose=30))
        assert body_30["bobinage"]["depasse_max"] is False
        assert not any("max presse" in a["message"] for a in body_30["alertes"])
    finally:
        _set_machine(presse_id, **avant)


def test_surplus_paquets_n_laize_avec_outil():
    """Imposé NON multiple de n_laize (poses en laize post-optim) → production
    au multiple supérieur + surplus + alerte info « paquets de N »."""
    mat_id, cyl_id, presse_id = _ids()
    # laize_utile 165 mm, étiquette 50 + intervalle 3 → n_laize = floor(165/53) = 3.
    avant = _set_machine(presse_id, laize_utile_mm=165, diametre_max_bobine_mm=1100)
    try:
        body = _preview(_base(mat_id, cyl_id, nb_bobines_impose=7))
        b = body["bobinage"]
        assert b["nb_bobines"] == 7  # la demande client reste affichée
        assert b["nb_bobines_production"] == 9  # multiple supérieur de 3
        assert b["surplus_bobines"] == 2
        assert any(
            a["niveau"] == "info" and "paquets de 3" in a["message"]
            for a in body["alertes"]
        )
    finally:
        _set_machine(presse_id, **avant)


def test_multiple_exact_surplus_zero_sans_alerte():
    """Imposé multiple exact de n_laize → surplus 0, PAS d'alerte paquets."""
    mat_id, cyl_id, presse_id = _ids()
    avant = _set_machine(presse_id, laize_utile_mm=165, diametre_max_bobine_mm=1100)
    try:
        body = _preview(_base(mat_id, cyl_id, nb_bobines_impose=9))
        b = body["bobinage"]
        assert b["nb_bobines_production"] == 9
        assert b["surplus_bobines"] == 0
        assert not any("paquets" in a["message"] for a in body["alertes"])
    finally:
        _set_machine(presse_id, **avant)


def test_non_regression_lot_f_sans_impose():
    """Sans `nb_bobines_impose` → bloc bobinage STRICTEMENT identique au Lot F :
    mêmes clés (les champs F2 sont ABSENTS du JSON, pas nuls), mêmes formules."""
    mat_id, cyl_id, presse_id = _ids()
    _set_machine(presse_id, diametre_max_bobine_mm=1100, temps_changement_bobine_min=15)
    b = _bobinage(_base(mat_id, cyl_id, ml_par_bobine=700))
    # Contrat de sortie Lot F, octet pour octet : AUCUNE clé F2.
    assert set(b.keys()) == {
        "ml_total", "m2_total", "ml_par_bobine", "nb_bobines",
        "diametre_bobine_mm", "diametre_mandrin_mm", "diametre_max_presse_mm",
        "depasse_max", "nb_changements", "temps_arret_min",
    }
    # Formules Lot F inchangées.
    assert b["ml_par_bobine"] == 700
    assert b["nb_bobines"] == math.ceil(b["ml_total"] / 700)
    assert b["nb_changements"] == max(0, b["nb_bobines"] - 1)
    assert b["temps_arret_min"] == b["nb_changements"] * 15


def test_sans_outil_n_laize_egale_nb_filles():
    """Mode sans outil : la granularité production suit `nb_filles` (même
    source que le planificateur — pas de poses outil en sans outil)."""
    mat_id, _, _ = _ids()
    payload = {
        "laize": 50, "dev": 40, "quantite": 10_000,
        "matiere_id": mat_id, "epaisseur_um": 90,
        "mode_sans_outil": True, "laize_stock_mm": 250,
    }
    nf = _preview(payload)["geometrie"]["nb_filles"]
    assert nf is not None and nf >= 2
    body = _preview({**payload, "nb_bobines_impose": nf + 1})
    b = body["bobinage"]
    assert b is not None
    assert b["nb_bobines"] == nf + 1
    assert b["nb_bobines_production"] == 2 * nf  # multiple supérieur de nf
    assert b["surplus_bobines"] == nf - 1
    assert any(
        a["niveau"] == "info" and f"paquets de {nf}" in a["message"]
        for a in body["alertes"]
    )
