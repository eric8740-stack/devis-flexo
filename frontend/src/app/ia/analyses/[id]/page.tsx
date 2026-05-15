"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
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
  getIAAnalyse,
  type IAAnalyseDetail,
  type IACouleurDetectee,
} from "@/lib/api";

/**
 * Détail d'une analyse passée (feat-historique-analyses).
 *
 * Sections :
 *   1. Photo originale (servie auth via /api/ia/photos/{key})
 *   2. Résultats Claude — couleurs détectées + override réserve papier
 *      (réutilise la logique du fix-analyseur-photo)
 *   3. Techniques + finitions + matière + limites
 *   4. Actions : supprimer + (placeholder "Créer un devis depuis cette
 *      analyse" grisé, Phase 2)
 */
export default function AnalyseDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { toast } = useToast();

  const idRaw = params?.id;
  const id = typeof idRaw === "string" ? parseInt(idRaw, 10) : NaN;

  const [analyse, setAnalyse] = useState<IAAnalyseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // State overrides "réserve papier vs encre blanche" — partagé avec
  // /ia/analyser-photo (fix-analyseur-photo) pour cohérence UX.
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const toggleOverride = (hex: string) =>
    setOverrides((prev) => ({ ...prev, [hex]: !prev[hex] }));

  useEffect(() => {
    if (isNaN(id)) {
      setNotFound(true);
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await getIAAnalyse(id);
        if (!cancelled) setAnalyse(r);
      } catch (err) {
        if (cancelled) return;
        // 404 backend → tenant cross ou id inconnu
        if (
          err instanceof Error &&
          err.message.includes("404")
        ) {
          setNotFound(true);
        } else {
          toast({
            title: "Chargement impossible",
            description:
              err instanceof Error ? err.message : "Erreur inconnue",
            variant: "destructive",
          });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, toast]);

  const handleDelete = async () => {
    if (!analyse) return;
    if (
      !window.confirm(
        "Supprimer cette analyse ? La photo et les résultats seront perdus définitivement."
      )
    ) {
      return;
    }
    setDeleting(true);
    try {
      await deleteIAAnalyse(analyse.id);
      toast({ title: "Analyse supprimée" });
      router.push("/ia/analyses");
    } catch (err) {
      toast({
        title: "Suppression impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-5xl p-6 text-sm text-muted-foreground">
        Chargement…
      </main>
    );
  }

  if (notFound || !analyse) {
    return (
      <main className="mx-auto max-w-5xl space-y-4 p-6">
        <h1 className="text-2xl font-bold">Analyse introuvable</h1>
        <p className="text-sm text-muted-foreground">
          Cette analyse n&apos;existe pas ou ne vous appartient pas.
        </p>
        <Link href="/ia/analyses">
          <Button variant="outline">← Retour à l&apos;historique</Button>
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="flex items-baseline justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">
            {analyse.image_filename ?? `Analyse #${analyse.id}`}
          </h1>
          <p className="text-sm text-muted-foreground">
            {new Date(analyse.created_at).toLocaleString("fr-FR")} ·{" "}
            {analyse.model_utilise}
            {analyse.image_size_bytes != null && analyse.image_size_bytes > 0 && (
              <> · {formatBytes(analyse.image_size_bytes)}</>
            )}
          </p>
        </div>
        <Link href="/ia/analyses">
          <Button variant="outline" size="sm">
            ← Retour
          </Button>
        </Link>
      </header>

      {/* --- Photo originale --- */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Photo originale</CardTitle>
        </CardHeader>
        <CardContent>
          <IAPhotoAuthenticated
            imageKey={analyse.image_key}
            alt={analyse.image_filename ?? `Analyse ${analyse.id}`}
            className="max-h-[60vh] w-full rounded-md border border-border object-contain"
          />
        </CardContent>
      </Card>

      {analyse.erreur && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
          <strong>Échec de l&apos;analyse :</strong> {analyse.erreur}
        </div>
      )}

      {/* --- Résultats Claude (réutilise structure /ia/analyser-photo) --- */}
      {!analyse.erreur && (
        <ResultatsBlock analyse={analyse} overrides={overrides} toggleOverride={toggleOverride} />
      )}

      {/* --- Actions --- */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <Button
          variant="outline"
          disabled
          title="Bientôt disponible"
          className="cursor-not-allowed opacity-60"
        >
          Créer un devis depuis cette analyse (bientôt)
        </Button>
        <Button
          variant="outline"
          onClick={handleDelete}
          disabled={deleting}
          className="text-red-700 hover:bg-red-50"
        >
          {deleting ? "Suppression…" : "Supprimer cette analyse"}
        </Button>
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Bloc résultats (réutilise la structure ResultatsSection de /analyser-photo)
// ---------------------------------------------------------------------------

function ResultatsBlock({
  analyse,
  overrides,
  toggleOverride,
}: {
  analyse: IAAnalyseDetail;
  overrides: Record<string, boolean>;
  toggleOverride: (hex: string) => void;
}) {
  const r = analyse.resultats_ia;
  const confianceColor: Record<string, string> = {
    haut: "bg-emerald-100 text-emerald-900",
    moyen: "bg-amber-100 text-amber-900",
    faible: "bg-red-100 text-red-900",
  };

  const nbOverridesEncre = r.couleurs_detectees.filter(
    (c) => Boolean(c.support_reserve) && overrides[c.rgb_approximatif],
  ).length;
  const minStations = r.couleurs_min_technique + nbOverridesEncre;
  const maxStations = r.couleurs_max_technique + nbOverridesEncre;

  return (
    <section className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h2 className="text-xl font-bold">Résultats Claude</h2>
        <span
          className={`rounded px-2 py-1 text-xs font-medium ${confianceColor[r.niveau_confiance] ?? "bg-gray-100"}`}
        >
          Confiance : {r.niveau_confiance}
        </span>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>
            Couleurs détectées ({r.couleurs_detectees.length})
          </CardTitle>
          <CardDescription>
            Min technique flexo : <strong>{minStations}</strong> stations ·
            Max si toutes finitions visibles :{" "}
            <strong>{maxStations}</strong>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            {r.couleurs_detectees.map((c, i) => {
              const isReserve = Boolean(c.support_reserve);
              const isOverridden =
                isReserve && Boolean(overrides[c.rgb_approximatif]);
              return (
                <CouleurMini
                  key={i}
                  couleur={c}
                  isReserve={isReserve}
                  isOverridden={isOverridden}
                  onToggle={
                    isReserve
                      ? () => toggleOverride(c.rgb_approximatif)
                      : undefined
                  }
                />
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Techniques d&apos;impression
            </CardTitle>
          </CardHeader>
          <CardContent>
            {r.techniques_impression_estimees.length === 0 ? (
              <p className="text-sm text-muted-foreground">Aucune détectée.</p>
            ) : (
              <ul className="space-y-1">
                {r.techniques_impression_estimees.map((t) => (
                  <li key={t} className="text-sm">
                    • {t}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Finitions visibles</CardTitle>
          </CardHeader>
          <CardContent>
            {r.finitions_visibles.length === 0 ? (
              <p className="text-sm text-muted-foreground">Aucune visible.</p>
            ) : (
              <ul className="space-y-1">
                {r.finitions_visibles.map((f) => (
                  <li key={f} className="text-sm">
                    • {f}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Matière estimée</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm sm:grid-cols-3">
          <KV label="Type" value={r.matiere_estimee.type} />
          <KV label="Couleur" value={r.matiere_estimee.couleur} />
          <KV label="Finition" value={r.matiere_estimee.finition_apparente} />
          {r.presence_blanc_opaque && (
            <div className="rounded bg-amber-50 px-2 py-1 text-xs text-amber-900 sm:col-span-3">
              ⚠ Blanc opaque détecté derrière les couleurs (matière transparente
              + spot détection verso recommandé pour le moteur d&apos;optimisation).
            </div>
          )}
        </CardContent>
      </Card>

      {r.limites_analyse.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Limites de cette analyse</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {r.limites_analyse.map((l, i) => (
                <li key={i} className="text-muted-foreground">
                  • {l}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </section>
  );
}

function CouleurMini({
  couleur,
  isReserve,
  isOverridden,
  onToggle,
}: {
  couleur: IACouleurDetectee;
  isReserve: boolean;
  isOverridden: boolean;
  onToggle?: () => void;
}) {
  const showBadgeReserve = isReserve && !isOverridden;
  const showBadgeEncre = isReserve && isOverridden;
  return (
    <div className="flex items-start gap-3 rounded-md border border-border p-3">
      <div
        className="h-12 w-12 flex-shrink-0 rounded-md border border-border"
        style={{ backgroundColor: couleur.rgb_approximatif }}
        title={couleur.rgb_approximatif}
      />
      <div className="flex-1 space-y-1 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono">{couleur.rgb_approximatif}</span>
          {showBadgeReserve && (
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-600">
              Réserve papier
            </span>
          )}
          {showBadgeEncre && (
            <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-800">
              Encre blanche d&apos;opacité
            </span>
          )}
        </div>
        {couleur.pantone_proche_estime && (
          <div className="text-xs text-muted-foreground">
            ≈ {couleur.pantone_proche_estime}
          </div>
        )}
        <div className="text-xs text-muted-foreground">
          {couleur.surface_pct}% de la surface
        </div>
        {onToggle && (
          <button
            type="button"
            onClick={onToggle}
            className="text-xs font-medium text-blue-600 hover:underline"
          >
            {isOverridden
              ? "Considérer comme réserve papier"
              : "Considérer comme encre blanche"}
          </button>
        )}
      </div>
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="font-medium">{value}</div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Kio`;
  return `${(bytes / 1024 / 1024).toFixed(1)} Mio`;
}
