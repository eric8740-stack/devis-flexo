"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

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
  listProductionsActives,
  type ListProductionsActivesResponse,
  type ProductionActive,
} from "@/lib/api/controleBat";

import { UploadBatDialog } from "./_components/UploadBatDialog";

/**
 * Sprint 15 Lot A — Écran atelier Contrôle BAT IA.
 *
 * Cible : tablette / poste atelier. Mobile-first strict, gros boutons
 * tactiles, pas de tooltips au survol — toute info utile en texte.
 *
 * Affiche la liste des productions actives (devis confirmés en cours
 * de production). Une carte par production avec n° devis, client,
 * désignation, machine, état du BAT de référence. La sélection ouvre
 * l'écran de contrôle (route /atelier/controle-bat/[id], implémentée
 * au Lot C).
 *
 * Lot B : depuis la carte, bouton "Rattacher le BAT" qui ouvre le
 * dialog d'upload. Au succès on rafraîchit la liste pour mettre à
 * jour le badge bat_reference_uploaded.
 *
 * Gating : si l'utilisateur n'a pas `has_flexocheck`, on affiche un
 * message d'accès sans tenter l'appel API (le backend renvoie 403
 * de toute façon, mais on évite la requête).
 */
export default function AtelierControleBatPage() {
  const { user } = useAuth();
  const hasAccess = user?.has_flexocheck === true;

  const [data, setData] = useState<ListProductionsActivesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploadTarget, setUploadTarget] = useState<ProductionActive | null>(
    null,
  );

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    return listProductionsActives()
      .then((res) => setData(res))
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!hasAccess) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    listProductionsActives()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hasAccess]);

  if (!hasAccess) {
    return <AccesRefuseSection />;
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-4 sm:p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">
          Contrôle BAT — productions en cours
        </h1>
        <p className="text-sm text-muted-foreground sm:text-base">
          Sélectionnez une production pour lancer le contrôle du premier
          tirage face au BAT de référence.
        </p>
      </header>

      {loading && (
        <p className="text-base text-muted-foreground">Chargement…</p>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-md border border-destructive bg-destructive/10 p-4 text-base text-destructive"
        >
          <strong>Erreur :</strong> {error}
        </div>
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState />
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <ul
          aria-label="Productions actives"
          className="grid gap-4 sm:grid-cols-2"
        >
          {data.items.map((p) => (
            <li key={p.devis_id}>
              <ProductionCard
                production={p}
                onRequestUploadBat={() => setUploadTarget(p)}
              />
            </li>
          ))}
        </ul>
      )}

      {uploadTarget && (
        <UploadBatDialog
          devisId={uploadTarget.devis_id}
          devisNumero={uploadTarget.designation}
          open={uploadTarget !== null}
          onOpenChange={(open) => {
            if (!open) setUploadTarget(null);
          }}
          onUploaded={() => {
            void reload();
          }}
        />
      )}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Composants
// ---------------------------------------------------------------------------

function ProductionCard({
  production,
  onRequestUploadBat,
}: {
  production: ProductionActive;
  onRequestUploadBat: () => void;
}) {
  const href = `/atelier/controle-bat/${production.devis_id}`;
  const hasBat = production.bat_reference_uploaded;
  return (
    <Card
      data-testid={`production-${production.devis_id}`}
      className="flex h-full flex-col"
    >
      <CardHeader>
        <div className="flex items-baseline justify-between gap-2">
          {/* designation = Devis.numero (DEV-YYYY-NNNN) composé backend */}
          <CardTitle className="font-mono text-xl sm:text-2xl">
            {production.designation}
          </CardTitle>
          {hasBat ? (
            <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900">
              BAT rattaché
            </span>
          ) : (
            <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
              BAT manquant
            </span>
          )}
        </div>
        <CardDescription className="text-base text-foreground">
          {production.client ?? "—"}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-between gap-4">
        <dl className="space-y-1 text-sm sm:text-base">
          <div>
            <dt className="inline text-muted-foreground">Machine : </dt>
            <dd className="inline">{production.machine}</dd>
          </div>
        </dl>
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            variant="outline"
            size="lg"
            onClick={onRequestUploadBat}
            className="h-12 w-full text-base"
          >
            {hasBat ? "Remplacer le BAT" : "📎 Rattacher le BAT"}
          </Button>
          <Button
            asChild
            size="lg"
            disabled={!hasBat}
            className="h-12 w-full text-base"
          >
            {hasBat ? (
              <Link href={href}>Ouvrir le contrôle →</Link>
            ) : (
              // Bouton désactivé : on rend un span pour éviter une navigation
              // sur un BAT absent (le Lot C exige bat_reference_uploaded).
              <span aria-disabled="true">Ouvrir le contrôle →</span>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Aucune production en cours</CardTitle>
        <CardDescription>
          Les devis confirmés en cours de production apparaîtront ici dès
          qu&apos;ils seront lancés sur une machine.
        </CardDescription>
      </CardHeader>
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
