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

import type {
  DevisDetail,
  LotProductionRead,
  OptimisationConfigOut,
  SensEnroulement,
} from "@/lib/api";

// Brief #33 — étape 4 chiffrage ajoutée (options globales, marge, réduction).
export type EtapeOptim = "saisie" | "candidats" | "detail" | "chiffrage";

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
  goChiffrage: () => void;

  // Contexte saisie nécessaire aux étapes 2/3 (validation somme,
  // affichage récap, props composant visuel).
  quantiteTotale: number;
  laizeEtiqMm: number;
  devEtiqMm: number;
  mandrinMm: number;

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

  // Brief #33 — étape 4 state.
  const [optionsCodes, setOptionsCodes] = useState<string[]>([]);
  const [margeOverridePct, setMargeOverridePct] = useState<string>("");
  const [reductionPct, setReductionPct] = useState<string>("0");
  const [devisExistantId, setDevisExistantId] = useState<number | null>(null);
  const [devisExistantNumero, setDevisExistantNumero] = useState<string | null>(
    null
  );

  const goSaisie = useCallback(() => {
    setEtape("saisie");
    setSelection([]);
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

    // 5. Mode édition + bascule sur étape 4 ouverte par défaut.
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
      goChiffrage,
      quantiteTotale,
      laizeEtiqMm,
      devEtiqMm,
      mandrinMm,
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
      hydrateFromDevisExistant,
    }),
    [
      etape,
      goSaisie,
      goCandidats,
      goDetail,
      goChiffrage,
      quantiteTotale,
      laizeEtiqMm,
      devEtiqMm,
      mandrinMm,
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
