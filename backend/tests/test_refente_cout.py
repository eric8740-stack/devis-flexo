"""Lot back B — coût de refente pur (axe largeur × nb_filles + gâche).

Tests sans DB du helper `calculer_cout_refente` : orthogonalité filles × Ø,
gâche raccord, pas de poste fantôme à 1 fille, validations.
"""
from decimal import Decimal

import pytest

from app.services.rebobinage.refente import (
    ResultatRefente,
    calculer_cout_refente,
)
from app.services.rebobinage.types import ResultatBobines


def _bobines(nb_bobines: int) -> ResultatBobines:
    return ResultatBobines(
        nb_etiq_par_bobine=1000,
        nb_bobines=nb_bobines,
        bobine_partielle=False,
        nb_etiq_derniere_bobine=1000,
        longueur_totale_m=Decimal("100"),
    )


def test_une_fille_pas_de_refente_cout_zero():
    """1 fille = pas de slitting → ligne non applicable, coût 0 (pas de
    poste fantôme)."""
    r = calculer_cout_refente(
        nb_filles=1,
        longueur_par_fille_m=Decimal("100"),
        bobines_par_fille=_bobines(2),
        vitesse_pratique_m_min=200,
        temps_changement_bobine_min=Decimal("2"),
        cout_exploitation_rebobineuse_eur_h=Decimal("60"),
        gache_raccord_pct=Decimal("1"),
    )
    assert isinstance(r, ResultatRefente)
    assert r.applicable is False
    assert r.cout_refente_eur == Decimal("0.00")


def test_orthogonalite_filles_x_bobines_o():
    """nb_bobines_total = nb_filles × nb_bobines_par_fille (axes orthogonaux)."""
    r = calculer_cout_refente(
        nb_filles=4,
        longueur_par_fille_m=Decimal("100"),
        bobines_par_fille=_bobines(3),
        vitesse_pratique_m_min=200,
        temps_changement_bobine_min=Decimal("2"),
        cout_exploitation_rebobineuse_eur_h=Decimal("60"),
        gache_raccord_pct=Decimal("0"),
    )
    assert r.applicable is True
    assert r.nb_filles == 4
    assert r.nb_bobines_par_fille == 3
    assert r.nb_bobines_total == 12


def test_nb_filles_multiplie_temps_et_cout():
    """Sans gâche : temps = nb_filles × (roulage + (nb_bob−1)×changement).
    4 filles × (100/200 + 2×2) = 4 × 4.5 = 18 min → 0.3 h × 60 = 18 €."""
    r = calculer_cout_refente(
        nb_filles=4,
        longueur_par_fille_m=Decimal("100"),
        bobines_par_fille=_bobines(3),
        vitesse_pratique_m_min=200,
        temps_changement_bobine_min=Decimal("2"),
        cout_exploitation_rebobineuse_eur_h=Decimal("60"),
        gache_raccord_pct=Decimal("0"),
    )
    assert r.temps_refente_h == Decimal("0.3000")
    assert r.cout_refente_eur == Decimal("18.00")


def test_gache_raccord_augmente_le_cout():
    """Gâche 10 % ajoute du métrage rebobiné → temps/coût en hausse."""
    base = calculer_cout_refente(
        nb_filles=4,
        longueur_par_fille_m=Decimal("100"),
        bobines_par_fille=_bobines(3),
        vitesse_pratique_m_min=200,
        temps_changement_bobine_min=Decimal("2"),
        cout_exploitation_rebobineuse_eur_h=Decimal("60"),
        gache_raccord_pct=Decimal("0"),
    )
    avec_gache = calculer_cout_refente(
        nb_filles=4,
        longueur_par_fille_m=Decimal("100"),
        bobines_par_fille=_bobines(3),
        vitesse_pratique_m_min=200,
        temps_changement_bobine_min=Decimal("2"),
        cout_exploitation_rebobineuse_eur_h=Decimal("60"),
        gache_raccord_pct=Decimal("10"),
    )
    # gâche = 10 % × (4 × 100) = 40 m ; temps gâche = 40/200 = 0.2 min.
    assert avec_gache.gache_metres == Decimal("40.00")
    assert avec_gache.cout_refente_eur > base.cout_refente_eur


def test_cout_zero_si_taux_zero():
    """Taux refente 0 (config neutre, non configuré) → coût 0 mais applicable."""
    r = calculer_cout_refente(
        nb_filles=4,
        longueur_par_fille_m=Decimal("100"),
        bobines_par_fille=_bobines(3),
        vitesse_pratique_m_min=200,
        temps_changement_bobine_min=Decimal("2"),
        cout_exploitation_rebobineuse_eur_h=Decimal("0"),
        gache_raccord_pct=Decimal("0"),
    )
    assert r.applicable is True
    assert r.cout_refente_eur == Decimal("0.00")


def test_validations():
    with pytest.raises(ValueError):
        calculer_cout_refente(
            nb_filles=4, longueur_par_fille_m=Decimal("100"),
            bobines_par_fille=_bobines(3), vitesse_pratique_m_min=0,
            temps_changement_bobine_min=Decimal("2"),
            cout_exploitation_rebobineuse_eur_h=Decimal("60"),
            gache_raccord_pct=Decimal("0"),
        )
    with pytest.raises(ValueError):
        calculer_cout_refente(
            nb_filles=4, longueur_par_fille_m=Decimal("100"),
            bobines_par_fille=_bobines(3), vitesse_pratique_m_min=200,
            temps_changement_bobine_min=Decimal("2"),
            cout_exploitation_rebobineuse_eur_h=Decimal("-1"),
            gache_raccord_pct=Decimal("0"),
        )
