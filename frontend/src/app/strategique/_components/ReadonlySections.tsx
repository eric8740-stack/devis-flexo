"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  type Complexe,
  type Machine,
  type TarifEncre,
  listComplexes,
  listMachines,
  listTarifEncre,
} from "@/lib/api";

// Sections Machines/Complexes/Encre — tables EXISTANTES. Affichage lecture
// seule + lien vers la page de gestion dédiée (anti-doublon : on ne
// ré-implémente pas le CRUD déjà présent ailleurs, cf. audit).
// NB Lot 4b : l'ancienne OutilsSection readonly (TarifPoste via
// getTarifsGrouped) a été supprimée — le moteur lit désormais ConfigCouts
// (Lot 4a), l'édition se fait dans ConfigCoutsChamps.tsx.

function GererLink({ href, children }: { href: string; children: string }) {
  return (
    <Link href={href} className="text-sm font-medium text-primary hover:underline">
      {children} →
    </Link>
  );
}

function fmt(v: number | string | null): string {
  if (v === null || v === undefined) return "—";
  return String(v);
}

// --- Section 1 : Machines ---------------------------------------------------
export function MachinesSection() {
  const [rows, setRows] = useState<Machine[] | null>(null);
  useEffect(() => {
    listMachines().then(setRows).catch(() => setRows([]));
  }, []);
  return (
    <div className="space-y-3">
      <GererLink href="/machines">Gérer les machines</GererLink>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Référence</TableHead>
            <TableHead>Vitesse réelle (m/min)</TableHead>
            <TableHead>Coût exploitation (€/h)</TableHead>
            <TableHead>Durée calage (h)</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {(rows ?? []).map((m) => (
            <TableRow key={m.id}>
              <TableCell>{m.nom}</TableCell>
              {/* B2 : aligné sur /machines — `vitesse_moyenne_m_h ÷ 60`
                  (et non plus `vitesse_max_m_min` qui n'alimente aucun
                  chiffrage). Les 2 pages affichent la même valeur. */}
              <TableCell>
                {m.vitesse_moyenne_m_h != null
                  ? Math.round(m.vitesse_moyenne_m_h / 60)
                  : "—"}
              </TableCell>
              <TableCell>{fmt(m.cout_horaire_eur)}</TableCell>
              <TableCell>{fmt(m.duree_calage_h)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// --- Section 2 : Complexes & Matières ---------------------------------------
export function ComplexesSection() {
  const [rows, setRows] = useState<Complexe[] | null>(null);
  useEffect(() => {
    listComplexes().then(setRows).catch(() => setRows([]));
  }, []);
  return (
    <div className="space-y-3">
      <GererLink href="/complexes">Gérer les complexes</GererLink>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Référence</TableHead>
            <TableHead>Famille</TableHead>
            <TableHead>Grammage (g/m²)</TableHead>
            <TableHead>Prix matière (€/m²)</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {(rows ?? []).map((c) => (
            <TableRow key={c.id}>
              <TableCell>{c.reference}</TableCell>
              <TableCell>{c.famille}</TableCell>
              <TableCell>{fmt(c.grammage_g_m2)}</TableCell>
              <TableCell>{fmt(c.prix_m2_eur)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// --- Section 3 : Encre (lecture seule, pas d'édition MVP) -------------------
export function EncreSection() {
  const [rows, setRows] = useState<TarifEncre[] | null>(null);
  useEffect(() => {
    listTarifEncre().then(setRows).catch(() => setRows([]));
  }, []);
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Lecture seule (édition prévue en Phase 2).
      </p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Type encre</TableHead>
            <TableHead>Coût (€/kg)</TableHead>
            <TableHead>Conso. (g/m²/couleur)</TableHead>
            <TableHead>Prix min</TableHead>
            <TableHead>Prix max</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {(rows ?? []).map((t) => (
            <TableRow key={t.id}>
              <TableCell>{t.libelle || t.type_encre}</TableCell>
              <TableCell>{fmt(t.prix_kg_defaut)}</TableCell>
              <TableCell>{fmt(t.ratio_g_m2_couleur)}</TableCell>
              <TableCell>{fmt(t.prix_kg_min)}</TableCell>
              <TableCell>{fmt(t.prix_kg_max)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
