"""Tests smoke des schémas Pydantic v2 (S3 Lot 3c).

Pas de moteur testé ici : ces schémas seront alimentés par les calculateurs
poste_X_xxx.py en Lot 3d. On vérifie juste que les contraintes Pydantic
sont en place (champs requis, bornes, extra="forbid").
"""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.devis import DevisInput, DevisOutput, PartenaireSTForfait
from app.schemas.poste_result import PosteResult


# ---------------------------------------------------------------------------
# PosteResult
# ---------------------------------------------------------------------------


def test_poste_result_valid_with_typed_details():
    poste = PosteResult(
        poste_numero=1,
        libelle="Matière",
        montant_eur=Decimal("12.5000"),
        details={"surface_m2": 0.825, "nb_couleurs": 4, "complexe_ref": "CMP-001"},
    )
    assert poste.montant_eur == Decimal("12.5000")
    # details accepte float, int, str — pas de Decimal (volontaire)
    assert poste.details["surface_m2"] == 0.825
    assert poste.details["nb_couleurs"] == 4
    assert poste.details["complexe_ref"] == "CMP-001"


def test_poste_result_rejects_poste_numero_out_of_range():
    with pytest.raises(ValidationError):
        PosteResult(poste_numero=0, libelle="X", montant_eur=Decimal("1"))
    with pytest.raises(ValidationError):
        PosteResult(poste_numero=8, libelle="X", montant_eur=Decimal("1"))


def test_poste_result_rejects_negative_montant():
    with pytest.raises(ValidationError):
        PosteResult(poste_numero=1, libelle="X", montant_eur=Decimal("-1"))


# ---------------------------------------------------------------------------
# DevisInput
# ---------------------------------------------------------------------------


def _minimal_input_kwargs() -> dict:
    return {
        "complexe_id": 1,
        "laize_utile_mm": 250,
        "ml_total": 1000,
        "machine_id": 1,
    }


def test_devis_input_minimal_payload_is_valid():
    payload = DevisInput(**_minimal_input_kwargs())
    assert payload.complexe_id == 1
    assert payload.nb_couleurs_par_type == {}
    assert payload.forfaits_st == []
    assert payload.heures_dossier_override is None
    assert payload.pct_marge_override is None


def test_devis_input_full_payload_is_valid():
    payload = DevisInput(
        complexe_id=2,
        laize_utile_mm=300,
        ml_total=5000,
        nb_couleurs_par_type={"process_cmj": 4, "pantone": 2},
        machine_id=1,
        forfaits_st=[
            PartenaireSTForfait(partenaire_st_id=1, montant_eur=Decimal("150.00"))
        ],
        heures_dossier_override=Decimal("2.5"),
        pct_marge_override=Decimal("0.22"),
    )
    assert payload.nb_couleurs_par_type["process_cmj"] == 4
    assert len(payload.forfaits_st) == 1
    assert payload.pct_marge_override == Decimal("0.22")


def test_devis_input_rejects_unknown_field():
    """extra='forbid' garantit qu'aucun champ parasite ne passe."""
    with pytest.raises(ValidationError):
        DevisInput(**_minimal_input_kwargs(), champ_inconnu=42)


def test_devis_input_rejects_zero_or_negative_dimensions():
    for bad_field in ("laize_utile_mm", "ml_total", "machine_id", "complexe_id"):
        kwargs = _minimal_input_kwargs() | {bad_field: 0}
        with pytest.raises(ValidationError):
            DevisInput(**kwargs)


def test_devis_input_pct_marge_override_capped_at_2():
    with pytest.raises(ValidationError):
        DevisInput(**_minimal_input_kwargs(), pct_marge_override=Decimal("2.5"))


# ---------------------------------------------------------------------------
# Sprint 7 Lot 7b — mode_calcul + intervalle_mm conditionnel
# ---------------------------------------------------------------------------


def test_devis_input_mode_default_manuel():
    """Sans mode_calcul → default 'manuel' (préserve V1a payload Sprint 5)."""
    payload = DevisInput(**_minimal_input_kwargs())
    assert payload.mode_calcul == "manuel"
    assert payload.intervalle_mm is None


def test_devis_input_mode_manuel_intervalle_None_autorise():
    """En mode manuel, intervalle_mm = None est autorisé (default 3 dans moteur)."""
    payload = DevisInput(**_minimal_input_kwargs(), mode_calcul="manuel")
    assert payload.mode_calcul == "manuel"
    assert payload.intervalle_mm is None


def test_devis_input_mode_manuel_intervalle_explicite_OK():
    """En mode manuel, intervalle_mm explicite OK dans la plage 2.5-15."""
    payload = DevisInput(
        **_minimal_input_kwargs(),
        mode_calcul="manuel",
        intervalle_mm=Decimal("4.5"),
    )
    assert payload.intervalle_mm == Decimal("4.5")


def test_devis_input_mode_matching_intervalle_None_OK():
    """En mode matching, intervalle_mm DOIT être None."""
    payload = DevisInput(**_minimal_input_kwargs(), mode_calcul="matching")
    assert payload.mode_calcul == "matching"
    assert payload.intervalle_mm is None


def test_devis_input_mode_matching_intervalle_set_rejette():
    """En mode matching, intervalle_mm fourni → ValidationError (incohérent)."""
    with pytest.raises(ValidationError, match="matching"):
        DevisInput(
            **_minimal_input_kwargs(),
            mode_calcul="matching",
            intervalle_mm=Decimal("3"),
        )


def test_devis_input_mode_invalid_rejette():
    """Literal contraint à 'manuel' ou 'matching'."""
    with pytest.raises(ValidationError):
        DevisInput(**_minimal_input_kwargs(), mode_calcul="auto")


def test_devis_input_intervalle_mm_borne_basse_25_acceptee():
    DevisInput(**_minimal_input_kwargs(), intervalle_mm=Decimal("2.5"))


def test_devis_input_intervalle_mm_borne_haute_15_acceptee():
    DevisInput(**_minimal_input_kwargs(), intervalle_mm=Decimal("15"))


def test_devis_input_intervalle_mm_rejette_sous_borne():
    with pytest.raises(ValidationError):
        DevisInput(**_minimal_input_kwargs(), intervalle_mm=Decimal("2.4"))


def test_devis_input_intervalle_mm_rejette_au_dessus_borne():
    with pytest.raises(ValidationError):
        DevisInput(**_minimal_input_kwargs(), intervalle_mm=Decimal("15.1"))


# ---------------------------------------------------------------------------
# DevisOutput
# ---------------------------------------------------------------------------


def _make_postes() -> list[PosteResult]:
    return [
        PosteResult(poste_numero=i, libelle=f"P{i}", montant_eur=Decimal("10"))
        for i in range(1, 8)
    ]


def test_devis_output_with_7_postes_is_valid():
    output = DevisOutput(
        postes=_make_postes(),
        cout_revient_eur=Decimal("70"),
        pct_marge_appliquee=Decimal("0.18"),
        prix_vente_ht_eur=Decimal("82.6"),
        prix_au_mille_eur=Decimal("6.92"),
    )
    assert len(output.postes) == 7
    assert output.prix_au_mille_eur == Decimal("6.92")


def test_devis_output_rejects_less_than_7_postes():
    with pytest.raises(ValidationError):
        DevisOutput(
            postes=_make_postes()[:6],
            cout_revient_eur=Decimal("60"),
            pct_marge_appliquee=Decimal("0.18"),
            prix_vente_ht_eur=Decimal("70.8"),
            prix_au_mille_eur=Decimal("5.00"),
        )
