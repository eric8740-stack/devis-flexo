"use client";

import { useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

import { ChangementsSection } from "./_components/ChangementsSection";
import { ChargesSection } from "./_components/ChargesSection";
import {
  CalageCoutsSection,
  FinitionsCoutsSection,
  MargeRoulageSection,
  OutilsCoutsSection,
} from "./_components/ConfigCoutsChamps";
import { CoutsSection } from "./_components/CoutsSection";
import {
  ComplexesSection,
  EncreSection,
  MachinesSection,
} from "./_components/ReadonlySections";
import { RoulageSection } from "./_components/RoulageSection";

// Onglet Stratégique (Brief stratégique v2) — config par entreprise.
// Machines/Complexes/Encre : tables existantes, lecture seule + lien de
//   gestion (anti-doublon).
// Outils/Calage/Finitions : coûts ConfigCouts migrés depuis TarifPoste
//   (Lot 4a) → édition directe (Lot 4b).
// Roulage, Coûts/Marges, Changements : config Phase 1 → CRUD.
// Charges : CRUD inline des frais fixes mensuels (la page
//   /charges-mensuelles standalone reste disponible).
const SECTIONS: {
  id: string;
  label: string;
  title: string;
  description: string;
  node: React.ReactNode;
}[] = [
  {
    id: "machines",
    label: "Machines",
    title: "Machines",
    description: "Parc presse — lecture seule, édition sur la page Machines.",
    node: <MachinesSection />,
  },
  {
    id: "complexes",
    label: "Complexes & Matières",
    title: "Complexes & Matières",
    description: "Supports — lecture seule, édition sur la page Complexes.",
    node: <ComplexesSection />,
  },
  {
    id: "encre",
    label: "Encre",
    title: "Encre",
    description: "Tarifs encre par type (prix/kg, consommation g/m²/couleur).",
    node: <EncreSection />,
  },
  {
    id: "outils",
    label: "Outils",
    title: "Outils (clichés & découpe)",
    description:
      "Coûts clichés et outils de découpe utilisés par le chiffrage (config tenant, éditable).",
    node: <OutilsCoutsSection />,
  },
  {
    id: "calage",
    label: "Calage",
    title: "Calage",
    description: "Forfait de calage appliqué au chiffrage (config tenant).",
    node: <CalageCoutsSection />,
  },
  {
    id: "finitions",
    label: "Finitions",
    title: "Finitions",
    description: "Prix des finitions au m² appliqué au chiffrage (config tenant).",
    node: <FinitionsCoutsSection />,
  },
  {
    id: "roulage",
    label: "Roulage & Production",
    title: "Roulage & Production",
    description: "Débits et mode de roulage par format (configurable).",
    node: (
      <div className="space-y-8">
        <RoulageSection />
        <div>
          <h3 className="mb-3 text-sm font-semibold">Marge de confort</h3>
          <MargeRoulageSection />
        </div>
      </div>
    ),
  },
  {
    id: "couts",
    label: "Coûts & Marges",
    title: "Coûts & Marges",
    description:
      "Coûts variables/fixes, marges et changements (source : config tenant).",
    node: (
      <div className="space-y-8">
        <CoutsSection />
        <div>
          <h3 className="mb-3 text-sm font-semibold">Changements</h3>
          <ChangementsSection />
        </div>
      </div>
    ),
  },
  {
    id: "charges",
    label: "Charges",
    title: "Charges",
    description:
      "Frais fixes mensuels (loyer, salaires, énergie, …). La page /charges-mensuelles standalone reste accessible.",
    node: <ChargesSection />,
  },
];

export default function StrategiquePage() {
  const [active, setActive] = useState(SECTIONS[0].id);
  const section = SECTIONS.find((s) => s.id === active) ?? SECTIONS[0];

  return (
    <main className="container mx-auto max-w-5xl p-4 sm:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Stratégique</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Données techniques et tarifaires de votre entreprise. Chaque
          paramètre alimente le chiffrage — ajustez-les à votre réalité.
        </p>
      </header>

      <nav className="mb-6 flex flex-wrap gap-2" aria-label="Sections stratégiques">
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setActive(s.id)}
            aria-current={s.id === active ? "page" : undefined}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm transition-colors",
              s.id === active
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            {s.label}
          </button>
        ))}
      </nav>

      <Card>
        <CardHeader>
          <CardTitle>{section.title}</CardTitle>
          <CardDescription>{section.description}</CardDescription>
        </CardHeader>
        <CardContent>{section.node}</CardContent>
      </Card>
    </main>
  );
}
