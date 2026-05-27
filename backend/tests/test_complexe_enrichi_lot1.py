"""Tests Lot 1 complexe enrichi — grammage films + champs techniques.

Vérifie sur le tenant démo (entreprise_id=1, seedé depuis complexe.csv) :
  - les 13 films ont désormais un grammage_g_m2 non-NULL (fin du bug 0 €
    sur le best-effort) ;
  - les champs techniques (epaisseur_microns, est_transparent, opacite_pct,
    sous_type) sont peuplés de façon cohérente ;
  - les papiers conservent leur grammage (dont id=31, complexe du benchmark).

Le seed re-tourne avant chaque test (conftest autouse) → l'état reflète
le CSV enrichi.
"""
from decimal import Decimal

from app.db import SessionLocal
from app.models import Complexe

# ids 1-13 = films ; 14-31 = papiers/thermiques (cf. complexe.csv).
FILM_IDS = list(range(1, 14))
TRANSPARENT_REFS = {
    "BOPP_TRANSPARENT_50",
    "PP_TRANSPARENT_60",
    "PE_TRANSPARENT_70",
    "PVC_TRANSPARENT_120",
}
# Grammages de face attendus pour les 13 films (épaisseur × densité).
GRAMMAGE_FILMS_ATTENDU = {
    1: Decimal("45.5"), 2: Decimal("45.5"), 3: Decimal("63.7"),
    4: Decimal("54.6"), 5: Decimal("54.3"), 6: Decimal("54.3"),
    7: Decimal("72.4"), 8: Decimal("64.4"), 9: Decimal("64.4"),
    10: Decimal("92.0"), 11: Decimal("104.0"), 12: Decimal("130.0"),
    13: Decimal("156.0"),
}


def _complexes() -> list[Complexe]:
    with SessionLocal() as db:
        return (
            db.query(Complexe)
            .filter_by(entreprise_id=1)
            .order_by(Complexe.id)
            .all()
        )


def test_les_13_films_ont_un_grammage_non_null():
    """Plus aucun film sans grammage → le best-effort ne casse plus sur P1."""
    by_id = {c.id: c for c in _complexes()}
    for fid in FILM_IDS:
        assert by_id[fid].grammage_g_m2 is not None, (
            f"complexe film id={fid} ({by_id[fid].reference}) sans grammage"
        )
        assert Decimal(by_id[fid].grammage_g_m2) == GRAMMAGE_FILMS_ATTENDU[fid]


def test_aucun_complexe_sans_grammage():
    """Les 31 complexes du tenant démo ont tous un grammage (films + papiers)."""
    assert all(c.grammage_g_m2 is not None for c in _complexes())


def test_epaisseur_microns_films_seulement():
    """Films : epaisseur_microns renseigné. Papiers : NULL (caractérisés au
    grammage)."""
    for c in _complexes():
        if c.id in FILM_IDS:
            assert c.epaisseur_microns is not None, c.reference
        else:
            assert c.epaisseur_microns is None, c.reference


def test_est_transparent_derive_de_la_reference():
    """est_transparent True ssi 'TRANSPARENT' dans la référence."""
    for c in _complexes():
        assert c.est_transparent == (c.reference in TRANSPARENT_REFS), c.reference


def test_opacite_et_sous_type_peuples():
    """opacite_pct (transparent 5 / film opaque 92 / papier 95) et sous_type
    renseignés sur les 31."""
    for c in _complexes():
        assert c.opacite_pct is not None, c.reference
        assert c.sous_type, c.reference
        if c.reference in TRANSPARENT_REFS:
            assert Decimal(c.opacite_pct) == Decimal("5.0"), c.reference
        elif c.id in FILM_IDS:
            assert Decimal(c.opacite_pct) == Decimal("92.0"), c.reference
        else:
            assert Decimal(c.opacite_pct) == Decimal("95.0"), c.reference


def test_papiers_grammage_inchange_dont_benchmark_id31():
    """Les papiers gardent leur grammage entier d'origine — en particulier
    id=31 (VELIN_STANDARD_80, complexe du benchmark figé) reste à 80."""
    by_id = {c.id: c for c in _complexes()}
    assert Decimal(by_id[31].grammage_g_m2) == Decimal("80")
    assert by_id[31].reference == "VELIN_STANDARD_80"
    assert Decimal(by_id[17].grammage_g_m2) == Decimal("80")  # COUCHE_BRILLANT_80
