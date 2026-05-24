"use client";

import { SectionMatiereStockage } from "./brief-client/SectionMatiereStockage";
import { SectionRouleauLivre } from "./brief-client/SectionRouleauLivre";
import { SectionTypeEntreeFichier } from "./brief-client/SectionTypeEntreeFichier";
import type { BriefClientData } from "./brief-client/types";
import { useOptimisationPose } from "./OptimisationPoseStore";

// Sprint 14 Lot 4.3 — orchestrateur du brief client unifié.
// Plus de state local ; les valeurs viennent du store
// `OptimisationPoseProvider` (Lot 4.2). Les sous-composants gardent leur
// signature (`value` + `onChange` plein) — on adapte ici en wrappant
// `setBriefClient` qui accepte un Partial.

export { BRIEF_CLIENT_DEFAULTS } from "./brief-client/types";
export type {
  BriefClientData,
  TypeEntreeFichier,
} from "./brief-client/types";

export function BriefClientForm() {
  const { briefClient, setBriefClient } = useOptimisationPose();

  // Les sous-composants émettent un BriefClientData complet — on l'envoie
  // tel quel au setter partiel du store (un Data est un Partial<Data>).
  const handleChange = (next: BriefClientData) => setBriefClient(next);

  return (
    <div className="space-y-6">
      <SectionRouleauLivre value={briefClient} onChange={handleChange} />
      <SectionMatiereStockage value={briefClient} onChange={handleChange} />
      <SectionTypeEntreeFichier value={briefClient} onChange={handleChange} />
    </div>
  );
}
