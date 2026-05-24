"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState, type ChangeEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import {
  createControleBat,
  getControleBatContext,
  PHOTO_TIRAGE_MAX_SIZE_MO,
  relancerTirage,
  type ControleBatContext,
  type ControleBatResult,
  type DecideControleResponse,
} from "@/lib/api/controleBat";

import { DialogValiderProduction } from "../_components/DialogValiderProduction";
import { ResultatControle } from "../_components/ResultatControle";
import { TentativesTimeline } from "../_components/TentativesTimeline";

/**
 * Sprint 15 Lots C/D/E — Détail Contrôle BAT : capture, analyse, décision.
 *
 * Cible atelier (tablette, mobile). Mobile-first strict, gros boutons
 * tactiles, encart protocole en texte clair (PAS de tooltip au survol).
 *
 * Workflow opérateur :
 *   1. Affichage du BAT de référence en grand (Lot C).
 *   2. Encart protocole photo toujours visible (Lot C).
 *   3. Bouton « 📷 Prendre photo 1er tirage » → input capture="environment"
 *      qui ouvre la caméra arrière de la tablette ; fallback upload fichier
 *      sur desktop (Lot C).
 *   4. Au submit, animation « Analyse en cours… » pendant le POST IA
 *      (Lot C, ~5-10 s).
 *   5. Résultat détaillé : score, écarts, sens enroulement (Lot D).
 *   6. Décision opérateur (Lot E) :
 *        - « ✅ Valider la production » → POST decision (dialog décideur)
 *        - « 🔁 Ajuster et recommencer » → reset photo, prochain submit
 *          appelle l'endpoint /retirage avec le dernier controle_id
 *          → la tentative est incrémentée côté backend.
 *      Une fois validée, les boutons d'action sont masqués.
 *      Si le backend lève `alerte_chef_atelier`, un bandeau rouge
 *      "Prévenir le chef d'atelier" s'affiche en tête du résultat.
 *
 * Gating : si l'utilisateur n'a pas `has_flexocheck`, message d'accès
 * sans appel API (le backend renverrait 403 de toute façon).
 */
export default function AtelierControleBatDetailPage() {
  const params = useParams<{ id: string }>();
  const devisId = Number(params?.id);
  const { user } = useAuth();
  const hasAccess = user?.has_flexocheck === true;

  const [context, setContext] = useState<ControleBatContext | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const [loadingContext, setLoadingContext] = useState(true);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  // Historique local des tentatives sur cette session de contrôle.
  // Lot E : on tient la liste pour la timeline. Le rendu détaillé se fait
  // toujours sur la DERNIÈRE tentative (la plus récente).
  const [attempts, setAttempts] = useState<ControleBatResult[]>([]);
  const lastResult = attempts.length > 0 ? attempts[attempts.length - 1] : null;
  const hasResult = lastResult !== null;

  // Décision finale opérateur (Lot E). Une fois set, on bloque les boutons
  // d'action — le contrôle est clôturé.
  const [decision, setDecision] = useState<DecideControleResponse | null>(null);
  const [showValidateDialog, setShowValidateDialog] = useState(false);

  useEffect(() => {
    if (!hasAccess) {
      setLoadingContext(false);
      return;
    }
    if (!Number.isInteger(devisId) || devisId <= 0) {
      setContextError("Identifiant de devis invalide.");
      setLoadingContext(false);
      return;
    }
    let cancelled = false;
    setLoadingContext(true);
    setContextError(null);
    getControleBatContext(devisId)
      .then((ctx) => {
        if (!cancelled) setContext(ctx);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setContextError(
            err instanceof Error ? err.message : String(err),
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingContext(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hasAccess, devisId]);

  // Cleanup objectURL du preview à chaque changement / unmount pour éviter
  // les fuites mémoire (les photos atelier peuvent peser plusieurs Mo).
  useEffect(() => {
    return () => {
      if (photoPreview) URL.revokeObjectURL(photoPreview);
    };
  }, [photoPreview]);

  const handlePhotoChange = (e: ChangeEvent<HTMLInputElement>) => {
    setPhotoError(null);
    setAnalyzeError(null);
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.type.startsWith("image/")) {
      setPhotoError(
        `Format non supporté (${f.type || "inconnu"}). Une image est requise.`,
      );
      return;
    }
    if (f.size > PHOTO_TIRAGE_MAX_SIZE_MO * 1024 * 1024) {
      setPhotoError(
        `Photo trop volumineuse (max ${PHOTO_TIRAGE_MAX_SIZE_MO} Mo).`,
      );
      return;
    }
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhoto(f);
    setPhotoPreview(URL.createObjectURL(f));
  };

  const handleAnalyze = async () => {
    if (!photo || !context) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      // 1ère analyse → createControleBat ; retirage → relancerTirage.
      // Le backend incrémente lui-même `tentative` côté retirage, on lui
      // fait confiance pour le compteur.
      const res =
        lastResult === null
          ? await createControleBat(context.devis_id, photo)
          : await relancerTirage(lastResult.controle_id, photo);
      setAttempts((prev) => [...prev, res]);
      // Vide la photo pour préparer un éventuel re-tirage : la photo en cours
      // a été analysée, garder le preview deviendrait trompeur.
      if (photoPreview) URL.revokeObjectURL(photoPreview);
      setPhoto(null);
      setPhotoPreview(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : String(err));
    } finally {
      setAnalyzing(false);
    }
  };

  // Lot E — "Ajuster et recommencer" : reset l'erreur d'analyse et la photo
  // courante (si l'opérateur en a une en attente), conserve attempts pour
  // la timeline, puis ouvre directement la caméra. Le but : un seul geste
  // pour relancer le cycle de capture. Au prochain submit, c'est
  // `relancerTirage` qui sera appelé (lastResult !== null).
  const handleAdjustAndRetry = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhoto(null);
    setPhotoPreview(null);
    setPhotoError(null);
    setAnalyzeError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    fileInputRef.current?.click();
  };

  if (!hasAccess) {
    return <AccesRefuseSection />;
  }

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-4 sm:p-6">
      <nav className="text-sm">
        <Link
          href="/atelier/controle-bat"
          className="text-muted-foreground hover:text-foreground"
        >
          ← Productions en cours
        </Link>
      </nav>

      {loadingContext && (
        <p className="text-base text-muted-foreground">Chargement…</p>
      )}

      {contextError && (
        <div
          role="alert"
          className="rounded-md border border-destructive bg-destructive/10 p-4 text-base text-destructive"
        >
          <strong>Erreur :</strong> {contextError}
        </div>
      )}

      {context && (
        <>
          <header className="space-y-1">
            <h1 className="font-mono text-2xl font-bold sm:text-3xl">
              {context.devis_numero}
            </h1>
            <p className="text-base text-muted-foreground">
              {context.client_nom ?? "—"} ·{" "}
              {context.designation ?? "Sans désignation"} ·{" "}
              {context.machine_nom}
            </p>
          </header>

          <BatReferenceSection context={context} />

          <ProtocolePhotoSection />

          {/*
            Section capture. Conditions d'affichage :
            - décision finale enregistrée → on masque, le contrôle est clôturé.
            - aucun résultat encore → 1ère analyse (entry-point du flow).
            - résultat existant + photo en attente → re-tirage en cours,
              on a besoin du preview + bouton "Lancer le tirage".
            - résultat existant + pas de photo → on masque : le bouton
              "Ajuster et recommencer" de la section résultats sert d'entry-
              point unique au prochain cycle (évite la double commande).
          */}
          {decision === null && (!hasResult || photo !== null) && (
            <CaptureSection
              inputRef={fileInputRef}
              photo={photo}
              photoPreview={photoPreview}
              photoError={photoError}
              analyzing={analyzing}
              analyzeError={analyzeError}
              hasResult={hasResult}
              onPhotoChange={handlePhotoChange}
              onAnalyze={handleAnalyze}
            />
          )}

          {/*
            L'input file doit rester monté pour que `handleAdjustAndRetry`
            puisse appeler `.click()` dessus depuis la section résultats,
            même quand la CaptureSection est masquée. On le rend en sr-only
            quand la CaptureSection n'est pas affichée.
          */}
          {decision === null && hasResult && photo === null && (
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handlePhotoChange}
              className="sr-only"
              data-testid="photo-input"
              aria-label="Photo du re-tirage"
              disabled={analyzing}
            />
          )}

          {/* Timeline + dernier résultat dès qu'on a au moins 1 tentative. */}
          {hasResult && lastResult && (
            <ResultatsSection
              attempts={attempts}
              lastResult={lastResult}
              decisionEnregistree={decision}
              onValiderClick={() => setShowValidateDialog(true)}
              onAjusterClick={handleAdjustAndRetry}
            />
          )}

          {/* Dialog validation : monté de façon contrôlée. */}
          {hasResult && lastResult && (
            <DialogValiderProduction
              controleId={lastResult.controle_id}
              devisNumero={context.devis_numero}
              open={showValidateDialog}
              onOpenChange={setShowValidateDialog}
              onValidated={(res) => setDecision(res)}
            />
          )}
        </>
      )}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Section BAT de référence
// ---------------------------------------------------------------------------

function BatReferenceSection({ context }: { context: ControleBatContext }) {
  const isImage = context.bat_mime_type.startsWith("image/");
  const isPdf = context.bat_mime_type === "application/pdf";
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">BAT de référence</CardTitle>
        <CardDescription>
          C&apos;est ce visuel que la photo du 1er tirage doit reproduire.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isImage && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={context.bat_url}
            alt={`BAT de référence pour ${context.devis_numero}`}
            data-testid="bat-image"
            className="max-h-[60vh] w-full rounded-md border border-border bg-muted object-contain"
          />
        )}
        {isPdf && (
          <iframe
            src={context.bat_url}
            title={`BAT de référence (PDF) pour ${context.devis_numero}`}
            data-testid="bat-pdf"
            className="h-[60vh] w-full rounded-md border border-border bg-muted"
          />
        )}
        {!isImage && !isPdf && (
          <p
            role="alert"
            className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
          >
            Type de BAT non affichable ({context.bat_mime_type}). Téléversez
            de nouveau un PDF ou une image.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Encart protocole photo (texte visible — pas de tooltip)
// ---------------------------------------------------------------------------

function ProtocolePhotoSection() {
  return (
    <Card data-testid="protocole-photo" className="border-blue-300 bg-blue-50">
      <CardHeader>
        <CardTitle className="text-base text-blue-900">
          Protocole photo
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-1 text-sm text-blue-900 sm:text-base">
          <li>• Face à la sortie presse, à environ 1 m de la bande.</li>
          <li>• Cadrage perpendiculaire à la bande (caméra à plat).</li>
          <li>• Bande défilant du fond vers l&apos;opérateur.</li>
          <li>• Éclairage atelier ambiant — pas de flash.</li>
        </ul>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Section capture + analyse
// ---------------------------------------------------------------------------

interface CaptureSectionProps {
  inputRef: React.RefObject<HTMLInputElement>;
  photo: File | null;
  photoPreview: string | null;
  photoError: string | null;
  analyzing: boolean;
  analyzeError: string | null;
  // hasResult permet d'adapter le libellé du bouton primaire : « Prendre
  // photo 1er tirage » à la 1ère tentative, « Prendre une nouvelle photo »
  // ensuite (workflow re-tirage Lot E).
  hasResult: boolean;
  onPhotoChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onAnalyze: () => void;
}

function CaptureSection({
  inputRef,
  photo,
  photoPreview,
  photoError,
  analyzing,
  analyzeError,
  hasResult,
  onPhotoChange,
  onAnalyze,
}: CaptureSectionProps) {
  const primaryLabel = hasResult
    ? "📷 Prendre une nouvelle photo"
    : "📷 Prendre photo 1er tirage";
  const submitLabel = hasResult
    ? "Lancer un nouveau tirage"
    : "Analyser la conformité";
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          {hasResult ? "Re-tirage" : "Photo du 1er tirage"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/*
          capture="environment" demande au navigateur d'ouvrir la caméra
          arrière sur mobile/tablette. Sur desktop, l'attribut est ignoré
          et le bouton ouvre la sélection de fichier classique.
        */}
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={onPhotoChange}
          className="sr-only"
          data-testid="photo-input"
          aria-label="Photo du 1er tirage"
          disabled={analyzing}
        />

        {!photo && (
          <Button
            type="button"
            size="lg"
            onClick={() => inputRef.current?.click()}
            disabled={analyzing}
            className="h-14 w-full text-lg"
          >
            {primaryLabel}
          </Button>
        )}

        {photoError && (
          <div
            role="alert"
            className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
          >
            {photoError}
          </div>
        )}

        {photoPreview && (
          <div data-testid="photo-preview" className="space-y-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photoPreview}
              alt="Aperçu de la photo du 1er tirage"
              className="max-h-[50vh] w-full rounded-md border border-border bg-muted object-contain"
            />
          </div>
        )}

        {photo && (
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={() => inputRef.current?.click()}
              disabled={analyzing}
              className="h-12 flex-1 text-base"
            >
              Reprendre la photo
            </Button>
            <Button
              type="button"
              size="lg"
              onClick={onAnalyze}
              disabled={analyzing}
              className="h-12 flex-1 text-base"
            >
              {analyzing ? "Analyse en cours…" : submitLabel}
            </Button>
          </div>
        )}

        {analyzing && (
          <div
            data-testid="analyzing-banner"
            role="status"
            aria-live="polite"
            className="flex items-center gap-3 rounded-md border border-blue-300 bg-blue-50 p-4 text-blue-900"
          >
            <span
              aria-hidden="true"
              className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-blue-300 border-t-blue-700"
            />
            <div>
              <div className="font-medium">Analyse en cours…</div>
              <div className="text-sm">
                Comparaison avec le BAT (généralement 5 à 10 secondes).
              </div>
            </div>
          </div>
        )}

        {analyzeError && (
          <div
            role="alert"
            className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
          >
            <strong>Analyse impossible :</strong> {analyzeError}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Section résultats (Lot D affichage + Lot E workflow)
// ---------------------------------------------------------------------------

interface ResultatsSectionProps {
  attempts: ControleBatResult[];
  lastResult: ControleBatResult;
  decisionEnregistree: DecideControleResponse | null;
  onValiderClick: () => void;
  onAjusterClick: () => void;
}

function ResultatsSection({
  attempts,
  lastResult,
  decisionEnregistree,
  onValiderClick,
  onAjusterClick,
}: ResultatsSectionProps) {
  return (
    <section className="space-y-4">
      <TentativesTimeline
        attempts={attempts}
        currentIndex={attempts.length - 1}
      />

      {lastResult.alerte_chef_atelier && decisionEnregistree === null && (
        <div
          role="alert"
          data-testid="alerte-chef-atelier"
          className="rounded-md border-2 border-red-500 bg-red-50 p-4"
        >
          <div className="flex items-start gap-3">
            <span aria-hidden="true" className="text-2xl">
              📣
            </span>
            <div>
              <div className="text-base font-bold text-red-900 sm:text-lg">
                Prévenir le chef d&apos;atelier
              </div>
              <p className="mt-1 text-sm text-red-900">
                Trop de tentatives échouées sur cette production. Avant
                de poursuivre, demandez l&apos;avis du chef d&apos;atelier
                — la décision peut nécessiter un arbitrage métier.
              </p>
            </div>
          </div>
        </div>
      )}

      <ResultatControle result={lastResult} />

      {decisionEnregistree ? (
        <DecisionEnregistreeBlock decision={decisionEnregistree} />
      ) : (
        <DecisionActionsBlock
          onValiderClick={onValiderClick}
          onAjusterClick={onAjusterClick}
        />
      )}
    </section>
  );
}

function DecisionActionsBlock({
  onValiderClick,
  onAjusterClick,
}: {
  onValiderClick: () => void;
  onAjusterClick: () => void;
}) {
  return (
    <div
      data-testid="decision-actions"
      className="flex flex-col gap-2 sm:flex-row"
    >
      <Button
        type="button"
        variant="outline"
        size="lg"
        onClick={onAjusterClick}
        className="h-14 flex-1 text-base"
      >
        🔁 Ajuster et recommencer
      </Button>
      <Button
        type="button"
        size="lg"
        onClick={onValiderClick}
        className="h-14 flex-1 bg-emerald-600 text-base text-white hover:bg-emerald-700"
      >
        ✅ Valider la production
      </Button>
    </div>
  );
}

function DecisionEnregistreeBlock({
  decision,
}: {
  decision: DecideControleResponse;
}) {
  const valider = decision.decision_finale === "valider";
  const tone = valider
    ? "border-emerald-300 bg-emerald-50 text-emerald-900"
    : "border-red-300 bg-red-50 text-red-900";
  const icone = valider ? "✅" : "⛔";
  const titre = valider
    ? "Production validée"
    : "Production rejetée";
  const decidedAt = new Date(decision.decided_at).toLocaleString("fr-FR");
  return (
    <div
      data-testid="decision-enregistree"
      role="status"
      aria-live="polite"
      className={`rounded-md border-2 p-4 ${tone}`}
    >
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="text-2xl">
          {icone}
        </span>
        <div>
          <div className="text-base font-bold sm:text-lg">{titre}</div>
          <div className="mt-1 text-sm">
            par <strong>{decision.decideur}</strong> · {decidedAt}
          </div>
          {decision.motif && (
            <div className="mt-1 text-sm">
              <strong>Motif :</strong> {decision.motif}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AccesRefuseSection() {
  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
      <Card>
        <CardHeader>
          <CardTitle>Module FlexoCheck non activé</CardTitle>
          <CardDescription>
            Le module Contrôle BAT IA fait partie de l&apos;offre FlexoCheck.
            Contactez votre administrateur pour activer l&apos;accès sur votre
            compte.
          </CardDescription>
        </CardHeader>
      </Card>
    </main>
  );
}
