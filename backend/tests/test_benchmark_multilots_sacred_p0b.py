"""P0b — Benchmark sacre chemin multi-lots (e2e POST /api/devis).

Contexte : les 13 benchmarks sacrés actuels (test_cost_engine_benchmark.py +
test_cost_engine_5cas_benchmark.py) appellent tous `MoteurDevis.calculer(
_devis_median())` en direct, jamais via `_construire_devis_input_pour_lot`.
=> Angle mort total sur la chaîne multi-lots et le futur repoint
`MachineImprimerie.laize_utile_mm` -> `Machine.laize_utile_mm` (P1).

But P0b : figer l'invariant **chemin multi-lots -> cost_engine** AVANT le
repoint P1. Une regression du `laize_utile_mm` lu (320 MachineImprimerie
vs 330 Machine pour le tenant demo P5) modifierait `nb_poses_laize_max`
-> bouge tous les postes -> ce test attraperait la derive immediatement.

Test e2e :
  1. setup tenant demo + `_onboard_if_needed()` (peuple
     MachineImprimerie + CylindreMagnetique + Matiere).
  2. POST /api/devis avec un payload multi-lots DETERMINISTE (1 lot fige).
  3. Garde-fou anti-drift fixture : assert que la MachineImprimerie source
     a bien `laize_utile_mm == 320` (cf MACHINES_DEFAULT, Mark Andy 2200).
  4. Assert `prix_vente_ht_eur == 704.07 EUR` (figeage SACRED tripwire).

SACRED dependance : ce test consomme l'etat seedé + l'onboarding du
tenant demo. Tout changement de seed `machine_imprimerie` ou de catalogue
onboarding (cf `data/catalogue_defaults.py`) qui modifie `laize_utile_mm`
ou `vitesse_pratique_m_min` de la 1re machine -> casse intentionnellement
ce test. C'est le comportement souhaite.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis
from tests.test_lot_production_model import _onboard_if_needed


client = TestClient(app)
DEMO_ENTREPRISE_ID = 1


# === VALEUR SACRED FIGEE ===
# Tripwire chemin multi-lots. Machine source Mark Andy 2200 (laize_utile=320).
# RE-BASELINE L2 (validée Eric) : P1 rebasé sur laize_papier réelle plafonnée à
# laize_utile, marge_confort retirée. Le plafond MORD ici : laize_plaque=310
# (3×100 + 2×5), papier brut = 330 > laize_utile 320 → plafonné à 320. Base P1
# 330→320 → P1 243,56→236,18 (ΔP1 −7,38) → cout_revient 596,67→589,29 →
# prix_vente 704,07 → 695,36 €.
_EXPECTED_PRIX_VENTE_HT: Decimal = Decimal("695.36")

# Garde anti-drift fixture : la 1re MachineImprimerie active du tenant demo
# DOIT avoir cette laize utile. Si l'ordre d'INSERT onboarding ou le catalogue
# par defaut change -> _EXPECTED_PRIX_VENTE_HT serait silencieusement fige
# sur un autre scenario. Ce check echoue FORT avant d'arriver au sacred.
_EXPECTED_LAIZE_UTILE_MACHINE_SOURCE = Decimal("320.00")


# Payload deterministe -- toute valeur ici est figee et impacte le sacred.
# Si une valeur doit bouger -> remettre _EXPECTED_PRIX_VENTE_HT a re-baseliner
# et refaire valider par Eric.
_LOT_PAYLOAD_FIGE = {
    "nb_poses_dev": 2,
    "nb_poses_laize": 3,
    "sens_enroulement": 1,
    "quantite": 10_000,
}
_PAYLOAD_INPUT_FIGE = {
    "format_etiquette_largeur_mm": 100,
    "format_etiquette_hauteur_mm": 80,
    "mode_calcul": "manuel",
    # Sprint 16 fix chiffrage : pas de pct_marge_override -> default tenant.
    # nb_couleurs propage en amont par _mapper_nb_couleurs (test sans nb_couleurs
    # = P2 Encres a 0, deterministe).
}


def _fks_demo_premiere_combo() -> tuple[int, int, int]:
    """Recupere les ids deterministes du tenant demo apres
    `_onboard_if_needed`. P1+P2 : selection PAR NOM sur `Machine` (post
    fusion MI -> Machine via migration b2c3d4e5f6g7) -- la regle
    historique "1ere MachineImprimerie ORDER BY id" n'existe plus.
    """
    _onboard_if_needed()
    from app.models import CylindreMagnetique, Machine, Matiere

    with SessionLocal() as db:
        # P1+P2 : selection par NOM (deterministe et explicite). L'onboarding
        # INSERT Mark Andy 2200 dans `machine` (au lieu de machine_imprimerie
        # pre-P1+P2).
        machine = (
            db.query(Machine)
            .filter_by(
                entreprise_id=DEMO_ENTREPRISE_ID,
                nom="Mark Andy 2200",
                actif=True,
            )
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=DEMO_ENTREPRISE_ID, actif=True)
            .order_by(CylindreMagnetique.id)
            .first()
        )
        mat = (
            db.query(Matiere)
            .filter_by(entreprise_id=DEMO_ENTREPRISE_ID, actif=True)
            .order_by(Matiere.id)
            .first()
        )
        assert machine and cyl and mat, (
            "seed/onboarding tenant demo incomplet (Mark Andy 2200 attendue "
            "dans `machine` apres P1+P2)"
        )

        # Anti-drift : Mark Andy 2200 doit avoir laize_utile=320 (catalogue
        # MACHINES_DEFAULT). Si la laize change cote catalogue, le sacred
        # multi-lots serait fige sur un autre scenario -- echec FORT ici.
        assert machine.laize_utile_mm == _EXPECTED_LAIZE_UTILE_MACHINE_SOURCE, (
            f"DRIFT fixture : Mark Andy 2200 attendue avec "
            f"laize_utile_mm={_EXPECTED_LAIZE_UTILE_MACHINE_SOURCE}, "
            f"obtenu laize_utile_mm={machine.laize_utile_mm} "
            f"(machine.id={machine.id}). "
            "Le sacred multi-lots ci-dessous serait fige sur un autre "
            "scenario que celui valide -- INVESTIGUER avant de toucher "
            "a `_EXPECTED_PRIX_VENTE_HT`."
        )
        return machine.id, cyl.id, mat.id


def _payload_post_devis_multilots_fige() -> dict:
    machine_id, cyl_id, mat_id = _fks_demo_premiere_combo()
    return {
        "payload_input": {**_PAYLOAD_INPUT_FIGE, "machine_id": machine_id},
        "payload_output": {"mode": "manuel", "prix_vente_ht_eur": "0.00"},
        "statut": "brouillon",
        "quantite_totale": _LOT_PAYLOAD_FIGE["quantite"],
        "lots": [
            {
                **_LOT_PAYLOAD_FIGE,
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "matiere_id": mat_id,
            },
        ],
    }


def _purge_devis_tenant_demo() -> None:
    """Vide les devis du tenant demo avant chaque scenario pour rendre le
    numero auto (`DEV-YYYY-0001`) deterministe."""
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.entreprise_id == DEMO_ENTREPRISE_ID).delete()
        db.commit()


def _post_devis_multilots_et_lit_prix() -> Decimal:
    """POST /api/devis multi-lots deterministe + retourne prix_vente_ht_eur
    lu sur `payload_output.details_par_lot[0].details`."""
    _purge_devis_tenant_demo()
    r = client.post("/api/devis", json=_payload_post_devis_multilots_fige())
    assert r.status_code == 201, r.text
    po = r.json()["payload_output"]
    assert po.get("mode") == "multi-lots", (
        f"Attendu mode='multi-lots', got {po.get('mode')!r}. "
        f"Erreur chiffrage ? {po.get('chiffrage_auto_erreur')!r}"
    )
    dpl = po.get("details_par_lot")
    assert isinstance(dpl, list) and len(dpl) == 1, (
        f"Attendu 1 lot dans details_par_lot, got {dpl!r}"
    )
    details = dpl[0]["details"]
    return Decimal(str(details["prix_vente_ht_eur"]))


def test_benchmark_sacred_multilots_pre_repoint():
    """SACRED multi-lots : fige le prix_vente_ht_eur pour le scenario
    deterministe ci-dessus. Sert de tripwire AVANT le repoint P1
    (MachineImprimerie.laize_utile_mm -> Machine.laize_utile_mm).

    Une fois le repoint P1 appliqué : si cette valeur CHANGE, c'est que
    le repoint a modifie le `laize_utile_mm` effectivement passe au
    moteur (ex : MachineImprimerie=320 vs Machine=330 sur P5 demo).
    => Decision metier Eric requise avant figeage de la nouvelle valeur.
    """
    prix = _post_devis_multilots_et_lit_prix()
    assert prix == _EXPECTED_PRIX_VENTE_HT, (
        f"REGRESSION SACRED multi-lots : attendu "
        f"{_EXPECTED_PRIX_VENTE_HT} EUR, obtenu {prix} EUR. "
        "Si le changement est INTENTIONNEL (ex. repoint P1 valide par Eric), "
        "mettre a jour `_EXPECTED_PRIX_VENTE_HT` dans le module."
    )
