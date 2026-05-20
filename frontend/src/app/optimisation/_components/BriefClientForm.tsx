"use client";

import { SectionMatiereStockage } from "./brief-client/SectionMatiereStockage";
import { SectionRouleauLivre } from "./brief-client/SectionRouleauLivre";
import { SectionTypeEntreeFichier } from "./brief-client/SectionTypeEntreeFichier";
import type { BriefClientData } from "./brief-client/types";

// Sprint 14 Lot 3 — orchestrateur léger du brief client unifié.
// Trois sections empilées (Rouleau livré, Matière & stockage, Type
// d'entrée fichier). Mobile-first 375 px géré dans chaque sous-section.

export { BRIEF_CLIENT_DEFAULTS } from "./brief-client/types";
export type {
  BriefClientData,
  TypeEntreeFichier,
} from "./brief-client/types";

interface BriefClientFormProps {
  value: BriefClientData;
  onChange: (next: BriefClientData) => void;
}

export function BriefClientForm({ value, onChange }: BriefClientFormProps) {
  return (
    <div className="space-y-6">
      <SectionRouleauLivre value={value} onChange={onChange} />
      <SectionMatiereStockage value={value} onChange={onChange} />
      <SectionTypeEntreeFichier value={value} onChange={onChange} />
    </div>
  );
}
