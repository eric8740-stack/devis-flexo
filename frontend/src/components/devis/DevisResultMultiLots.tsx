"use client";

/**
 * Affichage d'un devis multi-lots — Brief #32 commit 3.
 *
 * Design joyeux §9bis :
 *   - Header devis : gradient subtle + numéro Fraunces + badge statut coloré.
 *   - Cards par lot : border-left 4px varié par index (bleu / or / vert /
 *     ambré, cycle). Hover lift + shadow douce.
 *   - Coût lot HT : typo bold gros, couleur accent bleu, séparateur orné.
 *   - Récap total HT : card hero gradient bleu→or, font Fraunces XL.
 *   - Bouton "Modifie ce devis" primary rempli gradient bleu→or.
 *   - Boutons "Imprime" / "Duplique" secondary outlined coloré.
 *   - Microcopie tutoyée systématique.
 *
 * Hors scope MVP : intégration du visuel SchemaImplantation par lot
 * (composant SACRED réutilisé tel quel) — nécessite un mapping
 * LotProductionRead → props OptimisationConfigOut qui dépasse ce brief.
 * Placeholder visuel à la place avec les rotations déjà calculées
 * backend (rotation_vue_a_deg / rotation_vue_c_deg).
 */
import Link from "next/link";

import { PostesCard } from "@/components/DevisResult";
import { SchemaImplantation } from "@/components/SchemaImplantation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type {
  DevisDetail,
  LotProductionRead,
  OptimisationConfigOut,
  PosteResult,
} from "@/lib/api";

const STATUT_COLORS: Record<string, string> = {
  brouillon: "bg-amber-100 text-amber-900 border-amber-300",
  valide: "bg-emerald-100 text-emerald-900 border-emerald-300",
};

const STATUT_LABEL: Record<string, string> = {
  brouillon: "Brouillon",
  valide: "Validé",
};

// Cycle de couleurs pour les border-left des cards lot (§9bis).
const LOT_BORDER_COLORS = [
  "border-l-blue-700",
  "border-l-amber-600",
  "border-l-emerald-600",
  "border-l-purple-600",
];

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

const fmtEuros = (montant: string | number | null | undefined): string => {
  if (montant === null || montant === undefined) return "—";
  const n = typeof montant === "string" ? parseFloat(montant) : montant;
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

// Brief rapport de fabrication — décomposition 7 postes + chiffrage par lot
// extraits du dump cost_engine. Le backend stocke `payload_output.details_par_lot[i]`
// = { ordre, prix_vente_ht_eur, cout_revient_eur, details: {DevisOutput} }
// (cf. _chiffrer_devis_multilots). DevisOutput.details_par_lot[i].details
// contient au top : prix_vente_ht_eur, cout_revient_eur, pct_marge_appliquee,
// prix_au_mille_eur, postes[7]. Les ratios €/ml et €/m² sont calculés côté UI
// depuis postes[P5].details.ml_total et postes[P1].details.surface_support_m2.
export interface LotChiffrage {
  postes: PosteResult[];
  coutRevient: number;
  prixVenteHt: number;
  pctMarge: number; // 0..1 (0.18 = 18 %)
  prixAuMille: number;
  mlTotal: number | null;
  surfaceM2: number | null;
}

function toNum(v: unknown): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
}

function toNumOrNull(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string") {
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

/**
 * Retourne le chiffrage par lot dans l'ORDRE de `payload_output.details_par_lot`,
 * sous forme de tableau positional. Les entrées sans `postes` valides sont
 * remplacées par `null` (rapport masqué pour ce lot uniquement).
 *
 * Pourquoi pas un Map<ordre, …> ? Conventions d'indexation divergentes —
 * `LotProduction.ordre` est 1-indexé côté DB (create_devis `enumerate(start=1)`)
 * mais `CoutLot.ordre` est 0-indexé côté agrégateur cost_engine. Un lookup
 * `Map.get(lot.ordre)` ratait systématiquement. Les deux côtés étant construits
 * dans le même ordre depuis `data.lots`, l'alignement positional est robuste
 * (et neutre vis-à-vis d'une future renumérotation des ordres).
 */
export function extractLotChiffrageParLot(
  payloadOutput: Record<string, unknown>,
): (LotChiffrage | null)[] {
  const raw = payloadOutput.details_par_lot;
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    if (!entry || typeof entry !== "object") return null;
    const e = entry as {
      cout_revient_eur?: unknown;
      prix_vente_ht_eur?: unknown;
      details?: Record<string, unknown>;
    };
    const postes = e.details?.postes;
    if (!Array.isArray(postes) || postes.length === 0) return null;
    const postesTyped = postes as PosteResult[];
    const p1 = postesTyped.find((p) => p.poste_numero === 1);
    const p5 = postesTyped.find((p) => p.poste_numero === 5);
    return {
      postes: postesTyped,
      coutRevient: toNum(e.cout_revient_eur ?? e.details?.cout_revient_eur),
      prixVenteHt: toNum(e.prix_vente_ht_eur ?? e.details?.prix_vente_ht_eur),
      pctMarge: toNum(e.details?.pct_marge_appliquee),
      prixAuMille: toNum(e.details?.prix_au_mille_eur),
      mlTotal: toNumOrNull(p5?.details?.ml_total),
      surfaceM2: toNumOrNull(p1?.details?.surface_support_m2),
    } satisfies LotChiffrage;
  });
}

export function DevisResultMultiLots({
  devis,
  pdfUrl,
  onDupliquer,
  onSupprimer,
}: {
  devis: DevisDetail;
  pdfUrl: string;
  onDupliquer: () => void;
  onSupprimer: () => void;
}) {
  const lots = devis.lots_production ?? [];
  const reductionPct = parseFloat(devis.reduction_pct ?? "0") || 0;
  // Fix bandeau erreur chiffrage — `ht_total_eur` NULL signale un chiffrage
  // auto incomplet (cf. fix backend CC1). On NE calcule PAS de prix dans ce
  // cas : surtout pas de `parseFloat(null) || 0` qui afficherait un « 0,00 € »
  // trompeur. Le message vient du top-level `chiffrage_auto_erreur`, avec
  // repli sur `payload_output.chiffrage_auto_erreur` (devis créés avant que
  // le backend ne remonte le champ top-level).
  const payloadOutput = (devis.payload_output ?? {}) as Record<string, unknown>;
  const chiffrageErreur =
    devis.ht_total_eur === null || devis.ht_total_eur === undefined
      ? devis.chiffrage_auto_erreur ??
        (typeof payloadOutput.chiffrage_auto_erreur === "string"
          ? payloadOutput.chiffrage_auto_erreur
          : null) ??
        "Le chiffrage automatique n'a pas abouti — aucun prix disponible."
      : null;
  const brut = chiffrageErreur === null ? parseFloat(devis.ht_total_eur!) || 0 : 0;
  const apresRemise = brut * (1 - reductionPct / 100);
  // Brief #33 commit 5 — laize/dev/mandrin de l'étiquette pour le
  // SchemaImplantation par lot. Récupérés depuis payload_input (snapshoté
  // à la création par OptimisationPoseDetailLots / OptimisationChiffrage).
  const payloadInput = (devis.payload_input ?? {}) as Record<string, unknown>;
  const laizeEtiqMm =
    typeof payloadInput.format_etiquette_largeur_mm === "number"
      ? payloadInput.format_etiquette_largeur_mm
      : parseFloat(devis.format_l_mm) || 0;
  const devEtiqMm =
    typeof payloadInput.format_etiquette_hauteur_mm === "number"
      ? payloadInput.format_etiquette_hauteur_mm
      : parseFloat(devis.format_h_mm) || 0;
  const mandrinMm =
    typeof payloadInput.mandrin_mm === "number" ? payloadInput.mandrin_mm : 76;
  const chiffrageParLot = extractLotChiffrageParLot(payloadOutput);
  // Backend et frontend itèrent `data.lots` dans le même ordre — l'alignement
  // positional (idx) est robuste, contrairement à un lookup par `ordre`
  // (off-by-one entre LotProduction 1-indexé et CoutLot 0-indexé).

  return (
    <div className="space-y-6">
      {/* Header devis — gradient subtle + badge statut coloré */}
      <header className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50/60 via-amber-50/30 to-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-baseline gap-3">
              <h1
                className="bg-gradient-to-r from-blue-800 to-amber-700 bg-clip-text font-mono text-3xl font-bold text-transparent"
                style={{ fontFamily: "Fraunces, serif" }}
              >
                {devis.numero}
              </h1>
              <span
                className={
                  "rounded-full border px-3 py-0.5 text-xs font-medium " +
                  (STATUT_COLORS[devis.statut] ?? "bg-gray-100 text-gray-900")
                }
              >
                {STATUT_LABEL[devis.statut] ?? devis.statut}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Créé le {fmtDate(devis.date_creation)} · Machine{" "}
              {devis.machine_nom}
              {devis.client_nom && (
                <>
                  {" · "}Client <strong>{devis.client_nom}</strong>
                </>
              )}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" size="sm">
              <Link href="/devis">↩ Liste</Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <a href={pdfUrl} download={`${devis.numero}.pdf`}>
                🖨️ Imprime
              </a>
            </Button>
            <Button variant="outline" size="sm" onClick={onDupliquer}>
              📑 Duplique
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onSupprimer}
              className="text-red-700 hover:bg-red-50 hover:text-red-800"
            >
              🗑 Supprime
            </Button>
          </div>
        </div>
      </header>

      {/* Cards par lot — border-left coloré varié */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Tes lots de production · {lots.length} lot{lots.length > 1 ? "s" : ""}
        </h2>
        {lots.map((lot, idx) => (
          <LotCard
            key={lot.id}
            lot={lot}
            colorClass={LOT_BORDER_COLORS[idx % LOT_BORDER_COLORS.length]!}
            laizeEtiqMm={laizeEtiqMm}
            devEtiqMm={devEtiqMm}
            mandrinMm={mandrinMm}
            chiffrage={chiffrageParLot[idx] ?? null}
          />
        ))}
        {lots.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Ce devis n&apos;a pas encore de lot enregistré.
          </p>
        )}
      </section>

      {/* Récap total HT — card hero gradient bleu→or (§9bis).
          Fix bandeau erreur : si le chiffrage est incomplet, on remplace le
          prix par un bandeau d'erreur visible (jamais de « 0,00 € » trompeur). */}
      <section className="rounded-2xl border-2 border-blue-200 bg-gradient-to-br from-blue-50 via-amber-50/50 to-white p-8 shadow">
        {chiffrageErreur !== null ? (
          <div
            role="alert"
            data-testid="chiffrage-erreur-bandeau"
            className="rounded-xl border-2 border-red-300 bg-red-50 px-5 py-4 text-red-900"
          >
            <p className="text-base font-semibold">
              ⚠ Chiffrage incomplet — aucun prix calculé
            </p>
            <p className="mt-1 text-sm">{chiffrageErreur}</p>
            <p className="mt-2 text-xs text-red-700">
              Ce devis a été enregistré en brouillon mais son prix n&apos;a pas
              pu être calculé. Reprends-le pour corriger la cause, puis
              recalcule.
            </p>
          </div>
        ) : (
          <div className="space-y-2 text-center">
            <p className="text-xs uppercase tracking-widest text-muted-foreground">
              💰 Coût total HT
            </p>
            <p
              className="bg-gradient-to-r from-blue-700 to-amber-600 bg-clip-text text-5xl font-bold text-transparent"
              style={{ fontFamily: "Fraunces, serif" }}
            >
              {fmtEuros(reductionPct > 0 ? apresRemise : brut)} €
            </p>
            {reductionPct > 0 && (
              <p className="text-xs text-muted-foreground">
                Brut <strong>{fmtEuros(brut)} €</strong> − Réduction{" "}
                <strong>{reductionPct}%</strong> = {fmtEuros(apresRemise)} €
              </p>
            )}
            <p className="text-sm text-muted-foreground">
              {lots.length} lot{lots.length > 1 ? "s" : ""} ·{" "}
              {lots.reduce((s, l) => s + l.quantite, 0).toLocaleString("fr-FR")}{" "}
              étiquettes au total
            </p>
          </div>
        )}

        <div className="mt-6 flex justify-center">
          <Button
            asChild
            size="lg"
            className="bg-gradient-to-r from-blue-700 to-amber-600 px-8 py-6 text-base font-semibold text-white shadow-md transition-all hover:from-blue-800 hover:to-amber-700 hover:shadow-lg"
          >
            {/* Brief #33 commit 4 — redirige vers /optimisation?devis_id=X
                pour ouvrir le workflow 4 étapes en mode édition (étape 4
                ouverte par défaut, hydratée via getDevisDetail). */}
            <Link href={`/optimisation?devis_id=${devis.id}`}>
              ✎ Modifie ton devis
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}

// Formatage FR aligné droite : 1234.5 → "1 234,50 €".
const fmtEurAlign = (n: number, opts?: { decimals?: number }): string => {
  const decimals = opts?.decimals ?? 2;
  return `${n.toLocaleString("fr-FR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} €`;
};

function RecapitulatifLot({ chiffrage, quantite }: { chiffrage: LotChiffrage; quantite: number }) {
  const { prixVenteHt, coutRevient, pctMarge, prixAuMille, mlTotal, surfaceM2 } = chiffrage;
  const margeEur = prixVenteHt - coutRevient;
  // Ratios dérivés : prix par mille étiquette, par mètre linéaire, par m² imprimé.
  // prixAuMille fourni directement par cost_engine (cf. DevisOutput.prix_au_mille_eur).
  const prixParMl = mlTotal && mlTotal > 0 ? prixVenteHt / mlTotal : null;
  const prixParM2 = surfaceM2 && surfaceM2 > 0 ? prixVenteHt / surfaceM2 : null;
  return (
    <section
      data-testid="recapitulatif-lot"
      className="rounded-lg border border-blue-200 bg-gradient-to-br from-blue-50/40 via-amber-50/20 to-white p-5 print:border-blue-300 print:bg-white"
    >
      <div className="flex flex-wrap items-end justify-between gap-4">
        {/* Mis en avant : Prix vente HT */}
        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-widest text-muted-foreground">
            Prix de vente HT
          </p>
          <p
            className="bg-gradient-to-r from-blue-700 to-amber-600 bg-clip-text font-mono text-3xl font-bold tabular-nums text-transparent sm:text-4xl"
            style={{ fontFamily: "Fraunces, serif" }}
          >
            {fmtEurAlign(prixVenteHt)}
          </p>
        </div>
        {/* Secondaire : coût de revient + marge */}
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Coût de revient</dt>
          <dd className="text-right font-mono tabular-nums">{fmtEurAlign(coutRevient)}</dd>
          <dt className="text-muted-foreground">Marge appliquée</dt>
          <dd className="text-right font-mono tabular-nums">
            {(pctMarge * 100).toFixed(1).replace(".", ",")} %{" "}
            <span className="text-muted-foreground">({fmtEurAlign(margeEur)})</span>
          </dd>
        </dl>
      </div>
      {/* Pied discret : ratios */}
      <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-1 border-t border-dashed border-blue-100 pt-3 text-xs text-muted-foreground sm:grid-cols-3">
        <div className="flex items-baseline justify-between sm:block">
          <dt>Prix au mille étiq.</dt>
          <dd className="font-mono tabular-nums text-foreground sm:mt-0.5">
            {fmtEurAlign(prixAuMille)} / 1 000
          </dd>
        </div>
        <div className="flex items-baseline justify-between sm:block">
          <dt>€ par mètre linéaire</dt>
          <dd className="font-mono tabular-nums text-foreground sm:mt-0.5">
            {prixParMl !== null
              ? `${fmtEurAlign(prixParMl, { decimals: 4 })} / m`
              : "—"}
          </dd>
        </div>
        <div className="flex items-baseline justify-between sm:block">
          <dt>€ par m² imprimé</dt>
          <dd className="font-mono tabular-nums text-foreground sm:mt-0.5">
            {prixParM2 !== null
              ? `${fmtEurAlign(prixParM2, { decimals: 4 })} / m²`
              : "—"}
          </dd>
        </div>
      </dl>
      <p className="mt-2 text-[10px] uppercase tracking-wide text-muted-foreground">
        Sur {quantite.toLocaleString("fr-FR")} étiquettes
        {mlTotal ? ` · ${mlTotal.toLocaleString("fr-FR")} ml` : ""}
        {surfaceM2 ? ` · ${surfaceM2.toLocaleString("fr-FR")} m²` : ""}
      </p>
    </section>
  );
}

function LotCard({
  lot,
  colorClass,
  laizeEtiqMm,
  devEtiqMm,
  mandrinMm,
  chiffrage,
}: {
  lot: LotProductionRead;
  colorClass: string;
  laizeEtiqMm: number;
  devEtiqMm: number;
  mandrinMm: number;
  chiffrage: LotChiffrage | null;
}) {
  const posesTotal = lot.nb_poses_dev * lot.nb_poses_laize;
  // Brief #33 commit 5 — payload_visuel = snapshot OptimisationConfigOut
  // capturé à la création/édition (étape 4 chiffrage). Permet de rejouer
  // SchemaImplantation Vue A/B/C sans recalculer cost_engine côté UI.
  // Null pour les lots historiques (créés avant la migration j1c6e8a3d9b5)
  // → on retombe sur les infos textuelles seules dans ce cas.
  const candidatVisuel =
    lot.payload_visuel && typeof lot.payload_visuel === "object"
      ? (lot.payload_visuel as unknown as OptimisationConfigOut)
      : null;
  return (
    <Card
      className={
        "rounded-lg border-l-4 bg-white p-0 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md " +
        colorClass
      }
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          Lot {lot.ordre} ·{" "}
          <span className="font-mono">
            {lot.cylindre_nb_dents ?? "?"} dents
          </span>{" "}
          <span className="text-sm text-muted-foreground">
            (Z = {lot.cylindre_developpe_mm ?? "—"} mm)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1 text-sm">
          <p>
            <span className="text-muted-foreground">Machine :</span>{" "}
            <strong>{lot.machine_nom}</strong>
          </p>
          <p>
            <span className="text-muted-foreground">Poses :</span>{" "}
            <span className="font-mono">
              {lot.nb_poses_laize}×{lot.nb_poses_dev} = {posesTotal}
            </span>
          </p>
          <p>
            <span className="text-muted-foreground">Sens :</span>{" "}
            {lot.sens_enroulement_libelle ?? `Sens ${lot.sens_enroulement}`}
          </p>
          <p>
            <span className="text-muted-foreground">Quantité :</span>{" "}
            <strong>{lot.quantite.toLocaleString("fr-FR")}</strong> étiquettes
          </p>
          <p>
            <span className="text-muted-foreground">Matière :</span>{" "}
            {lot.matiere_libelle ?? `#${lot.matiere_id}`}
          </p>
        </div>

        <div className="flex flex-col items-end justify-center gap-1 rounded bg-gradient-to-br from-blue-50/50 to-amber-50/40 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            Coût lot HT
          </p>
          <p
            className="text-2xl font-bold text-blue-800"
            style={{ fontFamily: "Fraunces, serif" }}
          >
            {fmtEuros(lot.cout_lot_ht_eur)} €
          </p>
          {lot.intervalle_dev_reel_mm && (
            <p className="text-[10px] text-muted-foreground">
              Δ dev {lot.intervalle_dev_reel_mm} mm · Δ laize{" "}
              {lot.intervalle_laize_reel_mm ?? "—"} mm
            </p>
          )}
        </div>
      </CardContent>

      {candidatVisuel && (
        <div className="border-t border-border px-4 pb-4 pt-4 sm:px-6">
          <SchemaImplantation
            config={candidatVisuel}
            laizeEtiqMm={laizeEtiqMm}
            devEtiqMm={devEtiqMm}
            mandrinMm={mandrinMm}
          />
        </div>
      )}

      {chiffrage && (
        <div
          data-testid={`rapport-fabrication-lot-${lot.ordre}`}
          className="border-t border-border px-4 pb-4 pt-4 sm:px-6"
        >
          <header className="mb-3">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Rapport de fabrication
            </h3>
          </header>
          <div className="space-y-4">
            <RecapitulatifLot chiffrage={chiffrage} quantite={lot.quantite} />
            <PostesCard
              postes={chiffrage.postes}
              coutRevient={chiffrage.coutRevient}
            />
          </div>
        </div>
      )}
    </Card>
  );
}
