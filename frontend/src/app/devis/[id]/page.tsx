"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DevisResult } from "@/components/DevisResult";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  deleteDevis,
  duplicateDevis,
  getDevisDetail,
  type DevisCalculResult,
  type DevisDetail,
} from "@/lib/api";

const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

const STATUT_LABEL: Record<string, string> = {
  brouillon: "Brouillon",
  valide: "Valide",
};

export default function DevisDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { toast } = useToast();
  const id = Number(params.id);

  const [devis, setDevis] = useState<DevisDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setError("ID de devis invalide");
      return;
    }
    getDevisDetail(id)
      .then(setDevis)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  const handleDuplicate = async () => {
    setActionLoading(true);
    try {
      const nouveau = await duplicateDevis(id);
      toast({
        title: "Devis dupliqué",
        description: `Nouveau devis « ${nouveau.numero} » créé en brouillon.`,
      });
      router.push(`/devis/${nouveau.id}`);
    } catch (err) {
      toast({
        title: "Erreur duplication",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    setActionLoading(true);
    try {
      await deleteDevis(id);
      toast({
        title: "Devis supprimé",
        description: `« ${devis?.numero} » a été supprimé.`,
      });
      router.push("/devis");
    } catch (err) {
      toast({
        title: "Erreur suppression",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
      setActionLoading(false);
    }
  };

  if (error) {
    return (
      <main className="container mx-auto max-w-5xl p-4 sm:p-8">
        <div
          role="alert"
          className="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive"
        >
          <strong>Erreur :</strong> {error}
        </div>
        <div className="mt-4">
          <Button asChild variant="outline">
            <Link href="/devis">↩ Retour à la liste</Link>
          </Button>
        </div>
      </main>
    );
  }

  if (!devis) {
    return (
      <main className="container mx-auto max-w-5xl p-4 sm:p-8">
        <div className="text-sm text-muted-foreground">Chargement…</div>
      </main>
    );
  }

  // Le payload_output stocké est exactement la sortie /api/cost/calculer →
  // on peut le passer tel quel à DevisResult (Union DevisOutput | DevisOutputMatching).
  const calculResult = devis.payload_output as unknown as DevisCalculResult;
  const inputResume = devis.payload_input as Record<string, unknown>;

  return (
    <main className="container mx-auto max-w-5xl p-4 sm:p-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold font-mono">
              {devis.numero}
            </h1>
            <span
              className={`rounded-full px-2 py-1 text-xs font-medium ${
                devis.statut === "valide"
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-amber-100 text-amber-800"
              }`}
            >
              {STATUT_LABEL[devis.statut] ?? devis.statut}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Créé le {fmtDateTime(devis.date_creation)} · modifié le{" "}
            {fmtDateTime(devis.date_modification)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/devis">↩ Liste</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/devis/${devis.id}/pdf`}
              download={`${devis.numero}.pdf`}
            >
              📄 Télécharger PDF
            </a>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href={`/devis/${devis.id}/edit`}>✏️ Modifier</Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDuplicate}
            disabled={actionLoading}
          >
            🗎 Dupliquer
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                disabled={actionLoading}
              >
                🗑 Supprimer
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Supprimer ce devis ?</AlertDialogTitle>
                <AlertDialogDescription>
                  Le devis <strong>{devis.numero}</strong> sera définitivement
                  supprimé. Cette action est irréversible.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Annuler</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  Supprimer
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </header>

      <div className="grid gap-6">
        {devis.client_nom && (
          <Card>
            <CardHeader>
              <CardTitle>Client</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              <strong>{devis.client_nom}</strong>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Spécifications</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
              <div>
                <span className="text-muted-foreground">Format :</span>{" "}
                <span className="font-mono">
                  {parseFloat(devis.format_l_mm)} ×{" "}
                  {parseFloat(devis.format_h_mm)} mm
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Machine :</span>{" "}
                {devis.machine_nom}
              </div>
              <div>
                <span className="text-muted-foreground">Mode :</span>{" "}
                {devis.mode_calcul === "matching"
                  ? "Matching cylindres"
                  : "Manuel"}
              </div>
              {devis.mode_calcul === "matching" &&
                devis.cylindre_choisi_z !== null && (
                  <div>
                    <span className="text-muted-foreground">
                      Cylindre choisi :
                    </span>{" "}
                    <span className="font-mono">
                      Z={devis.cylindre_choisi_z},{" "}
                      {devis.cylindre_choisi_nb_etiq} étiq/tour
                    </span>
                  </div>
                )}
              {devis.mode_calcul === "manuel" &&
                inputResume.intervalle_mm !== undefined &&
                inputResume.intervalle_mm !== null && (
                  <div>
                    <span className="text-muted-foreground">
                      Intervalle étiquettes :
                    </span>{" "}
                    <span className="font-mono">
                      {String(inputResume.intervalle_mm)} mm
                    </span>
                  </div>
                )}
              {typeof inputResume.ml_total === "number" && (
                <div>
                  <span className="text-muted-foreground">Tirage :</span>{" "}
                  {inputResume.ml_total} m linéaires
                </div>
              )}
              {typeof inputResume.laize_utile_mm === "number" && (
                <div>
                  <span className="text-muted-foreground">Laize utile :</span>{" "}
                  {inputResume.laize_utile_mm} mm
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <DevisResult data={calculResult} />
      </div>
    </main>
  );
}
