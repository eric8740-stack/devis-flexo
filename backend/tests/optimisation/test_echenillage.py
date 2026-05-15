"""Tests règle échenillage Sprint 13 S13.D.2.

CdC § 505-528 : l'échenillage est le squelette de papier qui reste
entre les étiquettes après découpe. Intervalle dev trop faible →
squelette fragile → casse à grande vitesse. Intervalle trop grand →
gâche matière.

Barème ICE par défaut (CdC ligne 515) — tous calculés en fonction de
intervalle_dev_reel_mm :
  intervalle <= 2 mm  → parfait   (vit 1.00, gache 1.00, score 100)
  intervalle <= 3 mm  → parfait   (vit 1.00, gache 1.00, score 100)
  intervalle <= 4 mm  → bien      (vit 1.00, gache 1.00, score 85)
  intervalle <= 5 mm  → complique (vit 0.70, gache 1.08, score 50)
  intervalle <= 6 mm  → mauvais   (vit 0.60, gache 1.12, score 30)
  intervalle <= 7 mm  → mauvais   (vit 0.55, gache 1.15, score 20)
  intervalle <= 8 mm  → critique  (vit 0.50, gache 1.20, score 10)
  intervalle > 8 mm   → critique  (vit 0.40, gache 1.25, score 5)
"""
import pytest

from app.data.catalogue_defaults import get_bareme_by_code
from app.services.optimisation.regles.echenillage import (
    lookup_palier_echenillage,
)


BAREME_ICE = get_bareme_by_code("echenillage_ice")["bareme_data"]


@pytest.mark.parametrize(
    "intervalle_mm,qualite_attendue,vitesse,gache,score",
    [
        (1.0, "parfait", 1.00, 1.00, 100),     # sous palier 2
        (2.0, "parfait", 1.00, 1.00, 100),     # pile palier 2
        (2.5, "parfait", 1.00, 1.00, 100),     # entre 2 et 3 → palier 3
        (3.0, "parfait", 1.00, 1.00, 100),     # pile palier 3
        (3.5, "bien", 1.00, 1.00, 85),         # bascule sur palier 4
        (4.0, "bien", 1.00, 1.00, 85),
        (4.01, "complique", 0.70, 1.08, 50),   # bascule sur palier 5 → forte pénalité
        (5.0, "complique", 0.70, 1.08, 50),
        (5.5, "mauvais", 0.60, 1.12, 30),
        (6.0, "mauvais", 0.60, 1.12, 30),
        (6.5, "mauvais", 0.55, 1.15, 20),
        (7.0, "mauvais", 0.55, 1.15, 20),
        (7.5, "critique", 0.50, 1.20, 10),
        (8.0, "critique", 0.50, 1.20, 10),
        (8.01, "critique", 0.40, 1.25, 5),     # palier > 8
        (15.0, "critique", 0.40, 1.25, 5),     # très grand
    ],
)
def test_lookup_palier_echenillage(
    intervalle_mm, qualite_attendue, vitesse, gache, score
):
    palier = lookup_palier_echenillage(intervalle_mm, BAREME_ICE)
    assert palier["qualite"] == qualite_attendue
    assert palier["coef_vitesse"] == vitesse
    assert palier["coef_gache"] == gache
    assert palier["score"] == score


def test_bareme_vide_retourne_palier_neutre():
    """Edge case : barème non configuré → palier neutre (coefs 1.0,
    qualité 'inconnu', score 0 pour ne pas favoriser un cylindre dans
    l'optimisation)."""
    palier = lookup_palier_echenillage(5.0, [])
    assert palier["coef_vitesse"] == 1.0
    assert palier["coef_gache"] == 1.0
    assert palier["qualite"] == "inconnu"
    assert palier["score"] == 0
