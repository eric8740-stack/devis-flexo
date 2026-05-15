"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { IAPhotoAuthenticated } from "@/components/ia/IAPhotoAuthenticated";
import { useToast } from "@/hooks/use-toast";
import {
  deleteIAAnalyse,
  listIAAnalyses,
  type IAAnalyseListItem,
  type IAAnalyseListResponse,
} from "@/lib/api";

const PAGE_SIZE = 20;

/**
 * Historique des analyses photo (feat-historique-analyses).
 *
 * Liste paginée des analyses du tenant courant, triée created_at DESC.
 * Chaque card : thumbnail authentifiée + métadonnées + boutons Voir / Supprimer.
 *
 * État vide explicite avec CTA vers /ia/analyser-photo.
 */
export default function AnalysesHistoriquePage() {
  const { toast } = useToast();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<IAAnalyseListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = async (p: number) => {
    setLoading(true);
    try {
      const r = await listIAAnalyses(p, PAGE_SIZE);
      setData(r);
    } catch (err) {
      toast({
        title: "Chargement impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleDelete = async (id: number) => {
    if (
      !window.confirm(
        "Supprimer cette analyse ? La photo et les résultats seront perdus définitivement."
      )
    ) {
      return;
    }
    setDeletingId(id);
    try {
      await deleteIAAnalyse(id);
      toast({ title: "Analyse supprimée" });
      // Reload current page — si on supprime la dernière entrée d'une
      // page > 1, on recule d'une page.
      const remaining = (data?.items.length ?? 1) - 1;
      if (remaining === 0 && page > 1) {
        setPage(page - 1);
      } else {
        await load(page);
      }
    } catch (err) {
      toast({
        title: "Suppression impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setDeletingId(null);
    }
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="flex items-baseline justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Historique des analyses</h1>
          <p className="text-sm text-muted-foreground">
            Toutes les analyses photo passées de votre entreprise.
          </p>
        </div>
        <Link href="/ia/analyser-photo">
          <Button>+ Nouvelle analyse</Button>
        </Link>
      </header>

      {loading && (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      )}

      {!loading && data && data.total === 0 && (
        <EmptyState />
      )}

      {!loading && data && data.total > 0 && (
        <>
          <div className="space-y-3">
            {data.items.map((item) => (
              <AnalyseListItemCard
                key={item.id}
                item={item}
                onDelete={() => handleDelete(item.id)}
                deleting={deletingId === item.id}
              />
            ))}
          </div>

          {totalPages > 1 && (
            <Pagination
              page={page}
              totalPages={totalPages}
              onPrev={() => setPage((p) => Math.max(1, p - 1))}
              onNext={() => setPage((p) => Math.min(totalPages, p + 1))}
            />
          )}
        </>
      )}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Composants
// ---------------------------------------------------------------------------

function EmptyState() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Aucune analyse pour le moment</CardTitle>
        <CardDescription>
          Lancez votre première analyse photo pour estimer rapidement les
          couleurs et techniques d&apos;une étiquette client existante.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Link href="/ia/analyser-photo">
          <Button>+ Première analyse</Button>
        </Link>
      </CardContent>
    </Card>
  );
}

function AnalyseListItemCard({
  item,
  onDelete,
  deleting,
}: {
  item: IAAnalyseListItem;
  onDelete: () => void;
  deleting: boolean;
}) {
  const confianceColor: Record<string, string> = {
    haut: "bg-emerald-100 text-emerald-900",
    moyen: "bg-amber-100 text-amber-900",
    faible: "bg-red-100 text-red-900",
  };
  const badge = item.niveau_confiance
    ? confianceColor[item.niveau_confiance] ?? "bg-gray-100"
    : "bg-gray-100";

  return (
    <Card className="flex items-center gap-4 p-3">
      <IAPhotoAuthenticated
        imageKey={item.image_key}
        alt={item.image_filename ?? `Analyse #${item.id}`}
        className="h-20 w-20 flex-shrink-0 rounded-md border border-border object-cover"
      />
      <div className="flex-1 space-y-1 text-sm">
        <div className="font-medium">
          {item.image_filename ?? `Analyse #${item.id}`}
        </div>
        <div className="text-xs text-muted-foreground">
          {formatRelativeDate(item.created_at)}
          {item.nombre_couleurs_distinctes != null && (
            <> · {item.nombre_couleurs_distinctes} couleur(s) détectée(s)</>
          )}
        </div>
        <div className="flex items-center gap-2">
          {item.niveau_confiance && (
            <span
              className={`rounded px-2 py-0.5 text-xs font-medium ${badge}`}
            >
              Confiance : {item.niveau_confiance}
            </span>
          )}
          {item.erreur && (
            <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-900">
              Échec analyse
            </span>
          )}
        </div>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Link href={`/ia/analyses/${item.id}`}>
          <Button variant="outline" size="sm">
            Voir
          </Button>
        </Link>
        <Button
          variant="outline"
          size="sm"
          onClick={onDelete}
          disabled={deleting}
          className="text-red-700 hover:bg-red-50"
        >
          {deleting ? "Suppression…" : "Supprimer"}
        </Button>
      </div>
    </Card>
  );
}

function Pagination({
  page,
  totalPages,
  onPrev,
  onNext,
}: {
  page: number;
  totalPages: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div className="flex items-center justify-between border-t border-border pt-4">
      <Button
        variant="outline"
        size="sm"
        onClick={onPrev}
        disabled={page <= 1}
      >
        ← Précédent
      </Button>
      <span className="text-sm text-muted-foreground">
        Page {page} / {totalPages}
      </span>
      <Button
        variant="outline"
        size="sm"
        onClick={onNext}
        disabled={page >= totalPages}
      >
        Suivant →
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRelativeDate(iso: string): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return "à l'instant";
  if (min < 60) return `il y a ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `il y a ${h} h`;
  const j = Math.floor(h / 24);
  if (j < 30) return `il y a ${j} j`;
  return date.toLocaleDateString("fr-FR");
}
