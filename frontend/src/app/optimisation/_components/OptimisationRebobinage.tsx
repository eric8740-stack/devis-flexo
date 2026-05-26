"use client";

/**
 * Sprint 16 Lot D — Étape Rebobinage.
 *
 * Insérée APRÈS l'optimisation de pose (étape "detail") et AVANT le
 * chiffrage final. Trois rôles :
 *
 *   1. Saisir / ajuster les paramètres bobine du client (diamètre
 *      mandrin, diamètre max bobine, sens d'enroulement, nb étiq/bobine,
 *      marquage, film protection, conditionnement). Champs pré-remplis
 *      depuis le brief client + saisie initiale (mandrin, sens).
 *
 *   2. Afficher le calcul auto (nb bobines, temps estimé, coût) et
 *      l'arbitrage pré-coupé vs découpe interne (mode optimal +
 *      alternatif + écart % + délais).
 *
 *   3. Souveraineté commerciale : le commercial peut FORCER un mode
 *      (pré-coupé ou découpe interne) ; un motif est OBLIGATOIRE
 *      (10 caractères mini) pour traçabilité.
 *
 * Mobile-first : grilles 1 col par défaut → 2 col en sm+. Pas de
 * tooltip au survol — toute info utile en texte visible.
 *
 * ⚠️ Lot C backend (calculs + arbitrage côté serveur) pas encore
 * disponible : les sections "Calcul" et "Arbitrage" affichent un
 * payload MOCK, clairement étiqueté, à remplacer au câblage Lot C.
 */
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

import { useOptimisationPose } from "./OptimisationPoseStore";

export type ModeRebobinage = "pre_coupe" | "decoupe_interne";

const MODE_LABEL: Record<ModeRebobinage, string> = {
  pre_coupe: "Pré-coupé",
  decoupe_interne: "Découpe interne",
};

const MODE_DESCRIPTION: Record<ModeRebobinage, string> = {
  pre_coupe:
    "Mandrins reçus déjà coupés à la longueur. Pas d'usinage interne, mise en route rapide.",
  decoupe_interne:
    "Mandrins découpés en interne avant rebobinage. Cycle plus long mais flexible sur les longueurs.",
};

const SENS_OPTIONS = ["SE1", "SE2", "SE3", "SE4", "SE5", "SE6", "SE7", "SE8"] as const;

// Diamètres mandrin courants flexo (alignés sur la saisie étape 1).
const DIAMETRES_MANDRIN_MM = [25, 38, 40, 50, 76] as const;

// Conditionnements typiques (à confirmer avec Lot C — choix par défaut MVP).
const CONDITIONNEMENT_OPTIONS = [
  { value: "bobine_standard", label: "Bobine standard (carton)" },
  { value: "carton_protect", label: "Carton renforcé (export)" },
  { value: "palette_filmee", label: "Palette filmée" },
  { value: "caisse_bois", label: "Caisse bois (fragile)" },
] as const;

const MOTIF_MIN_LENGTH = 10;

export function OptimisationRebobinage() {
  const {
    briefClient,
    mandrinMm,
    sommeQuantitesLots,
    quantiteTotale,
    goDetail,
    goChiffrage,
  } = useOptimisationPose();

  // ──────────────────────────────────────────────────────────────────
  // Pré-remplissage depuis le store (brief client + saisie initiale).
  // L'opérateur peut tout ajuster avant validation.
  // ──────────────────────────────────────────────────────────────────
  const [diametreMandrin, setDiametreMandrin] = useState<number>(mandrinMm);
  const [diametreMaxBobine, setDiametreMaxBobine] = useState<string>(
    briefClient.diametre_max_bobine_mm !== null
      ? String(briefClient.diametre_max_bobine_mm)
      : ""
  );
  const [sensEnroulement, setSensEnroulement] = useState<string>("SE1");
  const [nbEtiqParBobine, setNbEtiqParBobine] = useState<string>(
    briefClient.nb_etiquettes_par_rouleau !== null
      ? String(briefClient.nb_etiquettes_par_rouleau)
      : ""
  );
  const [marquage, setMarquage] = useState<boolean>(false);
  const [filmProtection, setFilmProtection] = useState<boolean>(false);
  const [conditionnement, setConditionnement] = useState<string>(
    "bobine_standard"
  );

  // ──────────────────────────────────────────────────────────────────
  // Forçage commercial : choix du mode + motif obligatoire si forcé.
  // ──────────────────────────────────────────────────────────────────
  const [forcerMode, setForcerMode] = useState<boolean>(false);
  const [modeForce, setModeForce] = useState<ModeRebobinage>("pre_coupe");
  const [motifForce, setMotifForce] = useState<string>("");
  const [motifErreur, setMotifErreur] = useState<string | null>(null);

  // ──────────────────────────────────────────────────────────────────
  // MOCK Lot D — calcul + arbitrage. Branchement Lot C backend à venir.
  // On dérive un mock plausible de la quantité totale + nb étiq/bobine
  // pour que les valeurs affichées soient cohérentes avec la saisie.
  // ──────────────────────────────────────────────────────────────────
  const qteEffective = sommeQuantitesLots || quantiteTotale || 0;
  const parsedNbEtiqBobine = parseInt(nbEtiqParBobine, 10);
  const nbEtiqBobineValide =
    Number.isFinite(parsedNbEtiqBobine) && parsedNbEtiqBobine > 0
      ? parsedNbEtiqBobine
      : 1000;
  const calculMock = useMemo(() => {
    const nbBobines = Math.max(1, Math.ceil(qteEffective / nbEtiqBobineValide));
    return {
      nb_bobines: nbBobines,
      // ~2 min par bobine en pré-coupé (mock).
      temps_estime_h: Math.round((nbBobines * 2) / 60 * 100) / 100,
      // ~0.45 € par bobine en pré-coupé (mock).
      cout_eur: Math.round(nbBobines * 0.45 * 100) / 100,
    };
  }, [qteEffective, nbEtiqBobineValide]);

  const arbitrageMock = useMemo(() => {
    // Pré-coupé légèrement plus cher mais plus rapide ; découpe interne
    // moins cher mais délai plus long. Écart % calculé sur le coût.
    const coutPreCoupe = calculMock.cout_eur;
    const coutDecoupeInterne = Math.round(coutPreCoupe * 0.72 * 100) / 100;
    const ecart =
      coutDecoupeInterne > 0
        ? Math.round(((coutPreCoupe - coutDecoupeInterne) / coutDecoupeInterne) * 100)
        : 0;
    return {
      mode_optimal: "decoupe_interne" as ModeRebobinage,
      mode_alternatif: "pre_coupe" as ModeRebobinage,
      ecart_pct: ecart,
      delais_optimal_jours: 5,
      delais_alternatif_jours: 2,
      cout_optimal_eur: coutDecoupeInterne,
      cout_alternatif_eur: coutPreCoupe,
    };
  }, [calculMock.cout_eur]);

  const modeRetenuFinal: ModeRebobinage = forcerMode
    ? modeForce
    : arbitrageMock.mode_optimal;

  // ──────────────────────────────────────────────────────────────────
  // Validation & navigation
  // ──────────────────────────────────────────────────────────────────
  const validerEtContinuer = () => {
    if (forcerMode) {
      const motifTrim = motifForce.trim();
      if (motifTrim.length < MOTIF_MIN_LENGTH) {
        setMotifErreur(
          `Motif obligatoire (${MOTIF_MIN_LENGTH} caractères minimum) pour tracer le forçage commercial.`
        );
        return;
      }
    }
    setMotifErreur(null);
    // TODO Lot C : avant goChiffrage, persister params + mode retenu
    // dans le store pour que l'étape chiffrage récupère le coût rebobinage.
    goChiffrage();
  };

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header>
        <h1 className="text-2xl font-bold">Rebobinage</h1>
        <p className="text-sm text-muted-foreground sm:text-base">
          Paramètres bobines client, calcul auto et arbitrage pré-coupé /
          découpe interne. Le commercial peut forcer un mode avec motif
          obligatoire.
        </p>
      </header>

      <div
        role="note"
        className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
      >
        <strong>Données calcul + arbitrage en mock</strong> tant que le Lot C
        backend (moteur rebobinage + endpoint arbitrage) n&apos;est pas
        câblé. Les paramètres saisis ci-dessous sont déjà persistables ;
        seuls les chiffres « Calcul » et « Arbitrage » seront remplacés.
      </div>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Section paramètres bobine client (pré-remplie)              */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Paramètres bobines client</CardTitle>
          <CardDescription>
            Pré-remplis depuis le brief client. Ajustez si le commercial a
            validé d&apos;autres valeurs avec ce client.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="rebob-mandrin">Ø Mandrin bobine (mm)</Label>
              <select
                id="rebob-mandrin"
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={diametreMandrin}
                onChange={(e) => setDiametreMandrin(Number(e.target.value))}
              >
                {DIAMETRES_MANDRIN_MM.map((d) => (
                  <option key={d} value={d}>
                    {d} mm
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                Pré-rempli depuis la saisie étape 1. Standard flexo : 40 ou
                76 mm.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rebob-diam-max">
                Ø Max bobine livrée (mm)
              </Label>
              <Input
                id="rebob-diam-max"
                type="number"
                min={50}
                max={600}
                step={1}
                value={diametreMaxBobine}
                onChange={(e) => setDiametreMaxBobine(e.target.value)}
                placeholder="ex: 300"
              />
              <p className="text-xs text-muted-foreground">
                Pré-rempli depuis le brief client (peut être laissé vide si
                contrainte non spécifiée).
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rebob-sens">Sens d&apos;enroulement</Label>
              <select
                id="rebob-sens"
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={sensEnroulement}
                onChange={(e) => setSensEnroulement(e.target.value)}
              >
                {SENS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                SE1-4 face extérieur, SE5-8 face intérieur (convention
                métier flexo).
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rebob-nb-etiq">Nb étiquettes / bobine</Label>
              <Input
                id="rebob-nb-etiq"
                type="number"
                min={1}
                step={1}
                value={nbEtiqParBobine}
                onChange={(e) => setNbEtiqParBobine(e.target.value)}
                placeholder="ex: 1000"
              />
              <p className="text-xs text-muted-foreground">
                Pré-rempli depuis le brief client. Pilote le nombre de
                bobines à produire.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <label className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-3 text-sm">
              <input
                type="checkbox"
                checked={marquage}
                onChange={(e) => setMarquage(e.target.checked)}
                className="mt-0.5 h-4 w-4 cursor-pointer accent-foreground"
              />
              <div>
                <div className="font-medium">Marquage bobine</div>
                <div className="text-xs text-muted-foreground">
                  Étiquette d&apos;identification collée sur chaque bobine.
                </div>
              </div>
            </label>
            <label className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-3 text-sm">
              <input
                type="checkbox"
                checked={filmProtection}
                onChange={(e) => setFilmProtection(e.target.checked)}
                className="mt-0.5 h-4 w-4 cursor-pointer accent-foreground"
              />
              <div>
                <div className="font-medium">Film protection</div>
                <div className="text-xs text-muted-foreground">
                  Film polyéthylène autour de chaque bobine (transport
                  longue distance).
                </div>
              </div>
            </label>
            <div className="space-y-2">
              <Label htmlFor="rebob-conditionnement">Conditionnement</Label>
              <select
                id="rebob-conditionnement"
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={conditionnement}
                onChange={(e) => setConditionnement(e.target.value)}
              >
                {CONDITIONNEMENT_OPTIONS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Section calcul auto (MOCK Lot D)                            */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Calcul rebobinage</CardTitle>
          <CardDescription>
            Sur la base de {qteEffective.toLocaleString("fr-FR")} étiquettes
            à produire / {nbEtiqBobineValide.toLocaleString("fr-FR")} par
            bobine.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <KPI
              label="Nombre de bobines"
              value={calculMock.nb_bobines.toLocaleString("fr-FR")}
              testId="calcul-nb-bobines"
            />
            <KPI
              label="Temps estimé"
              value={`${calculMock.temps_estime_h.toLocaleString("fr-FR")} h`}
              testId="calcul-temps"
            />
            <KPI
              label="Coût"
              value={`${calculMock.cout_eur.toLocaleString("fr-FR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })} €`}
              testId="calcul-cout"
            />
          </dl>
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Section arbitrage pré-coupé vs découpe interne (MOCK Lot D) */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Arbitrage pré-coupé / découpe interne</CardTitle>
          <CardDescription>
            Le moteur compare les deux modes sur coût + délai. Le mode
            optimal est mis en avant ; le mode alternatif reste visible
            pour décision commerciale.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <ModeArbitrageCard
            mode={arbitrageMock.mode_optimal}
            recommande
            coutEur={arbitrageMock.cout_optimal_eur}
            delaisJours={arbitrageMock.delais_optimal_jours}
            testId="arbitrage-optimal"
          />
          <ModeArbitrageCard
            mode={arbitrageMock.mode_alternatif}
            recommande={false}
            coutEur={arbitrageMock.cout_alternatif_eur}
            delaisJours={arbitrageMock.delais_alternatif_jours}
            ecartPct={arbitrageMock.ecart_pct}
            testId="arbitrage-alternatif"
          />
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Souveraineté commerciale : forçage + motif obligatoire      */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card data-testid="forcage-section">
        <CardHeader>
          <CardTitle>Souveraineté commerciale</CardTitle>
          <CardDescription>
            Le commercial peut écraser la recommandation moteur. Le mode
            forcé et le motif sont tracés.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={forcerMode}
              onChange={(e) => {
                setForcerMode(e.target.checked);
                if (!e.target.checked) {
                  setMotifErreur(null);
                }
              }}
              className="h-4 w-4 cursor-pointer accent-foreground"
              data-testid="forcer-mode-checkbox"
            />
            Forcer un mode (écrase la recommandation moteur)
          </label>
          {forcerMode && (
            <div className="space-y-3 rounded-md border border-amber-300 bg-amber-50 p-4">
              <div className="space-y-2">
                <Label htmlFor="rebob-mode-force">Mode forcé</Label>
                <select
                  id="rebob-mode-force"
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={modeForce}
                  onChange={(e) =>
                    setModeForce(e.target.value as ModeRebobinage)
                  }
                >
                  <option value="pre_coupe">{MODE_LABEL.pre_coupe}</option>
                  <option value="decoupe_interne">
                    {MODE_LABEL.decoupe_interne}
                  </option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="rebob-motif-force">
                  Motif du forçage (obligatoire,{" "}
                  {MOTIF_MIN_LENGTH} caractères minimum)
                </Label>
                <textarea
                  id="rebob-motif-force"
                  data-testid="motif-force-textarea"
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  rows={3}
                  value={motifForce}
                  onChange={(e) => {
                    setMotifForce(e.target.value);
                    if (motifErreur) setMotifErreur(null);
                  }}
                  placeholder="Contrainte client, urgence, capacité atelier saturée…"
                />
                <p className="text-xs text-muted-foreground">
                  Le motif est consigné avec l&apos;identité du commercial
                  pour traçabilité.
                </p>
              </div>
              {motifErreur && (
                <div
                  role="alert"
                  data-testid="motif-erreur"
                  className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
                >
                  {motifErreur}
                </div>
              )}
            </div>
          )}

          <div className="rounded-md border border-border bg-muted/30 p-3 text-sm">
            <strong>Mode retenu :</strong>{" "}
            <span data-testid="mode-retenu">{MODE_LABEL[modeRetenuFinal]}</span>{" "}
            {forcerMode ? (
              <span className="text-amber-800">(forcé commercial)</span>
            ) : (
              <span className="text-muted-foreground">
                (recommandation moteur)
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Navigation                                                  */}
      {/* ────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <Button variant="outline" size="sm" onClick={goDetail}>
          ← Retour détail lots
        </Button>
        <Button
          size="lg"
          onClick={validerEtContinuer}
          data-testid="rebobinage-continuer"
          className="bg-gradient-to-r from-blue-700 to-amber-600 px-8 py-6 text-base font-semibold text-white shadow-md transition-all hover:from-blue-800 hover:to-amber-700 hover:shadow-lg"
        >
          Continuer vers chiffrage →
        </Button>
      </div>
    </main>
  );
}

// ──────────────────────────────────────────────────────────────────
// Sous-composants
// ──────────────────────────────────────────────────────────────────

function KPI({
  label,
  value,
  testId,
}: {
  label: string;
  value: string;
  testId?: string;
}) {
  return (
    <div className="rounded-md border border-border bg-muted/20 p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div
        data-testid={testId}
        className="mt-1 font-mono text-2xl font-semibold text-foreground"
      >
        {value}
      </div>
    </div>
  );
}

function ModeArbitrageCard({
  mode,
  recommande,
  coutEur,
  delaisJours,
  ecartPct,
  testId,
}: {
  mode: ModeRebobinage;
  recommande: boolean;
  coutEur: number;
  delaisJours: number;
  ecartPct?: number;
  testId?: string;
}) {
  return (
    <div
      data-testid={testId}
      className={cn(
        "rounded-md border-2 p-4",
        recommande
          ? "border-emerald-400 bg-emerald-50"
          : "border-border bg-background"
      )}
    >
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-base font-semibold">{MODE_LABEL[mode]}</div>
        {recommande ? (
          <span className="rounded bg-emerald-600 px-2 py-0.5 text-xs font-semibold text-white">
            Recommandé
          </span>
        ) : (
          <span className="rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700">
            Alternatif
          </span>
        )}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {MODE_DESCRIPTION[mode]}
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">
            Coût
          </dt>
          <dd className="font-mono font-semibold">
            {coutEur.toLocaleString("fr-FR", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}{" "}
            €
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">
            Délai
          </dt>
          <dd className="font-mono font-semibold">{delaisJours} j</dd>
        </div>
      </dl>
      {ecartPct !== undefined && ecartPct !== 0 && (
        <div className="mt-2 text-xs text-amber-800">
          Écart vs optimal :{" "}
          <strong>
            {ecartPct > 0 ? "+" : ""}
            {ecartPct} %
          </strong>
        </div>
      )}
    </div>
  );
}
