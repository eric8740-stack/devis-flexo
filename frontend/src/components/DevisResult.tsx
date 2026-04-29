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
import type {
  CandidatCylindreOutput,
  DevisCalculResult,
  DevisOutput,
  PosteResult,
} from "@/lib/api";

interface DevisResultProps {
  data: DevisCalculResult;
}

const fmtEur = (s: string) =>
  new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(parseFloat(s));

const fmtPct = (s: string, decimals = 1) =>
  `${(parseFloat(s) * 100).toFixed(decimals)} %`;

const fmtDetailValue = (v: string | number | null): string => {
  // null autorisé depuis Lot 5c (ex. outil_decoupe_id non identifié).
  if (v === null) return "—";
  if (typeof v === "string") return v;
  if (Number.isInteger(v)) return String(v);
  // Montre jusqu'à 4 décimales utiles, supprime les 0 finals
  return v.toFixed(4).replace(/\.?0+$/, "");
};

const fmtMm = (s: string, decimals = 2) =>
  `${parseFloat(s).toFixed(decimals)} mm`;

// ---------------------------------------------------------------------------
// Sous-composants partagés (mode manuel + matching)
// ---------------------------------------------------------------------------

function PostesCard({
  postes,
  coutRevient,
}: {
  postes: PosteResult[];
  coutRevient: number;
}) {
  return (
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
            {postes.map((p) => {
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
          {postes.map((p) => (
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
  );
}

// ---------------------------------------------------------------------------
// Mode 'manuel' (Sprint 5/6 + Sprint 7 default)
// ---------------------------------------------------------------------------

function DevisResultManuel({ data }: { data: DevisOutput }) {
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
      <PostesCard postes={data.postes} coutRevient={coutRevient} />

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
            <div className="mt-2 text-sm text-muted-foreground">
              Prix au mille :{" "}
              <span className="font-mono text-xl font-semibold text-foreground">
                {fmtEur(data.prix_au_mille_eur)}
              </span>{" "}
              / 1000 étiq.
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

// ---------------------------------------------------------------------------
// Mode 'matching' (Sprint 7 — top 3 cylindres compatibles)
// ---------------------------------------------------------------------------

function CandidatCard({
  candidat,
  rang,
  isMeilleur,
}: {
  candidat: CandidatCylindreOutput;
  rang: number;
  isMeilleur: boolean;
}) {
  return (
    <Card className={isMeilleur ? "border-primary" : undefined}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span>
            Candidat #{rang} — Z={candidat.z}, {candidat.nb_etiq_par_tour} étiq/tour
          </span>
          {isMeilleur && (
            <span className="rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
              Meilleur prix au mille
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
          <div>
            <div className="text-xs text-muted-foreground">Circonférence</div>
            <div className="font-mono">{fmtMm(candidat.circonference_mm)}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Pas étiquette</div>
            <div className="font-mono">{fmtMm(candidat.pas_mm)}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Intervalle</div>
            <div className="font-mono">{fmtMm(candidat.intervalle_mm)}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Étiq. / m linéaire</div>
            <div className="font-mono">{candidat.nb_etiq_par_metre}</div>
          </div>
        </div>
        <div className="rounded-md bg-primary/5 p-3">
          <div className="text-xs text-muted-foreground">Prix au mille</div>
          <div className="font-mono text-2xl font-bold text-primary">
            {fmtEur(candidat.prix_au_mille_eur)}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            / 1000 étiq.
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function DevisResultMatching({
  data,
}: {
  data: { candidats: CandidatCylindreOutput[] };
}) {
  // HT identique entre candidats — postes/totaux portés par le 1er.
  const tete = data.candidats[0];
  const coutRevient = parseFloat(tete.cout_revient_eur);

  return (
    <div id="devis-result" className="grid gap-6">
      <PostesCard postes={tete.postes} coutRevient={coutRevient} />

      <Card>
        <CardHeader>
          <CardTitle>Récapitulatif (commun aux candidats)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-muted-foreground">Coût de revient</div>
              <div className="font-mono text-lg">
                {fmtEur(tete.cout_revient_eur)}
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">Marge appliquée</div>
              <div className="font-mono text-lg">
                {fmtPct(tete.pct_marge_appliquee, 2)}
              </div>
            </div>
          </div>
          <div className="rounded-md bg-primary/5 p-4">
            <div className="text-sm text-muted-foreground">Prix de vente HT</div>
            <div className="font-mono text-3xl font-bold text-primary">
              {fmtEur(tete.prix_vente_ht_eur)}
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              HT identique pour les {data.candidats.length} candidat(s) — les
              postes ne dépendent pas du choix de cylindre. Seul le prix au
              mille varie (ci-dessous).
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3">
        <h2 className="text-lg font-semibold">
          {data.candidats.length} cylindre(s) magnétique(s) compatible(s)
        </h2>
        <p className="text-sm text-muted-foreground">
          Triés par intervalle croissant = meilleur prix au mille en premier.
        </p>
        <div className="grid gap-4 lg:grid-cols-3">
          {data.candidats.map((c, idx) => (
            <CandidatCard
              key={`${c.z}-${c.nb_etiq_par_tour}`}
              candidat={c}
              rang={idx + 1}
              isMeilleur={idx === 0}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Composant racine — discrimine sur data.mode (Union TS narrowing)
// ---------------------------------------------------------------------------

export function DevisResult({ data }: DevisResultProps) {
  if (data.mode === "matching") {
    return <DevisResultMatching data={data} />;
  }
  return <DevisResultManuel data={data} />;
}
