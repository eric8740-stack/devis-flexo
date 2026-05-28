"use client";

/**
 * Store React Context — workflow Optimisation Pose 3 étapes (Sprint 13 avenant).
 *
 * Centralise la state machine 'saisie' → 'candidats' → 'detail' + les
 * données qui transitent entre étapes (params saisis, candidats moteur,
 * sélection avec quantités, matières par lot).
 *
 * Utilisation :
 *   <OptimisationPoseProvider>
 *     <ComposantsConsommateurs />  // useOptimisationPose()
 *   </OptimisationPoseProvider>
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  getClient,
  type Client,
  type DevisDetail,
  type LotProductionRead,
  type OptimisationConfigOut,
  type RebobinageCalculerRequest,
  type RebobinageResultat,
  type SensEnroulement,
} from "@/lib/api";
import type { MatcherOutilMatch } from "@/lib/api/matcherOutil";

import {
  extractBriefClientFromDevis,
  mergeBriefClient,
} from "./brief-client/store-helpers";
import {
  BRIEF_CLIENT_DEFAULTS,
  type BriefClientData,
} from "./brief-client/types";

// Sprint 16 Lot D — étape "rebobinage" insérée entre "detail" et "chiffrage" :
// paramètres bobine client + calcul nb bobines / temps / coût + arbitrage
// pré-coupé vs découpe interne.
export type EtapeOptim =
  | "saisie"
  | "candidats"
  | "detail"
  | "rebobinage"
  | "chiffrage";

export interface ParamsSaisie {
  laize: string;
  dev: string;
  rayonAngles: string;
  formeCourbe: boolean;
  intervalleDevMin: string;
  contrainteClientMm: string;
  nbCouleurs: string;
  quantiteTotale: string;
  matiereTransparente: boolean;
  selectedOptions: Set<string>;
  mandrin: number;
  sensEnroulement: SensEnroulement;
  epaisseurMatiere: string;
  nbPosesLaizeMode: "auto" | "force";
  nbPosesLaizeForce: string;
  // Souveraineté commerciale (forçages + lacets).
  forcerIntervalleLaize: boolean;
  intervalleLaizeForce: string;
  motifIntervalleLaize: string;
  forcerIntervalleDev: boolean;
  intervalleDevForce: string;
  motifIntervalleDev: string;
  lacetsAsymetriques: boolean;
  lacetDroit: string;
  lacetGauche: string;
}

/**
 * Construit un id stable pour un candidat (utilisé pour les checkboxes
 * + endpoint visuel). Format : '<cyl>-<mach>-<dev>x<laize>-SE<n>'.
 * Doit rester identique au backend (router /candidats/{id}/visuel).
 */
export function buildIdCandidat(c: OptimisationConfigOut): string {
  return `${c.cylindre_id}-${c.machine_id}-${c.nb_poses_dev}x${c.nb_poses_laize}-${c.sens_enroulement}`;
}

export interface SelectionLot {
  id_candidat: string;
  candidat: OptimisationConfigOut;
  quantite: number;
  matiere_id: number | null;
}

interface OptimisationPoseContextValue {
  etape: EtapeOptim;
  goSaisie: () => void;
  goCandidats: (
    candidats: OptimisationConfigOut[],
    quantiteTotale: number,
    laizeEtiq: number,
    devEtiq: number,
    mandrin: number,
  ) => void;
  goDetail: () => void;
  goRebobinage: () => void;
  goChiffrage: () => void;

  // Contexte saisie nécessaire aux étapes 2/3 (validation somme,
  // affichage récap, props composant visuel).
  quantiteTotale: number;
  laizeEtiqMm: number;
  devEtiqMm: number;
  mandrinMm: number;

  // Fix couleurs — nb de couleurs d'impression saisi à l'étape 1, transporté
  // jusqu'au chiffrage pour alimenter `payload_input.nb_couleurs.impression`
  // (POST /devis + preview live). Le backend (fix CC1) lit ce champ pour le
  // Poste 2 Encres ; sans lui, le devis optim est sous-évalué (encres = 0).
  // Seul `impression` provient du store : pantone/blanc/vernis n'existent pas
  // encore à la saisie → envoyés à 0 par OptimisationChiffrage.
  nbCouleursImpression: number;
  setNbCouleursImpression: (n: number) => void;

  // Avertissements non bloquants remontés par /api/optimisation/calculer
  // (ex. forçage intervalle laize hors recommandation moteur, motif manquant).
  // Affichés en bandeau orange à l'étape candidats. Réinitialisé à chaque
  // nouvelle soumission saisie (goSaisie / nouveau goCandidats).
  optimWarnings: string[];
  setOptimWarnings: (warnings: string[]) => void;

  candidats: OptimisationConfigOut[];
  selection: SelectionLot[];
  toggleSelection: (candidat: OptimisationConfigOut) => void;
  setQuantiteLot: (id_candidat: string, quantite: number) => void;
  setMatiereLot: (id_candidat: string, matiere_id: number) => void;

  sommeQuantitesLots: number;

  // Brief #33 — étape 4 chiffrage : options globales + marge + réduction.
  optionsCodes: string[];
  toggleOption: (code: string) => void;
  margeOverridePct: string;
  setMargeOverridePct: (v: string) => void;
  reductionPct: string;
  setReductionPct: (v: string) => void;

  // Brief #33 — mode édition : si défini, on PUT au lieu de POST.
  devisExistantId: number | null;
  devisExistantNumero: string | null;
  setModeEdition: (id: number, numero: string) => void;

  // Sprint 14 Lot 4.2 — brief client unifié (Rouleau livré, Matière &
  // stockage, Type d'entrée fichier). `setBriefClient` accepte un patch
  // partiel ; merge profond sur `conditions_stockage` (cf helper).
  briefClient: BriefClientData;
  setBriefClient: (patch: Partial<BriefClientData>) => void;

  // Sprint 14 Lot 4.5 — outil compatible sélectionné via le matcher.
  // null tant que l'utilisateur n'a pas cliqué un match. Objet complet
  // (pas que l'id) pour permettre l'affichage récap sans re-fetch.
  outilSelectionne: MatcherOutilMatch | null;
  setOutilSelectionne: (match: MatcherOutilMatch | null) => void;

  // Sprint 16 Lot D câblage — request et result du dernier calcul
  // rebobinage. Persistés côté store pour : (1) restaurer l'écran si
  // l'opérateur revient depuis chiffrage, (2) permettre à
  // OptimisationChiffrage d'appliquer la ligne sur le devis via
  // applyRebobinageDevis après création/update.
  rebobinageRequest: RebobinageCalculerRequest | null;
  rebobinageResult: RebobinageResultat | null;
  setRebobinage: (
    req: RebobinageCalculerRequest,
    result: RebobinageResultat,
  ) => void;
  clearRebobinage: () => void;

  // Sprint 16 — client du devis sélectionné dans le workflow optimisation.
  // Source de vérité unique pour l'auto-remplissage de l'étape rebobinage
  // (depuis les 9 champs profil) ET pour le client_id envoyé au POST/PUT
  // devis dans l'étape chiffrage. Hydraté en mode édition depuis
  // `devis.client_id` ; en mode création, set manuellement via le
  // sélecteur en tête de l'étape rebobinage ou de l'étape chiffrage.
  clientSelectionne: Client | null;
  setClientSelectionne: (client: Client | null) => void;

  // Sprint 16 — sens d'enroulement profil client (entier 1..8) transporté
  // séparément du `rebobinageRequest` car non consommé par le backend
  // /api/rebobinage/calculer. Propagé dans `payload_input.sens_enroulement`
  // du devis au POST/PUT depuis OptimisationChiffrage. Pré-rempli depuis
  // `clientSelectionne.sens_enroulement` ; override possible côté UI.
  // Invariant : simple stockage d'un entier brut, aucune logique de
  // rotation / interprétation (le Lot E reste gated).
  sensEnroulementClient: number | null;
  setSensEnroulementClient: (n: number | null) => void;

  // Brief #33 commit 3 — hydratation depuis un devis existant. Reconstruit
  // selection + candidats minimum à partir de `lots_production`, lit
  // payload_input pour options/marge/laize/dev/mandrin, bascule sur
  // l'étape 4 (chiffrage) ouverte par défaut.
  hydrateFromDevisExistant: (devis: DevisDetail) => void;
}

/**
 * Reconstruit un OptimisationConfigOut à partir d'un LotProductionRead.
 *
 * Brief #33 commit 5 — si `lot.payload_visuel` est présent (snapshot
 * complet du candidat à la création), on l'utilise directement : le
 * visuel SchemaImplantation sera fidèle au moment de la création. Sinon
 * (lots historiques antérieurs au brief), on reconstruit un fallback
 * minimal à partir des joints Brief #32 — visuel approximatif (laize
 * papier, chute latérale, ø bobine seront à 0).
 */
function _lotToCandidatPartiel(lot: LotProductionRead): OptimisationConfigOut {
  if (lot.payload_visuel && typeof lot.payload_visuel === "object") {
    return lot.payload_visuel as unknown as OptimisationConfigOut;
  }
  return {
    cylindre_id: lot.cylindre_id,
    machine_id: lot.machine_id,
    nb_poses_dev: lot.nb_poses_dev,
    nb_poses_laize: lot.nb_poses_laize,
    nb_poses_total: lot.nb_poses_dev * lot.nb_poses_laize,
    intervalle_dev_reel_mm: parseFloat(lot.intervalle_dev_reel_mm ?? "0"),
    intervalle_laize_reel_mm: parseFloat(lot.intervalle_laize_reel_mm ?? "0"),
    largeur_plaque_mm: parseFloat(lot.largeur_plaque_mm ?? "0"),
    z_mini_effet_banane: 0,
    qualite_echenillage: "—",
    consolidation_atteinte: false,
    intervalle_laize_souhaitable_mm: null,
    disposition_poses: "",
    coef_vitesse_echenillage: 1,
    coef_gache_echenillage: 1,
    coef_confort_rayon: 1,
    coef_quinconce: 1,
    coef_consolidation: 1,
    coef_vitesse_options: 1,
    coef_gache_options: 1,
    coef_vitesse_final: 1,
    coef_gache_final: 1,
    score: lot.score_optim ?? 0,
    laize_plaque_mm: parseFloat(lot.largeur_plaque_mm ?? "0"),
    laize_papier_mm: 0,
    chute_laterale_reelle_mm: 0,
    z_cylindre_mm: parseFloat(lot.cylindre_developpe_mm ?? "0"),
    nb_dents_cylindre: lot.cylindre_nb_dents ?? 0,
    ml_total_m: 0,
    m2_consomme: 0,
    rendement_pct: 0,
    diametre_bobine_mm: 0,
    laize_liner_mm: 0,
    sens_enroulement: `SE${lot.sens_enroulement}` as SensEnroulement,
    sens_enroulement_libelle: lot.sens_enroulement_libelle ?? "",
    rotation_vue_a_deg: lot.rotation_vue_a_deg ?? 0,
    rotation_vue_c_deg: lot.rotation_vue_c_deg ?? 0,
    machines_compatibles: [lot.machine_id],
    noms_machines_compatibles: [
      lot.machine_nom ?? `Machine #${lot.machine_id}`,
    ],
    petit_cylindre: (lot.cylindre_nb_dents ?? 999) <= 80,
    intervalle_laize_recommande_mm: parseFloat(
      lot.intervalle_laize_reel_mm ?? "0"
    ),
    intervalle_laize_applique_mm: parseFloat(
      lot.intervalle_laize_reel_mm ?? "0"
    ),
    forcage_intervalle_laize: false,
    motif_forcage_intervalle_laize: null,
    intervalle_dev_recommande_mm: parseFloat(
      lot.intervalle_dev_reel_mm ?? "0"
    ),
    intervalle_dev_applique_mm: parseFloat(
      lot.intervalle_dev_reel_mm ?? "0"
    ),
    forcage_intervalle_dev: false,
    motif_forcage_intervalle_dev: null,
    lacet_droit_mm: 0,
    lacet_gauche_mm: 0,
    lacets_asymetriques: false,
    matiere: null,
    epaisseur_appliquee_um: 0,
    forcage_epaisseur: false,
    motif_forcage_epaisseur: null,
  };
}

const OptimisationPoseContext =
  createContext<OptimisationPoseContextValue | null>(null);

export function OptimisationPoseProvider({ children }: { children: ReactNode }) {
  const [etape, setEtape] = useState<EtapeOptim>("saisie");
  const [candidats, setCandidats] = useState<OptimisationConfigOut[]>([]);
  const [selection, setSelection] = useState<SelectionLot[]>([]);
  const [quantiteTotale, setQuantiteTotale] = useState<number>(0);
  const [laizeEtiqMm, setLaizeEtiqMm] = useState<number>(0);
  const [devEtiqMm, setDevEtiqMm] = useState<number>(0);
  const [mandrinMm, setMandrinMm] = useState<number>(76);
  // Fix couleurs — nb couleurs impression (étape 1). Défaut 0 : si l'opérateur
  // n'est pas passé par la saisie (ex. édition hydratée), on n'invente pas de
  // couleurs ; le backend retombe sur 0 encre, cohérent avec l'ancien comportement.
  const [nbCouleursImpression, setNbCouleursImpression] = useState<number>(0);
  const [optimWarnings, setOptimWarnings] = useState<string[]>([]);

  // Brief #33 — étape 4 state.
  const [optionsCodes, setOptionsCodes] = useState<string[]>([]);
  const [margeOverridePct, setMargeOverridePct] = useState<string>("");
  const [reductionPct, setReductionPct] = useState<string>("0");
  const [devisExistantId, setDevisExistantId] = useState<number | null>(null);
  const [devisExistantNumero, setDevisExistantNumero] = useState<string | null>(
    null
  );

  // Sprint 14 Lot 4.2 — brief client unifié state (Rouleau livré /
  // Matière & stockage / Type d'entrée fichier). Defaults backend Lot 1.
  const [briefClient, setBriefClientState] = useState<BriefClientData>(
    BRIEF_CLIENT_DEFAULTS,
  );

  const setBriefClient = useCallback(
    (patch: Partial<BriefClientData>) => {
      setBriefClientState((prev) => mergeBriefClient(prev, patch));
    },
    [],
  );

  // Sprint 14 Lot 4.5 — outil sélectionné via matcher-outil.
  const [outilSelectionne, setOutilSelectionne] =
    useState<MatcherOutilMatch | null>(null);

  // Sprint 16 Lot D — request et result du dernier calcul rebobinage.
  const [rebobinageRequest, setRebobinageRequest] =
    useState<RebobinageCalculerRequest | null>(null);
  const [rebobinageResult, setRebobinageResult] =
    useState<RebobinageResultat | null>(null);

  const setRebobinage = useCallback(
    (req: RebobinageCalculerRequest, result: RebobinageResultat) => {
      setRebobinageRequest(req);
      setRebobinageResult(result);
    },
    [],
  );

  const clearRebobinage = useCallback(() => {
    setRebobinageRequest(null);
    setRebobinageResult(null);
  }, []);

  // Sprint 16 — client sélectionné + sens enroulement profil.
  const [clientSelectionne, setClientSelectionneState] =
    useState<Client | null>(null);
  const [sensEnroulementClient, setSensEnroulementClientState] =
    useState<number | null>(null);

  const setClientSelectionne = useCallback((client: Client | null) => {
    setClientSelectionneState(client);
    // Auto-fill du sens enroulement depuis le profil au changement de
    // client — l'utilisateur peut ensuite l'overrider via le setter
    // dédié. Si l'utilisateur a déjà overridé puis change de client,
    // on écrase ; pas de double-état "overridé vs profil" pour rester
    // KISS.
    if (client) {
      setSensEnroulementClientState(client.sens_enroulement);
    } else {
      setSensEnroulementClientState(null);
    }
  }, []);

  const setSensEnroulementClient = useCallback((n: number | null) => {
    setSensEnroulementClientState(n);
  }, []);

  const goSaisie = useCallback(() => {
    setEtape("saisie");
    setSelection([]);
    // Re-saisie : on repart d'une page candidats sans warnings pendants
    // (la prochaine soumission posera la nouvelle liste, ou vide).
    setOptimWarnings([]);
  }, []);
  const goCandidats = useCallback(
    (
      c: OptimisationConfigOut[],
      qte: number,
      laize: number,
      dev: number,
      mandrin: number,
    ) => {
      setCandidats(c);
      setSelection([]);
      setQuantiteTotale(qte);
      setLaizeEtiqMm(laize);
      setDevEtiqMm(dev);
      setMandrinMm(mandrin);
      setEtape("candidats");
    },
    []
  );
  const goDetail = useCallback(() => setEtape("detail"), []);
  const goRebobinage = useCallback(() => setEtape("rebobinage"), []);
  const goChiffrage = useCallback(() => setEtape("chiffrage"), []);

  const toggleOption = useCallback((code: string) => {
    setOptionsCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }, []);

  const setModeEdition = useCallback((id: number, numero: string) => {
    setDevisExistantId(id);
    setDevisExistantNumero(numero);
  }, []);

  const hydrateFromDevisExistant = useCallback((devis: DevisDetail) => {
    // 1. Reconstruit les candidats minimaux + selection à partir des lots
    //    snapshotés. Si le devis n'a pas de lots_production (legacy mono-
    //    config), la liste est vide → on bascule quand même sur étape 4
    //    avec selection vide ; l'utilisateur devra repasser par étape 1.
    const lots = devis.lots_production ?? [];
    const candidatsReconstruits = lots.map((lot) => _lotToCandidatPartiel(lot));
    const selectionReconstruite: SelectionLot[] = lots.map((lot, idx) => {
      const candidat = candidatsReconstruits[idx]!;
      return {
        id_candidat: buildIdCandidat(candidat),
        candidat,
        quantite: lot.quantite,
        matiere_id: lot.matiere_id,
      };
    });
    setCandidats(candidatsReconstruits);
    setSelection(selectionReconstruite);

    // 2. Restaure contexte étape 1 depuis payload_input.
    const payloadInput = (devis.payload_input ?? {}) as Record<string, unknown>;
    const qteTotale = lots.reduce((sum, l) => sum + l.quantite, 0);
    setQuantiteTotale(qteTotale);
    setLaizeEtiqMm(
      typeof payloadInput.format_etiquette_largeur_mm === "number"
        ? payloadInput.format_etiquette_largeur_mm
        : parseFloat(devis.format_l_mm)
    );
    setDevEtiqMm(
      typeof payloadInput.format_etiquette_hauteur_mm === "number"
        ? payloadInput.format_etiquette_hauteur_mm
        : parseFloat(devis.format_h_mm)
    );
    setMandrinMm(
      typeof payloadInput.mandrin_mm === "number"
        ? payloadInput.mandrin_mm
        : 76
    );
    // Fix couleurs — restaure nb couleurs impression depuis le nouveau
    // champ `nb_couleurs.impression` (devis créés après le fix). Devis
    // antérieurs : champ absent → 0.
    const nbCouleurs = payloadInput.nb_couleurs as
      | { impression?: unknown }
      | undefined;
    setNbCouleursImpression(
      nbCouleurs && typeof nbCouleurs.impression === "number"
        ? nbCouleurs.impression
        : 0
    );

    // 3. Restaure état étape 4 depuis payload_input.
    setOptionsCodes(
      Array.isArray(payloadInput.options_codes_etape4)
        ? (payloadInput.options_codes_etape4 as string[])
        : []
    );
    const margeOverride = payloadInput.pct_marge_override;
    setMargeOverridePct(
      typeof margeOverride === "number"
        ? String(margeOverride)
        : typeof margeOverride === "string"
          ? margeOverride
          : ""
    );

    // 4. Restaure réduction commerciale (champ devis.reduction_pct).
    setReductionPct(devis.reduction_pct ?? "0");

    // 5. Sprint 14 Lot 4.2 — restaure brief client (5 champs columns).
    setBriefClientState(extractBriefClientFromDevis(devis));

    // 6. Sprint 16 — restaure le client sélectionné depuis devis.client_id
    //    (fire-and-forget : si le fetch échoue, le composant rebobinage
    //    affichera juste le sélecteur vide ; pas d'erreur bloquante).
    //    Au retour : auto-remplissage du sens_enroulement profil via le
    //    setter dédié (cf. setClientSelectionne ci-dessus).
    if (devis.client_id !== null) {
      getClient(devis.client_id)
        .then((client) => {
          setClientSelectionneState(client);
          setSensEnroulementClientState(client.sens_enroulement);
        })
        .catch(() => {
          // Silencieux : le client peut être désactivé ou supprimé.
          setClientSelectionneState(null);
          setSensEnroulementClientState(null);
        });
    } else {
      setClientSelectionneState(null);
      setSensEnroulementClientState(null);
    }

    // 7. Mode édition + bascule sur étape 4 ouverte par défaut.
    setDevisExistantId(devis.id);
    setDevisExistantNumero(devis.numero);
    setEtape("chiffrage");
  }, []);

  const toggleSelection = useCallback(
    (candidat: OptimisationConfigOut) => {
      const id = buildIdCandidat(candidat);
      setSelection((prev) => {
        const exist = prev.find((s) => s.id_candidat === id);
        if (exist) return prev.filter((s) => s.id_candidat !== id);
        // Patch #31 — auto-fill du 1er lot avec la quantité totale du
        // devis. Cas le plus fréquent : utilisateur veut un seul lot
        // sur la qté totale, on évite la friction du "saisir 10000".
        // 2ème lot et suivants → quantite=0 (user saisit la répartition).
        const quantiteAuto = prev.length === 0 ? quantiteTotale : 0;
        return [
          ...prev,
          {
            id_candidat: id,
            candidat,
            quantite: quantiteAuto,
            matiere_id: null,
          },
        ];
      });
    },
    [quantiteTotale]
  );

  const setQuantiteLot = useCallback(
    (id_candidat: string, quantite: number) => {
      setSelection((prev) =>
        prev.map((s) =>
          s.id_candidat === id_candidat ? { ...s, quantite } : s
        )
      );
    },
    []
  );

  const setMatiereLot = useCallback(
    (id_candidat: string, matiere_id: number) => {
      setSelection((prev) =>
        prev.map((s) =>
          s.id_candidat === id_candidat ? { ...s, matiere_id } : s
        )
      );
    },
    []
  );

  const sommeQuantitesLots = useMemo(
    () => selection.reduce((sum, s) => sum + (s.quantite || 0), 0),
    [selection]
  );

  const value = useMemo<OptimisationPoseContextValue>(
    () => ({
      etape,
      goSaisie,
      goCandidats,
      goDetail,
      goRebobinage,
      goChiffrage,
      quantiteTotale,
      laizeEtiqMm,
      devEtiqMm,
      mandrinMm,
      nbCouleursImpression,
      setNbCouleursImpression,
      optimWarnings,
      setOptimWarnings,
      candidats,
      selection,
      toggleSelection,
      setQuantiteLot,
      setMatiereLot,
      sommeQuantitesLots,
      optionsCodes,
      toggleOption,
      margeOverridePct,
      setMargeOverridePct,
      reductionPct,
      setReductionPct,
      devisExistantId,
      devisExistantNumero,
      setModeEdition,
      briefClient,
      setBriefClient,
      outilSelectionne,
      setOutilSelectionne,
      rebobinageRequest,
      rebobinageResult,
      setRebobinage,
      clearRebobinage,
      clientSelectionne,
      setClientSelectionne,
      sensEnroulementClient,
      setSensEnroulementClient,
      hydrateFromDevisExistant,
    }),
    [
      etape,
      goSaisie,
      goCandidats,
      goDetail,
      goRebobinage,
      goChiffrage,
      quantiteTotale,
      laizeEtiqMm,
      devEtiqMm,
      mandrinMm,
      nbCouleursImpression,
      setNbCouleursImpression,
      optimWarnings,
      setOptimWarnings,
      candidats,
      selection,
      toggleSelection,
      setQuantiteLot,
      setMatiereLot,
      sommeQuantitesLots,
      optionsCodes,
      toggleOption,
      margeOverridePct,
      reductionPct,
      devisExistantId,
      devisExistantNumero,
      setModeEdition,
      briefClient,
      setBriefClient,
      outilSelectionne,
      rebobinageRequest,
      rebobinageResult,
      setRebobinage,
      clearRebobinage,
      clientSelectionne,
      setClientSelectionne,
      sensEnroulementClient,
      setSensEnroulementClient,
      hydrateFromDevisExistant,
    ]
  );

  return (
    <OptimisationPoseContext.Provider value={value}>
      {children}
    </OptimisationPoseContext.Provider>
  );
}

export function useOptimisationPose(): OptimisationPoseContextValue {
  const ctx = useContext(OptimisationPoseContext);
  if (!ctx) {
    throw new Error(
      "useOptimisationPose doit être appelé dans un OptimisationPoseProvider"
    );
  }
  return ctx;
}
