"use client";

import { useEffect, useRef, useState, type DragEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import {
  BAT_MAX_SIZE_MO,
  BAT_MIME_TYPES,
  uploadBatReference,
  type BatMimeType,
} from "@/lib/api/controleBat";

interface UploadBatDialogProps {
  devisId: number;
  devisNumero: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUploaded: () => void;
}

/**
 * Sprint 15 Lot B — Dialog d'upload du BAT de référence.
 *
 * Cible atelier : zone de drop visible, gros bouton "Choisir un fichier"
 * pour les opérateurs sur tablette sans drag-and-drop natif fluide. Aperçu
 * inline pour les images (vérification rapide qu'on n'a pas attaché la
 * mauvaise photo), badge fichier pour les PDF.
 *
 * Le bouton de soumission est désactivé tant qu'aucun fichier valide n'est
 * sélectionné. Les rejets de validation (type / taille) sont affichés
 * dans la zone d'erreur du dialog plutôt qu'en toast, pour rester visible
 * pendant que l'opérateur ré-essaie.
 */
export function UploadBatDialog({
  devisId,
  devisNumero,
  open,
  onOpenChange,
  onUploaded,
}: UploadBatDialogProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset à chaque ouverture/fermeture : pas de fuite d'état d'un upload à
  // l'autre, et pas d'image fantôme si l'opérateur ferme puis ré-ouvre.
  useEffect(() => {
    if (!open) {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setFile(null);
      setPreviewUrl(null);
      setDragOver(false);
      setSubmitting(false);
      setError(null);
    }
    // previewUrl dans les deps ferait boucle ; on veut juste réagir à open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleSelect = (f: File | null) => {
    setError(null);
    if (!f) return;
    if (!BAT_MIME_TYPES.includes(f.type as BatMimeType)) {
      setError(
        `Format non supporté (${f.type || "inconnu"}). Autorisés : PDF, JPEG, PNG, WebP.`,
      );
      return;
    }
    if (f.size > BAT_MAX_SIZE_MO * 1024 * 1024) {
      setError(
        `Fichier trop volumineux (max ${BAT_MAX_SIZE_MO} Mo). Compressez ou réduisez la définition.`,
      );
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(f);
    if (f.type.startsWith("image/")) {
      setPreviewUrl(URL.createObjectURL(f));
    } else {
      setPreviewUrl(null);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0] ?? null;
    handleSelect(f);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      await uploadBatReference(devisId, file);
      onUploaded();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setSubmitting(false);
    }
  };

  const isImage = file?.type.startsWith("image/") ?? false;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Rattacher le BAT — {devisNumero}</DialogTitle>
          <DialogDescription>
            BAT de référence pour le contrôle du premier tirage. Formats
            acceptés : PDF, JPEG, PNG, WebP (max {BAT_MAX_SIZE_MO} Mo).
          </DialogDescription>
        </DialogHeader>

        <div
          data-testid="dropzone"
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={cn(
            "rounded-md border-2 border-dashed p-6 text-center transition-colors",
            dragOver
              ? "border-primary bg-primary/5"
              : "border-input bg-muted/30",
          )}
        >
          <p className="text-sm text-muted-foreground">
            Glissez le fichier ici ou cliquez sur le bouton ci-dessous.
          </p>
          <div className="mt-4">
            <input
              ref={fileInputRef}
              type="file"
              accept={BAT_MIME_TYPES.join(",")}
              onChange={(e) => handleSelect(e.target.files?.[0] ?? null)}
              className="sr-only"
              data-testid="file-input"
              aria-label="Fichier BAT"
            />
            <Button
              type="button"
              size="lg"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              className="h-12 text-base"
            >
              Choisir un fichier
            </Button>
          </div>
        </div>

        {file && (
          <div
            data-testid="file-preview"
            className="space-y-2 rounded-md border border-border p-3"
          >
            <div className="flex items-baseline justify-between gap-2">
              <span
                className="truncate text-sm font-medium"
                title={file.name}
              >
                {file.name}
              </span>
              <span className="flex-shrink-0 text-xs text-muted-foreground">
                {formatBytes(file.size)}
              </span>
            </div>
            {isImage && previewUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={previewUrl}
                alt={`Aperçu du BAT ${file.name}`}
                className="max-h-64 w-full rounded-md border border-border object-contain"
              />
            )}
            {!isImage && (
              <p className="rounded bg-muted px-2 py-1 text-xs text-muted-foreground">
                Aperçu PDF non disponible — le fichier sera envoyé tel quel.
              </p>
            )}
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
          >
            {error}
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Annuler
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={!file || submitting}
            className="h-11 text-base"
          >
            {submitting ? "Téléversement…" : "Téléverser le BAT"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / 1024 / 1024).toFixed(1)} Mo`;
}
