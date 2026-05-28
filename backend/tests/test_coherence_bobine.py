"""Tests — alerte cohérence Ø extérieur ↔ nb étiquettes/bobine.

Couvre :
- helpers inverses dans `bat_calculs` (nb_max + diamètre_requis)
  → cohérence stricte avec la forward `calcul_diametre_bobine` (SSOT mm) ;
- service `evaluer_coherence_bobine` :
    * cas cohérent (silencieux, severity=ok),
    * Ø trop petit (warning + Ø requis exposé),
    * Ø > Dmax client (fit warning séparé) ;
- endpoint POST /api/devis/coherence-bobine (smoke).

Pas de check_bareme cost_engine : géométrique pur, pas de coût.
"""
import math

from fastapi.testclient import TestClient

from app.main import app
from app.services.coherence_bobine import (
    EPAISSEUR_FALLBACK_UM,
    evaluer_coherence_bobine,
)
from app.services.optimisation.bat_calculs import (
    calcul_diametre_bobine,
    calcul_diametre_requis_pour_nb_etiq,
    calcul_nb_max_etiq_pour_diametre,
)


_client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers inverses (round-trip avec le forward)
# ---------------------------------------------------------------------------


def test_nb_max_round_trip_avec_diametre_bobine():
    """nb_max(D) doit donner ≈ nb_etiq utilisé pour générer D via forward.

    On part de nb_etiq=4000, pas=80 mm, mandrin=76, épaisseur 150 µm,
    laize papier 100 mm. forward → D ; on demande nb_max(D) qui doit
    valoir nb_etiq (à 1 près, arrondi).
    """
    nb_etiq = 4000
    pas_mm = 80.0
    mandrin_mm = 76
    epaisseur_um = 150.0
    ml_m = nb_etiq * pas_mm / 1000  # 320 m
    d_calc = calcul_diametre_bobine(
        ml_total_m=ml_m,
        epaisseur_matiere_um=epaisseur_um,
        mandrin_mm=mandrin_mm,
        laize_papier_mm=100.0,
    )
    nb_max = calcul_nb_max_etiq_pour_diametre(
        diametre_ext_mm=float(d_calc),
        mandrin_mm=mandrin_mm,
        epaisseur_matiere_um=epaisseur_um,
        pas_mm=pas_mm,
    )
    # Tolérance ±1 % : le forward arrondit D à l'entier (±0.5 mm), or
    # nb_max varie en D² → l'amplification est ≈ 2 × D × ΔD / D² ≈ 1 %
    # pour ces valeurs. Pas un défaut métier, juste l'aller-retour.
    assert abs(nb_max - nb_etiq) / nb_etiq < 0.01, (d_calc, nb_max, nb_etiq)


def test_diametre_requis_round_trip():
    """D_requis(nb) ≈ D forward(ml = nb × pas / 1000)."""
    nb_etiq = 5000
    pas_mm = 80.0
    mandrin_mm = 76
    epaisseur_um = 150.0
    d_forward = calcul_diametre_bobine(
        ml_total_m=nb_etiq * pas_mm / 1000,
        epaisseur_matiere_um=epaisseur_um,
        mandrin_mm=mandrin_mm,
        laize_papier_mm=100.0,
    )
    d_requis = calcul_diametre_requis_pour_nb_etiq(
        nb_etiq=nb_etiq,
        mandrin_mm=mandrin_mm,
        epaisseur_matiere_um=epaisseur_um,
        pas_mm=pas_mm,
    )
    # Même arrondi (round) côté forward et inverse → strict ±1 mm.
    assert abs(d_requis - d_forward) <= 1


def test_nb_max_garde_fou_diametre_inferieur_mandrin():
    assert calcul_nb_max_etiq_pour_diametre(50.0, 76, 150.0, 80.0) == 0


def test_diametre_requis_garde_fou_nb_zero():
    """nb=0 → renvoie le mandrin (rien à enrouler)."""
    assert calcul_diametre_requis_pour_nb_etiq(0, 76, 150.0, 80.0) == 76


# ---------------------------------------------------------------------------
# Service evaluer_coherence_bobine — cas brief
# ---------------------------------------------------------------------------


def _coherent_inputs():
    """Saisie cohérente : on calcule le D forward exact pour nb_etiq donné."""
    nb_etiq = 4000
    pas_mm = 80.0
    mandrin_mm = 76
    epaisseur_um = 150.0
    d_exact = calcul_diametre_bobine(
        ml_total_m=nb_etiq * pas_mm / 1000,
        epaisseur_matiere_um=epaisseur_um,
        mandrin_mm=mandrin_mm,
        laize_papier_mm=100.0,
    )
    return {
        "diametre_ext_saisi_mm": float(d_exact),
        "nb_etiq_saisi": nb_etiq,
        "mandrin_mm": mandrin_mm,
        "pas_mm": pas_mm,
        "epaisseur_catalogue_um": epaisseur_um,
    }


def test_cas_coherent_silencieux():
    """Ø et nb_etiq cohérents (à 3 % près) → severity = ok, message vide."""
    res = evaluer_coherence_bobine(**_coherent_inputs())
    assert res.severity == "ok"
    assert res.message == ""
    assert res.fit_severity is None  # pas de profil client → pas de check fit


def test_cas_diametre_trop_petit_warning_et_diametre_requis():
    """Ø saisi nettement insuffisant pour le nb d'étiq → warning + Ø requis."""
    inp = _coherent_inputs()
    # On garde nb_etiq=4000 mais on force Ø à un niveau qui ne peut tenir
    # qu'environ 2000 étiq → 4000 dépasse > tolérance 3 %.
    inp["diametre_ext_saisi_mm"] = 150.0  # << Ø_exact (~242 mm)
    res = evaluer_coherence_bobine(**inp)
    assert res.severity == "warning"
    assert "150" in res.message
    assert str(res.diametre_requis_mm) in res.message
    # Ø requis doit être > Ø saisi (sinon, le warning n'aurait pas de sens).
    assert res.diametre_requis_mm > inp["diametre_ext_saisi_mm"]


def test_cas_fit_machine_client_depasse():
    """Ø saisi > Ø max machine client (profil sprint 16) → fit warning."""
    inp = _coherent_inputs()
    inp["diametre_max_client_mm"] = inp["diametre_ext_saisi_mm"] - 10.0
    res = evaluer_coherence_bobine(**inp)
    # Check 1 reste OK (saisie auto-cohérente).
    assert res.severity == "ok"
    # Check 2 (fit) doit warner.
    assert res.fit_severity == "warning"
    assert "ne rentre pas" in (res.fit_message or "").lower()


def test_fallback_epaisseur_si_catalogue_absent():
    """Pas d'épaisseur catalogue → fallback 150 µm + source signalée."""
    inp = _coherent_inputs()
    inp["epaisseur_catalogue_um"] = None
    res = evaluer_coherence_bobine(**inp)
    assert res.epaisseur_source == "fallback"
    assert math.isclose(res.epaisseur_appliquee_um, EPAISSEUR_FALLBACK_UM)


def test_info_si_bobine_non_pleine():
    """nb saisi << nb_max(Ø) → severity = info."""
    inp = _coherent_inputs()
    # Multiplie Ø par 1.5 → nb_max bondit, mais on garde nb_etiq.
    inp["diametre_ext_saisi_mm"] *= 1.5
    res = evaluer_coherence_bobine(**inp)
    assert res.severity == "info"
    assert "non pleine" in res.message.lower()


# ---------------------------------------------------------------------------
# Endpoint smoke
# ---------------------------------------------------------------------------


def test_endpoint_coherent_renvoie_200_severity_ok():
    payload = _coherent_inputs()
    r = _client.post("/api/devis/coherence-bobine", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["severity"] == "ok"
    assert data["epaisseur_source"] == "catalogue"


def test_endpoint_warning_diametre_trop_petit():
    payload = _coherent_inputs()
    payload["diametre_ext_saisi_mm"] = 150.0
    r = _client.post("/api/devis/coherence-bobine", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["severity"] == "warning"
    assert data["diametre_requis_mm"] > 150


def test_endpoint_fit_warning_si_dmax_client_depasse():
    payload = _coherent_inputs()
    payload["diametre_max_client_mm"] = payload["diametre_ext_saisi_mm"] - 10.0
    r = _client.post("/api/devis/coherence-bobine", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["fit_severity"] == "warning"
    assert "ne rentre pas" in (data["fit_message"] or "").lower()
