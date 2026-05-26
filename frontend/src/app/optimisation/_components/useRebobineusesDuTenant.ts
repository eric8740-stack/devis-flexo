"use client";

/**
 * Sprint 16 — Hook de chargement des rebobineuses du tenant courant.
 *
 * **État du contrat** : l'endpoint backend `GET /api/machines-rebobineuses`
 * n'est PAS encore mergé sur main au moment de ce commit. On expose ici
 * un contrat stable côté UI (`MachineRebobineuseLite`, états
 * loading / error / machines) et une implémentation placeholder qui
 * renvoie une seule rebobineuse virtuelle id=1.
 *
 * Le placeholder préserve le comportement actuel de la prod (qui hardcode
 * `machine_rebobineuse_id=1`) tout en faisant disparaître la constante
 * `MACHINE_REBOBINEUSE_ID_DEFAUT` du composant. Quand CC #1 mergera
 * l'endpoint, le câblage final = remplacer le corps de ce hook par un
 * `useEffect + fetch /api/machines-rebobineuses` ; le composant
 * consommateur et ses tests restent inchangés.
 *
 * Champs exposés volontairement minimaux (nom + actif) pour permettre à
 * l'UI de rendre un select sans avoir à connaître les détails moteur
 * (vitesse_pratique_m_min, cout_horaire_eur, etc. — ces champs restent
 * côté backend pour le calcul).
 */
import { useMemo } from "react";

export interface MachineRebobineuseLite {
  id: number;
  nom: string;
  // `actif=false` n'est pas filtré côté UI : si le backend renvoie une
  // machine inactive, on l'affiche tout de même mais avec un libellé
  // visible. Le backend reste responsable du filtre par défaut.
  actif: boolean;
}

interface UseRebobineusesResult {
  machines: MachineRebobineuseLite[];
  loading: boolean;
  error: string | null;
}

// TODO commit de câblage (suit le merge de l'endpoint backend) :
// remplacer le corps du hook par un useEffect + fetch authentifié vers
// /api/machines-rebobineuses. Garder la même signature de retour.
//
// const [machines, setMachines] = useState<MachineRebobineuseLite[]>([]);
// const [loading, setLoading] = useState(true);
// const [error, setError] = useState<string | null>(null);
// useEffect(() => { ... fetch ... }, []);
// return { machines, loading, error };
const PLACEHOLDER_MACHINES: MachineRebobineuseLite[] = [
  {
    id: 1,
    // Libellé identifiable : l'opérateur sait que ce n'est pas une
    // rebobineuse de son parc tant que l'endpoint n'est pas câblé.
    nom: "Rebobineuse par défaut (en attente du parc tenant)",
    actif: true,
  },
];

export function useRebobineusesDuTenant(): UseRebobineusesResult {
  // useMemo pour stabiliser la référence et éviter de re-déclencher les
  // useEffect consommateurs à chaque render.
  const machines = useMemo(() => PLACEHOLDER_MACHINES, []);
  return { machines, loading: false, error: null };
}
