"""Tests smoke des schémas Pydantic v2 (S3 Lot 3c).

Pas de moteur testé ici : ces schémas seront alimentés par les calculateurs
poste_X_xxx.py en Lot 3d. On vérifie juste que les contraintes Pydantic
sont en place (champs requis, bornes, extra="forbid").
"""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.devis import (
    CandidatCylindreOutput,
    DevisInput,
    DevisOutput,
    DevisOutputMatching,
    PartenaireSTForfait,
)
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


def test_devis_output_default_mode_manuel():
    """Sprint 7 — DevisOutput porte mode='manuel' (discriminant Union API)."""
    output = DevisOutput(
        postes=_make_postes(),
        cout_revient_eur=Decimal("70"),
        pct_marge_appliquee=Decimal("0.18"),
        prix_vente_ht_eur=Decimal("82.6"),
        prix_au_mille_eur=Decimal("6.92"),
    )
    assert output.mode == "manuel"


# ---------------------------------------------------------------------------
# Sprint 7 Lot 7c V2 — DevisOutputMatching + CandidatCylindreOutput
# (formule corrigée pas = (Z × 3.175) / nb_etiq, plages Z=51-144 / nb_etiq=1-40)
# ---------------------------------------------------------------------------


def _make_candidat(z: int = 72, nb_etiq: int = 5) -> CandidatCylindreOutput:
    """Helper : un candidat cylindre minimal cohérent avec la formule corrigée.

    Z=72, nb_etiq=5 → circonf=228.6, pas=45.72, intervalle=5.72 (avec format_h=40).
    Vérifié dans le tableau Develop.xlsx Eric (sonde de validation).
    """
    circonference = Decimal(z) * Decimal("3.175")
    pas = circonference / Decimal(nb_etiq)
    return CandidatCylindreOutput(
        z=z,
        nb_etiq_par_tour=nb_etiq,
        circonference_mm=circonference,
        pas_mm=pas,
        intervalle_mm=pas - Decimal("40"),  # format_h=40 par défaut
        nb_etiq_par_metre=int((Decimal("1000") / pas).quantize(Decimal("1"))),
        postes=_make_postes(),
        cout_revient_eur=Decimal("70"),
        pct_marge_appliquee=Decimal("0.18"),
        prix_vente_ht_eur=Decimal("82.6"),
        prix_au_mille_eur=Decimal("6.92"),
    )


def test_candidat_cylindre_z_borne_basse():
    """Z minimum = 51 (corrigé v2 vs v1 qui était 72)."""
    # Construit avec un intervalle valide pour ne tester que la borne Z.
    # (51/1 donnerait intervalle=121.93 hors plage Pydantic 2.5-15)
    cand_valid = CandidatCylindreOutput(
        z=51,
        nb_etiq_par_tour=5,
        circonference_mm=Decimal("161.93"),  # 51 × 3.175 (légère imprécision OK)
        pas_mm=Decimal("32.385"),
        intervalle_mm=Decimal("3"),  # arbitraire dans la plage 2.5-15 pour le test schéma
        nb_etiq_par_metre=30,
        postes=_make_postes(),
        cout_revient_eur=Decimal("70"),
        pct_marge_appliquee=Decimal("0.18"),
        prix_vente_ht_eur=Decimal("82.6"),
        prix_au_mille_eur=Decimal("6.92"),
    )
    assert cand_valid.z == 51
    with pytest.raises(ValidationError):
        # Z=50 → sous la borne basse v2
        CandidatCylindreOutput(
            z=50,
            nb_etiq_par_tour=5,
            circonference_mm=Decimal("158.75"),
            pas_mm=Decimal("31.75"),
            intervalle_mm=Decimal("3"),
            nb_etiq_par_metre=30,
            postes=_make_postes(),
            cout_revient_eur=Decimal("70"),
            pct_marge_appliquee=Decimal("0.18"),
            prix_vente_ht_eur=Decimal("82.6"),
            prix_au_mille_eur=Decimal("6.92"),
        )


def test_candidat_cylindre_z_borne_haute():
    """Z maximum = 144 (corrigé v2 vs v1 qui était 187)."""
    cand = _make_candidat(z=144, nb_etiq=10)  # circonf=457.20, pas=45.72
    assert cand.z == 144
    with pytest.raises(ValidationError):
        # Z=145 → au-dessus borne haute v2
        CandidatCylindreOutput(
            z=145,
            nb_etiq_par_tour=5,
            circonference_mm=Decimal("460.375"),
            pas_mm=Decimal("92.075"),
            intervalle_mm=Decimal("3"),  # placeholder valide pour ne tester que Z
            nb_etiq_par_metre=10,
            postes=_make_postes(),
            cout_revient_eur=Decimal("70"),
            pct_marge_appliquee=Decimal("0.18"),
            prix_vente_ht_eur=Decimal("82.6"),
            prix_au_mille_eur=Decimal("6.92"),
        )


def test_candidat_cylindre_nb_etiq_borne_basse_1():
    """nb_etiq_par_tour minimum = 1 (formats très grands, 1 étiquette par tour)."""
    cand = CandidatCylindreOutput(
        z=144,
        nb_etiq_par_tour=1,
        circonference_mm=Decimal("457.20"),
        pas_mm=Decimal("457.20"),
        intervalle_mm=Decimal("7.2"),  # avec format_h=450 par exemple
        nb_etiq_par_metre=2,
        postes=_make_postes(),
        cout_revient_eur=Decimal("70"),
        pct_marge_appliquee=Decimal("0.18"),
        prix_vente_ht_eur=Decimal("82.6"),
        prix_au_mille_eur=Decimal("6.92"),
    )
    assert cand.nb_etiq_par_tour == 1


def test_candidat_cylindre_nb_etiq_borne_haute_40():
    """nb_etiq_par_tour maximum = 40 (limite haute tableau Eric)."""
    # Z=144, nb_etiq=40 → pas=11.43, intervalle=11.43-format_h
    cand = CandidatCylindreOutput(
        z=144,
        nb_etiq_par_tour=40,
        circonference_mm=Decimal("457.20"),
        pas_mm=Decimal("11.43"),
        intervalle_mm=Decimal("3.43"),  # format_h=8 par exemple
        nb_etiq_par_metre=87,
        postes=_make_postes(),
        cout_revient_eur=Decimal("70"),
        pct_marge_appliquee=Decimal("0.18"),
        prix_vente_ht_eur=Decimal("82.6"),
        prix_au_mille_eur=Decimal("6.92"),
    )
    assert cand.nb_etiq_par_tour == 40
    with pytest.raises(ValidationError):
        # nb_etiq=41 → au-dessus borne
        CandidatCylindreOutput(
            z=144,
            nb_etiq_par_tour=41,
            circonference_mm=Decimal("457.20"),
            pas_mm=Decimal("11.15"),
            intervalle_mm=Decimal("3"),
            nb_etiq_par_metre=89,
            postes=_make_postes(),
            cout_revient_eur=Decimal("70"),
            pct_marge_appliquee=Decimal("0.18"),
            prix_vente_ht_eur=Decimal("82.6"),
            prix_au_mille_eur=Decimal("6.92"),
        )


def test_devis_output_matching_default_mode():
    out = DevisOutputMatching(candidats=[_make_candidat()])
    assert out.mode == "matching"
    assert len(out.candidats) == 1


def test_devis_output_matching_max_3_candidats():
    """Borne max=3 (le moteur retourne au max les 3 meilleurs)."""
    DevisOutputMatching(candidats=[_make_candidat(z=72 + i) for i in range(3)])
    with pytest.raises(ValidationError):
        DevisOutputMatching(candidats=[_make_candidat(z=72 + i) for i in range(4)])


def test_devis_output_matching_min_1_candidat():
    """Liste vide rejetée (le moteur lève CostEngineError 422 avant)."""
    with pytest.raises(ValidationError):
        DevisOutputMatching(candidats=[])
