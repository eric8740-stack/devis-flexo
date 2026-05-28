"""Planificateur de bobines — 3 scénarios de découpe pour le rapport
de fabrication interne (`/devis/[id]`).

Calculable **uniquement post-optim** : on a besoin de `n_laize` (poses
en laize, résultat optim) et `pas_mm = dev_étiq + écart_dev_réel`.

Les bobines sortent **par paquets de n_laize identiques** (coupe
synchronisée). On raisonne sur UNE piste (R étiq, R = ceil(Q / n_laize)),
répliqué × n_laize.

3 scénarios :

- **A — pleines + reliquat** :
    `k = R // nb_max`, `reste = R - k*nb_max`. Par piste : k bobines
    de nb_max + 1 partielle si reste > 0. Surprod = R*n_laize - Q.

- **B — équilibrées** :
    `k = ceil(R / nb_max)`. Par piste : k bobines ~égales
    (la dernière absorbe l'arrondi).

- **C — tomber juste (ajuste Q)** :
    Cherche Q' proche de Q telle que R' = Q' / n_laize soit divisible
    par un entier ≤ nb_max → 0 reliquat, bobines pleines égales. On
    propose une option **en dessous** (`q_inf`) et **au-dessus** (`q_sup`)
    de Q. La carte UI montre la plus proche par défaut.

Cost rebobinage : LECTURE SEULE de `arbitrage_mandrins.calculer_arbitrage`
(prend `nb_bobines` en direct) + `calcul_temps.calculer_temps_et_cout_machine`
(prend un `ResultatBobines` synthétique). On ne MODIFIE rien dans le
moteur de coût.

Helpers SSOT CC2 réutilisés sans duplication :
- `calcul_nb_max_etiq_pour_diametre` : nb max d'étiquettes en bobine pleine
- `calcul_diametre_requis_pour_nb_etiq` : Ø affiché par bobine partielle
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.services.optimisation.bat_calculs import (
    calcul_diametre_bobine,
    calcul_diametre_requis_pour_nb_etiq,
    calcul_nb_max_etiq_pour_diametre,
)
from app.services.rebobinage.arbitrage_mandrins import (
    RebobinageError,
    calculer_arbitrage,
)
from app.services.rebobinage.calcul_temps import (
    calculer_temps_et_cout_machine,
)
from app.services.rebobinage.types import (
    ChoixOperateur,
    MachineRebobinageParams,
    ParametresMandrinRuntime,
    ResultatBobines,
    TarifsMandrins,
)


ScenarioKey = Literal["A", "B", "C_inf", "C_sup", "IMPOSE"]


@dataclass(frozen=True)
class RepartitionBobine:
    """Un groupe de bobines identiques (étiq par bobine + count par piste)."""

    nb_etiq_par_bobine: int
    nb_bobines_par_piste: int  # = count par piste
    diametre_mm: int  # Ø via SSOT CC2


@dataclass(frozen=True)
class ScenarioBobines:
    """Un scénario complet, prêt pour l'UI."""

    cle: ScenarioKey  # A / B / C_inf / C_sup
    titre: str  # libellé court UI
    repartition: list[RepartitionBobine]
    nb_bobines_par_piste: int  # sum(r.nb_bobines_par_piste)
    nb_bobines_total: int  # = nb_bobines_par_piste × n_laize
    quantite_totale_etiq: int  # produite par ce scénario (≥ Q sauf C_inf)
    surprod_etiq: int  # quantite_totale - Q (négatif si C_inf)
    q_ajustee: int | None  # défini pour C_inf / C_sup, None sinon
    # Coût rebobinage (LECTURE SEULE moteur existant).
    cout_total_eur: Decimal | None  # None si machine/tarifs absents
    cout_machine_eur: Decimal | None
    cout_mandrins_eur: Decimal | None
    mode_mandrins_optimal: str | None  # "pre_coupe" / "decoupe_interne"


@dataclass(frozen=True)
class AlerteImpose:
    """Détail anti-fléau quand le client impose un nb/bobine.

    `physiquement_impossible=True` si nb_impose > nb_max(Dmax) → la bobine
    dépasse le Ø de la machine de pose. L'opérateur doit alors soit
    repartir au client avec `nb_realisable_max`, soit forcer + motif
    (souveraineté préservée).
    """

    nb_impose: int
    nb_realisable_max: int  # = nb_max(Dmax) (helper CC2)
    diametre_requis_mm: int  # Ø qu'exigerait le nb_impose
    physiquement_impossible: bool


@dataclass(frozen=True)
class PlanificateurResult:
    """Sortie complète planificateur : 3 (ou 4) scénarios + recommandation.

    Scénarios A / B / C_inf / C_sup toujours présents (sauf cas dégénérés).
    Scénario IMPOSE présent uniquement si `nb_etiq_impose` fourni en entrée.
    """

    scenarios: list[ScenarioBobines]
    recommande_cle: ScenarioKey | None  # plus bas coût total, None si pas de coût
    nb_max_par_bobine: int  # nb_max(Ø_dmax) — affiché pour transparence
    pas_mm: float  # = dev + écart_dev — affiché pour transparence
    # Anti-fléau : si nb_etiq_impose fourni, on remonte les diagnostics
    # même si le scénario IMPOSE est physiquement impossible (UI veut
    # afficher les deux chiffres : nb_realisable_max + diametre_requis).
    alerte_impose: AlerteImpose | None = None


def _diametre_pour_nb(
    nb_etiq: int,
    mandrin_mm: int,
    epaisseur_um: float,
    pas_mm: float,
) -> int:
    """Wrapper conservateur : 0 étiq → Ø = mandrin (cohérent CC2)."""
    return calcul_diametre_requis_pour_nb_etiq(
        nb_etiq=nb_etiq,
        mandrin_mm=mandrin_mm,
        epaisseur_matiere_um=epaisseur_um,
        pas_mm=pas_mm,
    )


def _scenario_A(
    R: int,
    n_laize: int,
    nb_max: int,
    Q: int,
    mandrin_mm: int,
    epaisseur_um: float,
    pas_mm: float,
) -> ScenarioBobines:
    """Pleines + reliquat : k bobines de nb_max + 1 partielle si reste > 0."""
    k = R // nb_max
    reste = R - k * nb_max
    repartition: list[RepartitionBobine] = []
    if k > 0:
        repartition.append(
            RepartitionBobine(
                nb_etiq_par_bobine=nb_max,
                nb_bobines_par_piste=k,
                diametre_mm=_diametre_pour_nb(
                    nb_max, mandrin_mm, epaisseur_um, pas_mm
                ),
            )
        )
    if reste > 0:
        repartition.append(
            RepartitionBobine(
                nb_etiq_par_bobine=reste,
                nb_bobines_par_piste=1,
                diametre_mm=_diametre_pour_nb(
                    reste, mandrin_mm, epaisseur_um, pas_mm
                ),
            )
        )
    nb_par_piste = sum(r.nb_bobines_par_piste for r in repartition)
    nb_total = nb_par_piste * n_laize
    quantite_totale = R * n_laize
    return ScenarioBobines(
        cle="A",
        titre="Pleines + reliquat",
        repartition=repartition,
        nb_bobines_par_piste=nb_par_piste,
        nb_bobines_total=nb_total,
        quantite_totale_etiq=quantite_totale,
        surprod_etiq=quantite_totale - Q,
        q_ajustee=None,
        cout_total_eur=None,
        cout_machine_eur=None,
        cout_mandrins_eur=None,
        mode_mandrins_optimal=None,
    )


def _scenario_B(
    R: int,
    n_laize: int,
    nb_max: int,
    Q: int,
    mandrin_mm: int,
    epaisseur_um: float,
    pas_mm: float,
) -> ScenarioBobines:
    """Équilibrées : k bobines ~égales (la dernière absorbe l'arrondi)."""
    if nb_max <= 0:
        # Cohérence avec _scenario_A : on retourne un scénario vide explicite.
        return ScenarioBobines(
            cle="B",
            titre="Équilibrées",
            repartition=[],
            nb_bobines_par_piste=0,
            nb_bobines_total=0,
            quantite_totale_etiq=0,
            surprod_etiq=-Q,
            q_ajustee=None,
            cout_total_eur=None,
            cout_machine_eur=None,
            cout_mandrins_eur=None,
            mode_mandrins_optimal=None,
        )
    k = math.ceil(R / nb_max)
    taille = math.ceil(R / k)  # quasi-égal (≤ nb_max par construction)
    # Les (k-1) premières bobines à `taille`, la dernière absorbe le reste.
    derniere = R - (k - 1) * taille
    repartition: list[RepartitionBobine] = []
    if k > 1:
        repartition.append(
            RepartitionBobine(
                nb_etiq_par_bobine=taille,
                nb_bobines_par_piste=k - 1,
                diametre_mm=_diametre_pour_nb(
                    taille, mandrin_mm, epaisseur_um, pas_mm
                ),
            )
        )
    repartition.append(
        RepartitionBobine(
            nb_etiq_par_bobine=derniere,
            nb_bobines_par_piste=1,
            diametre_mm=_diametre_pour_nb(
                derniere, mandrin_mm, epaisseur_um, pas_mm
            ),
        )
    )
    nb_par_piste = sum(r.nb_bobines_par_piste for r in repartition)
    nb_total = nb_par_piste * n_laize
    quantite_totale = R * n_laize
    return ScenarioBobines(
        cle="B",
        titre="Équilibrées",
        repartition=repartition,
        nb_bobines_par_piste=nb_par_piste,
        nb_bobines_total=nb_total,
        quantite_totale_etiq=quantite_totale,
        surprod_etiq=quantite_totale - Q,
        q_ajustee=None,
        cout_total_eur=None,
        cout_machine_eur=None,
        cout_mandrins_eur=None,
        mode_mandrins_optimal=None,
    )


def _scenario_C(
    cle: Literal["C_inf", "C_sup"],
    R: int,
    n_laize: int,
    nb_max: int,
    Q: int,
    mandrin_mm: int,
    epaisseur_um: float,
    pas_mm: float,
) -> ScenarioBobines | None:
    """Tomber juste : Q' divisible par k × n_laize, bobines pleines égales.

    Stratégie : on cherche un (k, t) avec t ≤ nb_max et k × t ≈ R, exact
    (sans reliquat). t = R / k devient un entier → on balaie k de 1 à
    R, on retient les valeurs entières.

    Variante `C_inf` → propose le Q' ≤ Q le plus proche (taille pleine
    < taille naturelle). `C_sup` → Q' ≥ Q le plus proche.
    """
    if nb_max <= 0 or n_laize <= 0:
        return None
    # On compare `quantite_totale = R' × n_laize` à Q (pas à R) pour
    # garantir que C_inf est STRICTEMENT en dessous de Q et C_sup
    # STRICTEMENT au-dessus. Sinon, sur un Q indivisible par n_laize,
    # les deux scénarios convergent vers le même R' = ceil(Q/n_laize)
    # et le commercial n'a aucune alternative.
    cibles: list[tuple[int, int]] = []  # (R', taille_pleine)
    if cle == "C_sup":
        # R' minimum tel que R' × n_laize > Q, avec bobines pleines ≤ nb_max.
        for k in range(1, R + 2):
            taille = math.ceil(R / k)
            if taille <= 0 or taille > nb_max:
                continue
            r_prime = k * taille
            if r_prime * n_laize > Q:
                cibles.append((r_prime, taille))
        if not cibles:
            return None
        r_prime, taille = min(cibles, key=lambda x: x[0])
    else:  # C_inf
        # R' maximum tel que R' × n_laize < Q, avec bobines pleines ≤ nb_max.
        for k in range(1, R + 1):
            taille = R // k
            if taille <= 0 or taille > nb_max:
                continue
            r_prime = k * taille
            if r_prime * n_laize < Q:
                cibles.append((r_prime, taille))
        if not cibles:
            return None
        r_prime, taille = max(cibles, key=lambda x: x[0])
    k = r_prime // taille
    repartition = [
        RepartitionBobine(
            nb_etiq_par_bobine=taille,
            nb_bobines_par_piste=k,
            diametre_mm=_diametre_pour_nb(
                taille, mandrin_mm, epaisseur_um, pas_mm
            ),
        )
    ]
    nb_par_piste = k
    nb_total = nb_par_piste * n_laize
    quantite_totale = r_prime * n_laize
    titre = (
        "Tomber juste — sup" if cle == "C_sup" else "Tomber juste — inf"
    )
    return ScenarioBobines(
        cle=cle,
        titre=titre,
        repartition=repartition,
        nb_bobines_par_piste=nb_par_piste,
        nb_bobines_total=nb_total,
        quantite_totale_etiq=quantite_totale,
        surprod_etiq=quantite_totale - Q,
        q_ajustee=quantite_totale,
        cout_total_eur=None,
        cout_machine_eur=None,
        cout_mandrins_eur=None,
        mode_mandrins_optimal=None,
    )


def _scenario_IMPOSE(
    R: int,
    n_laize: int,
    Q: int,
    nb_etiq_impose: int,
    mandrin_mm: int,
    epaisseur_um: float,
    pas_mm: float,
) -> ScenarioBobines:
    """Scénario imposé par le client : nb_etiq_par_bobine = nb_etiq_impose.

    Produit k = ceil(R / nb_impose) bobines, dont la dernière est
    partielle si R % nb_impose != 0. NE filtre PAS nb_impose > nb_max :
    la garde anti-fléau remonte dans `alerte_impose` séparément (on
    laisse le scénario apparaître pour transparence : « si tu forces ce
    nb, voilà ce que ça donne »).
    """
    k = math.ceil(R / nb_etiq_impose)
    reste = R - (k - 1) * nb_etiq_impose
    # Ø de la bobine pleine imposée (Ø max effectif du scénario).
    d_pleine = _diametre_pour_nb(
        nb_etiq_impose, mandrin_mm, epaisseur_um, pas_mm
    )
    repartition: list[RepartitionBobine] = []
    if k > 1:
        repartition.append(
            RepartitionBobine(
                nb_etiq_par_bobine=nb_etiq_impose,
                nb_bobines_par_piste=k - 1,
                diametre_mm=d_pleine,
            )
        )
    if reste > 0:
        repartition.append(
            RepartitionBobine(
                nb_etiq_par_bobine=reste,
                nb_bobines_par_piste=1,
                diametre_mm=_diametre_pour_nb(
                    reste, mandrin_mm, epaisseur_um, pas_mm
                ),
            )
        )
    nb_par_piste = sum(r.nb_bobines_par_piste for r in repartition)
    nb_total = nb_par_piste * n_laize
    quantite_totale = R * n_laize
    return ScenarioBobines(
        cle="IMPOSE",
        titre=f"Imposé client ({nb_etiq_impose}/bobine)",
        repartition=repartition,
        nb_bobines_par_piste=nb_par_piste,
        nb_bobines_total=nb_total,
        quantite_totale_etiq=quantite_totale,
        surprod_etiq=quantite_totale - Q,
        q_ajustee=None,
        cout_total_eur=None,
        cout_machine_eur=None,
        cout_mandrins_eur=None,
        mode_mandrins_optimal=None,
    )


def _evaluer_cout_rebobinage(
    scenario: ScenarioBobines,
    pas_mm: float,
    machine: MachineRebobinageParams | None,
    tarifs: TarifsMandrins | None,
    parametres: ParametresMandrinRuntime | None,
) -> ScenarioBobines:
    """Enrichit un scénario avec son coût rebobinage (LECTURE SEULE moteur).

    Si l'un des inputs (machine, tarifs, parametres) est manquant → on
    retourne le scénario inchangé (cost None). Le frontend affiche alors
    « coût indispo » sans casser.

    `nb_bobines` passé est celui DU SCÉNARIO (total devis, donc
    `nb_bobines_total`). On ne modifie pas le moteur, on l'utilise.
    """
    if (
        machine is None
        or tarifs is None
        or parametres is None
        or scenario.nb_bobines_total <= 0
    ):
        return scenario

    # Synthétique ResultatBobines : seuls nb_bobines + longueur_totale_m
    # sont consommés par `calculer_temps_et_cout_machine` ; les autres
    # champs sont remplis avec des valeurs cohérentes pour la sérialisation.
    longueur_totale_m = (
        Decimal(scenario.quantite_totale_etiq) * Decimal(str(pas_mm))
    ) / Decimal(1000)
    # Pour la moyenne (audit) — pas utilisée par le moteur, juste cohérence.
    nb_etiq_moyen = (
        scenario.quantite_totale_etiq // scenario.nb_bobines_total
        if scenario.nb_bobines_total > 0
        else 0
    )
    bobines_synth = ResultatBobines(
        nb_etiq_par_bobine=nb_etiq_moyen,
        nb_bobines=scenario.nb_bobines_total,
        bobine_partielle=any(
            r.nb_etiq_par_bobine != scenario.repartition[0].nb_etiq_par_bobine
            for r in scenario.repartition[1:]
        ),
        nb_etiq_derniere_bobine=scenario.repartition[-1].nb_etiq_par_bobine,
        longueur_totale_m=longueur_totale_m,
    )

    temps = calculer_temps_et_cout_machine(bobines_synth, machine)
    try:
        arbitrage = calculer_arbitrage(
            nb_bobines=scenario.nb_bobines_total,
            tarifs=tarifs,
            parametres=parametres,
            choix=ChoixOperateur(mode="auto"),
        )
    except RebobinageError:
        # Cas marginal : décalage auto → pre_coupe sans scie. On retourne
        # le scénario sans coût plutôt que de propager une 500.
        return scenario

    if arbitrage.mode_applique == "pre_coupe":
        cout_mandrins = arbitrage.cout_pre_coupe_total_eur
    else:
        cout_mandrins = arbitrage.cout_decoupe_interne_total_eur
    cout_total = (temps.cout_machine_eur + cout_mandrins).quantize(
        Decimal("0.0001")
    )

    # ScenarioBobines est frozen — on construit un nouveau dataclass.
    return ScenarioBobines(
        cle=scenario.cle,
        titre=scenario.titre,
        repartition=scenario.repartition,
        nb_bobines_par_piste=scenario.nb_bobines_par_piste,
        nb_bobines_total=scenario.nb_bobines_total,
        quantite_totale_etiq=scenario.quantite_totale_etiq,
        surprod_etiq=scenario.surprod_etiq,
        q_ajustee=scenario.q_ajustee,
        cout_total_eur=cout_total,
        cout_machine_eur=temps.cout_machine_eur,
        cout_mandrins_eur=cout_mandrins,
        mode_mandrins_optimal=arbitrage.mode_optimal,
    )


def calculer_plan_bobines(
    *,
    quantite_commandee: int,
    n_laize: int,
    pas_mm: float,
    mandrin_mm: int,
    diametre_max_bobine_mm: float,
    epaisseur_matiere_um: float,
    nb_etiq_impose: int | None = None,
    machine: MachineRebobinageParams | None = None,
    tarifs: TarifsMandrins | None = None,
    parametres: ParametresMandrinRuntime | None = None,
) -> PlanificateurResult:
    """Construit les 3 scénarios + recommandation.

    Inputs géométriques obligatoires (Q, n_laize, pas, mandrin, dmax, ε).
    Inputs cost optionnels (machine, tarifs, parametres) : si présents,
    chaque scénario porte son coût rebobinage et la `recommande_cle`
    désigne le moins cher ; sinon, scénarios renvoyés sans coût et
    `recommande_cle = None`.

    Raises:
      ValueError : Q ≤ 0, n_laize ≤ 0, pas ≤ 0, Dmax ≤ mandrin, ε ≤ 0.
    """
    if quantite_commandee <= 0:
        raise ValueError(f"quantite_commandee doit être > 0 (reçu {quantite_commandee})")
    if n_laize <= 0:
        raise ValueError(f"n_laize doit être > 0 (reçu {n_laize})")
    if pas_mm <= 0:
        raise ValueError(f"pas_mm doit être > 0 (reçu {pas_mm})")
    if epaisseur_matiere_um <= 0:
        raise ValueError(
            f"epaisseur_matiere_um doit être > 0 (reçu {epaisseur_matiere_um})"
        )
    if diametre_max_bobine_mm <= mandrin_mm:
        raise ValueError(
            f"diametre_max_bobine_mm ({diametre_max_bobine_mm}) doit être > "
            f"mandrin_mm ({mandrin_mm})"
        )

    Q = quantite_commandee
    R = math.ceil(Q / n_laize)
    nb_max = calcul_nb_max_etiq_pour_diametre(
        diametre_ext_mm=diametre_max_bobine_mm,
        mandrin_mm=mandrin_mm,
        epaisseur_matiere_um=epaisseur_matiere_um,
        pas_mm=pas_mm,
    )

    scenarios: list[ScenarioBobines] = []
    scenarios.append(
        _scenario_A(R, n_laize, nb_max, Q, mandrin_mm, epaisseur_matiere_um, pas_mm)
    )
    scenarios.append(
        _scenario_B(R, n_laize, nb_max, Q, mandrin_mm, epaisseur_matiere_um, pas_mm)
    )
    sc_inf = _scenario_C(
        "C_inf", R, n_laize, nb_max, Q, mandrin_mm, epaisseur_matiere_um, pas_mm
    )
    sc_sup = _scenario_C(
        "C_sup", R, n_laize, nb_max, Q, mandrin_mm, epaisseur_matiere_um, pas_mm
    )
    if sc_inf is not None:
        scenarios.append(sc_inf)
    if sc_sup is not None:
        scenarios.append(sc_sup)

    # Scénario imposé + garde anti-fléau. On l'ajoute SEULEMENT si l'input
    # est fourni (le commercial a saisi un nb client) — sinon on évite de
    # polluer l'UI avec un scénario hors contexte.
    alerte_impose: AlerteImpose | None = None
    if nb_etiq_impose is not None and nb_etiq_impose > 0:
        scenarios.append(
            _scenario_IMPOSE(
                R,
                n_laize,
                Q,
                nb_etiq_impose,
                mandrin_mm,
                epaisseur_matiere_um,
                pas_mm,
            )
        )
        # Diagnostic anti-fléau : remontre les 2 chiffres clés que le
        # commercial doit annoncer au client si le nb voulu dépasse Dmax.
        # Ø requis : on calcule via la SSOT forward (calcul_diametre_bobine)
        # pour rester cohérent avec l'inverse `calcul_diametre_requis_*`.
        ml_impose_m = nb_etiq_impose * pas_mm / 1000.0
        d_pour_impose = calcul_diametre_bobine(
            ml_total_m=ml_impose_m,
            epaisseur_matiere_um=epaisseur_matiere_um,
            mandrin_mm=mandrin_mm,
            # La laize papier ne change pas le calcul Ø (volumétrique
            # par section transverse) : on passe un placeholder > 0.
            laize_papier_mm=100.0,
        )
        alerte_impose = AlerteImpose(
            nb_impose=nb_etiq_impose,
            nb_realisable_max=nb_max,
            diametre_requis_mm=d_pour_impose,
            physiquement_impossible=nb_etiq_impose > nb_max,
        )

    # Enrichit chaque scénario avec son coût rebobinage (lecture seule).
    scenarios = [
        _evaluer_cout_rebobinage(s, pas_mm, machine, tarifs, parametres)
        for s in scenarios
    ]

    # Recommandation = coût total le plus bas (parmi ceux qui ont un coût).
    # Le scénario IMPOSE n'entre PAS dans la recommandation : il est
    # imposé externe, le commercial doit l'utiliser tel quel (ou repartir
    # au client). Recommander un autre serait trompeur.
    avec_cout = [
        s for s in scenarios if s.cout_total_eur is not None and s.cle != "IMPOSE"
    ]
    recommande_cle: ScenarioKey | None = None
    if avec_cout:
        recommande = min(avec_cout, key=lambda s: s.cout_total_eur)  # type: ignore[arg-type,return-value]
        recommande_cle = recommande.cle

    return PlanificateurResult(
        scenarios=scenarios,
        recommande_cle=recommande_cle,
        nb_max_par_bobine=nb_max,
        pas_mm=pas_mm,
        alerte_impose=alerte_impose,
    )
