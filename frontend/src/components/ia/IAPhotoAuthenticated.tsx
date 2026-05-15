"use client";

import { useEffect, useState } from "react";

import { fetchIAPhotoBlob } from "@/lib/api";

/**
 * Affiche une photo servie par /api/ia/photos/{key} avec authentification.
 *
 * Le tag `<img>` standard ne peut pas envoyer le Bearer JWT — d'où ce
 * composant qui fait fetch + URL.createObjectURL puis affiche l'URL
 * blob locale. Revoke automatique au unmount pour éviter les fuites.
 *
 * Si imageKey est null (analyse sans photo physique, mode dégradé ou
 * ancienne row pré-feat) → placeholder gris discret.
 */
export function IAPhotoAuthenticated({
  imageKey,
  alt,
  className,
}: {
  imageKey: string | null;
  alt: string;
  className?: string;
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!imageKey) {
      setObjectUrl(null);
      setError(false);
      return;
    }
    let cancelled = false;
    let createdUrl: string | null = null;
    setError(false);

    fetchIAPhotoBlob(imageKey)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        createdUrl = url;
        setObjectUrl(url);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [imageKey]);

  if (!imageKey || error) {
    return (
      <div
        className={`flex items-center justify-center bg-muted text-xs text-muted-foreground ${className ?? ""}`}
        aria-label={error ? "Photo indisponible" : "Pas de photo"}
      >
        {error ? "Photo indisponible" : "Pas de photo"}
      </div>
    );
  }

  if (!objectUrl) {
    return (
      <div
        className={`flex items-center justify-center bg-muted text-xs text-muted-foreground ${className ?? ""}`}
      >
        Chargement…
      </div>
    );
  }

  // Object URL local → pas besoin de next/image (qui exigerait remoteImages)
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={objectUrl} alt={alt} className={className} />;
}
