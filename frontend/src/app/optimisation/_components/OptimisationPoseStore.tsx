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
