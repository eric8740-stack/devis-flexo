"use client";

import { useEffect, useState } from "react";

import { fetchControleBatBlob } from "@/lib/api/controleBat";

/**
 * Sprint 15 — Affichage d'un BAT (ou photo de tirage) servi par
 * `/api/flexocheck/blobs/{key}`, endpoint AUTHENTIFIÉ.
 *
 * Le tag `<img>` ou `<iframe>` standard ne peut pas envoyer de header
 * Authorization Bearer. D'où ce wrapper : fetch authentifié → blob →
 * `URL.createObjectURL` → consommable par img/iframe en src local. Revoke
 * automatique au unmount pour éviter les fuites mémoire (les BAT PDF
 * peuvent peser plusieurs Mo).
 *
 * Branche img vs iframe selon le mime type :
 *   - "image/*" → balise <img>
 *   - "application/pdf" → balise <iframe> (PDF natif navigateur)
 *   - autre → message d'erreur
 *
 * `blobUrl` est l'URL relative renvoyée par le backend (ex:
 * `/api/flexocheck/blobs/abc.pdf`). Si null, on n'a pas de BAT rattaché.
 */
interface BatBlobAuthenticatedProps {
  blobUrl: string | null;
  mimeType: string | null;
  alt: string;
  // Classes appliquées à l'élément média (img/iframe). Les conteneurs
  // d'attente/erreur reprennent la même classe pour préserver la taille.
  className?: string;
  // testId optionnel pour pointer le média rendu (img/iframe) côté tests.
  testIdImage?: string;
  testIdPdf?: string;
}

export function BatBlobAuthenticated({
  blobUrl,
  mimeType,
  alt,
  className,
  testIdImage,
  testIdPdf,
}: BatBlobAuthenticatedProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!blobUrl) {
      setObjectUrl(null);
      setError(null);
      return;
    }
    let cancelled = false;
    let created: string | null = null;
    setError(null);

    fetchControleBatBlob(blobUrl)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        created = url;
        setObjectUrl(url);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      });

    return () => {
      cancelled = true;
      if (created) URL.revokeObjectURL(created);
    };
  }, [blobUrl]);

  if (!blobUrl) {
    return (
      <div
        className={`flex items-center justify-center bg-muted text-sm text-muted-foreground ${className ?? ""}`}
        aria-label="Aucun BAT rattaché"
      >
        Aucun BAT rattaché à ce devis.
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className={`flex items-center justify-center bg-destructive/10 p-3 text-sm text-destructive ${className ?? ""}`}
      >
        BAT indisponible : {error}
      </div>
    );
  }

  if (!objectUrl) {
    return (
      <div
        className={`flex items-center justify-center bg-muted text-sm text-muted-foreground ${className ?? ""}`}
      >
        Chargement du BAT…
      </div>
    );
  }

  if (mimeType?.startsWith("image/")) {
    // Object URL local → pas besoin de next/image (qui exigerait remoteImages).
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={objectUrl} alt={alt} className={className} data-testid={testIdImage} />;
  }

  if (mimeType === "application/pdf") {
    return (
      <iframe
        src={objectUrl}
        title={alt}
        className={className}
        data-testid={testIdPdf}
      />
    );
  }

  return (
    <div
      role="alert"
      className={`flex items-center justify-center bg-amber-50 p-3 text-sm text-amber-900 ${className ?? ""}`}
    >
      Type de BAT non affichable ({mimeType ?? "inconnu"}).
    </div>
  );
}
