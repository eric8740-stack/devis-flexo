"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { DevisOutput } from "@/lib/api";

interface DevisResultProps {
  data: DevisOutput;
}

const fmtEur = (s: string) =>
  new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(parseFloat(s));

const fmtPct = (s: string, decimals = 1) =>
  `${(parseFloat(s) * 100).toFixed(decimals)} %`;

const fmtDetailValue = (v: string | number): string => {
  if (typeof v === "string") return v;
  if (Number.isInteger(v)) return String(v);
  // Montre jusqu'à 4 décimales utiles, supprime les 0 finals
  return v.toFixed(4).replace(/\.?0+$/, "");
};

export function DevisResult({ data }: DevisResultProps) {
  const coutRevient = parseFloat(data.cout_revient_eur);
  const prixHt = parseFloat(data.prix_vente_ht_eur);

  // Reconstitue les ratios à partir des details exposés par les calculateurs.
  const p1 = data.postes.find((p) => p.poste_numero === 1);
  const p5 = data.postes.find((p) => p.poste_numero === 5);
  const mlTotal = p5?.details.ml_total ? Number(p5.details.ml_total) : 0;
  const laizeMm = p1?.details.laize_utile_mm
    ? Number(p1.details.laize_utile_mm)
    : 0;
  const surfaceImprimee = (laizeMm / 1000) * mlTotal;
  const eurParMl = mlTotal > 0 ? prixHt / mlTotal : 0;
  const eurParM2Imp = surfaceImprimee > 0 ? prixHt / surfaceImprimee : 0;

  return (
    <div id="devis-result" className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Détail des 7 postes</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>Libellé</TableHead>
                <TableHead className="text-right">Montant</TableHead>
                <TableHead className="text-right w-20">% revient</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.postes.map((p) => {
                const montant = parseFloat(p.montant_eur);
                const pct = coutRevient > 0 ? (montant / coutRevient) * 100 : 0;
                return (
                  <TableRow key={p.poste_numero}>
                    <TableCell className="font-medium">
                      P{p.poste_numero}
                    </TableCell>
                    <TableCell>{p.libelle}</TableCell>
                    <TableCell className="text-right font-mono">
                      {fmtEur(p.montant_eur)}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {pct.toFixed(1)} %
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          <div className="mt-6 grid gap-2">
            {data.postes.map((p) => (
              <details
                key={p.poste_numero}
                className="rounded-md border bg-muted/30 px-4 py-2 text-sm"
              >
                <summary className="cursor-pointer font-medium">
                  Audit P{p.poste_numero} — {p.libelle} (
                  {fmtEur(p.montant_eur)})
                </summary>
                <ul className="mt-2 grid gap-1 font-mono text-xs">
                  {Object.entries(p.details).map(([k, v]) => (
                    <li key={k}>
                      <span className="text-muted-foreground">{k}</span> ={" "}
                      <span>{fmtDetailValue(v)}</span>
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Récapitulatif</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-muted-foreground">Coût de revient</div>
              <div className="font-mono text-lg">
                {fmtEur(data.cout_revient_eur)}
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">Marge appliquée</div>
              <div className="font-mono text-lg">
                {fmtPct(data.pct_marge_appliquee, 2)}
              </div>
            </div>
          </div>
          <div className="rounded-md bg-primary/5 p-4">
            <div className="text-sm text-muted-foreground">Prix de vente HT</div>
            <div className="font-mono text-3xl font-bold text-primary">
              {fmtEur(data.prix_vente_ht_eur)}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
            <div>
              <span>€ / mètre linéaire :</span>{" "}
              <span className="font-mono text-foreground">
                {eurParMl.toFixed(4)}
              </span>
            </div>
            <div>
              <span>€ / m² imprimé :</span>{" "}
              <span className="font-mono text-foreground">
                {eurParM2Imp.toFixed(4)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
