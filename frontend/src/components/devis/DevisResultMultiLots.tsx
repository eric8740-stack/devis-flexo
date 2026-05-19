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

import { SchemaImplantation } from "@/components/SchemaImplantation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type {
  DevisDetail,
  LotProductionRead,
  OptimisationConfigOut,
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
  const brut = parseFloat(devis.ht_total_eur) || 0;
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
          />
        ))}
        {lots.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Ce devis n&apos;a pas encore de lot enregistré.
          </p>
        )}
      </section>

      {/* Récap total HT — card hero gradient bleu→or (§9bis) */}
      <section className="rounded-2xl border-2 border-blue-200 bg-gradient-to-br from-blue-50 via-amber-50/50 to-white p-8 shadow">
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

function LotCard({
  lot,
  colorClass,
  laizeEtiqMm,
  devEtiqMm,
  mandrinMm,
}: {
  lot: LotProductionRead;
  colorClass: string;
  laizeEtiqMm: number;
  devEtiqMm: number;
  mandrinMm: number;
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
    </Card>
  );
}
