"""Tests règle confort roulage Sprint 13 S13.D.4.

CdC § 716-784 : métaphore de la roue qui monte un trottoir. Un outil
de découpe en rotation subit la même physique — plus les angles sont
vifs, plus le choc à chaque pose force à ralentir.

Barème ICE par défaut :
  rayon 0 mm     → 0.75 (angles vifs, choc frontal)
  rayon 1 mm     → 0.90 (choc atténué)
  rayon 2 mm     → 1.00 (référence standard)
  rayon 3 mm     → 1.02 (très léger bonus)
  rayon 5 mm     → 1.08 (roulage doux)
  rayon 8-10 mm  → 1.12 (quasi-courbe continue)
  forme courbe   → 1.15 (rond/ovale, aucun choc, override rayon)

Quinconce :
  alignée  → 1.00 (défaut)
  quinconce → 1.10 (invisible pour le client final, bonus 'gratuit')
"""
import pytest

from app.data.catalogue_defaults import get_bareme_by_code
from app.services.optimisation.regles.confort_roulage import (
    coef_confort_rayon,
    coef_quinconce_disposition,
)


BAREME_ICE = get_bareme_by_code("confort_roulage_ice")["bareme_data"]


# ---------------------------------------------------------------------------
# coef_confort_rayon
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rayon_mm,coef_attendu",
    [
        (0.0, 0.75),    # angles vifs
        (0.5, 0.90),    # entre 0 et 1 → palier 1
        (1.0, 0.90),
        (1.5, 1.00),    # bascule sur palier 2 (standard)
        (2.0, 1.00),
        (2.5, 1.02),
        (3.0, 1.02),
        (4.0, 1.08),    # bascule sur palier 5
        (5.0, 1.08),
        (6.0, 1.12),    # palier 10
        (10.0, 1.12),
        (20.0, 1.12),   # au-delà : plateau
    ],
)
def test_coef_confort_rayon_paliers(rayon_mm, coef_attendu):
    coef = coef_confort_rayon(
        rayon_mm=rayon_mm, forme_courbe=False, bareme=BAREME_ICE
    )
    assert coef == coef_attendu


def test_forme_courbe_override_rayon():
    """Forme ronde/ovale : coef 1.15 indépendamment du rayon (le rayon
    perd son sens sur une forme continue)."""
    # Même avec rayon 0 ou 2, si forme_courbe=True → 1.15
    for rayon in [0.0, 2.0, 5.0]:
        coef = coef_confort_rayon(
            rayon_mm=rayon, forme_courbe=True, bareme=BAREME_ICE
        )
        assert coef == 1.15, f"forme_courbe avec rayon={rayon} devrait être 1.15"


def test_bareme_vide_retourne_coef_neutre():
    coef = coef_confort_rayon(
        rayon_mm=3.0, forme_courbe=False, bareme={}
    )
    assert coef == 1.0


# ---------------------------------------------------------------------------
# coef_quinconce_disposition
# ---------------------------------------------------------------------------


def test_disposition_alignee_coef_1():
    coef = coef_quinconce_disposition(
        disposition="alignee", bareme=BAREME_ICE
    )
    assert coef == 1.00


def test_disposition_quinconce_coef_bonus():
    coef = coef_quinconce_disposition(
        disposition="quinconce", bareme=BAREME_ICE
    )
    assert coef == 1.10


def test_disposition_inconnue_defaut_alignee():
    """Disposition inattendue → fallback alignée (sécurité)."""
    coef = coef_quinconce_disposition(
        disposition="zigzag", bareme=BAREME_ICE
    )
    assert coef == 1.00


def test_bareme_vide_quinconce_coef_neutre():
    coef = coef_quinconce_disposition(disposition="quinconce", bareme={})
    assert coef == 1.0
