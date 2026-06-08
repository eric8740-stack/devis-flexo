"""Lot back B — refente ADDITIVE dans ht_total (pur, sans DB).

La ligne refente entre dans `ht_total` mais JAMAIS dans `prix_vente_ht`
(7 postes sacrés). Absente / non appliquée → ht_total inchangé.
"""
from decimal import Decimal

from app.services.devis_total import (
    contribution_refente_eur,
    ht_total_avec_rebobinage,
)


def test_contribution_refente_appliquee():
    po = {"refente": {"applique": True, "cout_total_refente_eur": "42.50"}}
    assert contribution_refente_eur(po) == Decimal("42.50")


def test_contribution_refente_absente_ou_non_appliquee():
    assert contribution_refente_eur(None) == Decimal("0")
    assert contribution_refente_eur({}) == Decimal("0")
    assert contribution_refente_eur(
        {"refente": {"applique": False, "cout_total_refente_eur": "99"}}
    ) == Decimal("0")


def test_ht_total_additionne_refente_sans_toucher_la_base():
    base = Decimal("1424.31")  # sacré V1a — ne doit jamais être modifié
    po = {"refente": {"applique": True, "cout_total_refente_eur": "10.00"}}
    assert ht_total_avec_rebobinage(base, po) == Decimal("1434.31")
    # Sans ligne refente → ht_total == base (value-neutral).
    assert ht_total_avec_rebobinage(base, {}) == base


def test_ht_total_cumule_rebobinage_et_refente():
    base = Decimal("100.00")
    po = {
        "rebobinage_multilots": {
            "applique": True, "cout_total_rebobinage_eur": "5.00"
        },
        "refente": {"applique": True, "cout_total_refente_eur": "3.00"},
    }
    assert ht_total_avec_rebobinage(base, po) == Decimal("108.00")
