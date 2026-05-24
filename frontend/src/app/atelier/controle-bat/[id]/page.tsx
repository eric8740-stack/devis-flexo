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
  type ControleBatContext,
  type ControleBatResult,
} from "@/lib/api/controleBat";

import { ResultatControle } from "../_components/ResultatControle";

/**
 * Sprint 15 Lot C — Détail Contrôle BAT : capture du 1er tirage.
 *
 * Cible atelier (tablette, mobile). Mobile-first strict, gros boutons
 * tactiles, encart protocole en texte clair (PAS de tooltip au survol —
 * un opérateur sur tablette ne survole rien).
 *
 * Trois sections :
 *   1. BAT de référence affiché en grand (la photo viendra s'y comparer)
 *   2. Encart protocole photo (toujours visible)
 *   3. Bouton « 📷 Prendre photo 1er tirage » → input capture="environment"
 *      qui ouvre la caméra arrière de la tablette ; fallback upload fichier
 *      sur desktop
 *
 * Au submit, animation « Analyse en cours… » pendant le POST
 * (5-10 s côté IA d'après le brief). Le rendu détaillé du résultat
 * (score, écarts, sens enroulement…) est implémenté au Lot D — pour
 * l'instant on confirme juste la réception de l'analyse et on propose
 * de relancer une capture.
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
  const [result, setResult] = useState<ControleBatResult | null>(null);

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
    setResult(null);
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
      const res = await createControleBat(context.devis_id, photo);
      setResult(res);
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : String(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReset = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhoto(null);
    setPhotoPreview(null);
    setPhotoError(null);
    setAnalyzeError(null);
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
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

          <CaptureSection
            inputRef={fileInputRef}
            photo={photo}
            photoPreview={photoPreview}
            photoError={photoError}
            analyzing={analyzing}
            analyzeError={analyzeError}
            result={result}
            onPhotoChange={handlePhotoChange}
            onAnalyze={handleAnalyze}
            onReset={handleReset}
          />
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
  result: ControleBatResult | null;
  onPhotoChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onAnalyze: () => void;
  onReset: () => void;
}

function CaptureSection({
  inputRef,
  photo,
  photoPreview,
  photoError,
  analyzing,
  analyzeError,
  result,
  onPhotoChange,
  onAnalyze,
  onReset,
}: CaptureSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Photo du 1er tirage</CardTitle>
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

        {!photo && !result && (
          <Button
            type="button"
            size="lg"
            onClick={() => inputRef.current?.click()}
            disabled={analyzing}
            className="h-14 w-full text-lg"
          >
            📷 Prendre photo 1er tirage
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

        {photo && !result && (
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
              {analyzing ? "Analyse en cours…" : "Analyser la conformité"}
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

        {result && (
          <div className="space-y-4">
            <ResultatControle result={result} />
            {/*
              Lot D — bouton minimal pour relancer une capture. Le workflow
              re-tirage complet (compteur tentatives, décision finale
              opérateur, alerte chef d'atelier) est livré au Lot E.
            */}
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={onReset}
              className="h-12 w-full text-base"
            >
              Nouvelle capture
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
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
