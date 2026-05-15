"use client";

import { useState, type ChangeEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  postIAAnalyserPhoto,
  type IAAnalysePhotoResponse,
  type IACouleurDetectee,
} from "@/lib/api";

/**
 * Page POC FlexoCheck — Sprint 13 S13.E.4.
 *
 * UX simple : zone d'upload photo, aperçu, bouton "Analyser", affichage
 * des résultats Claude (couleurs détectées + swatches RGB, techniques,
 * matière estimée, niveau de confiance, limites de l'analyse).
 *
 * Convention CdC § 1930 : c'est une ESTIMATION PRÉLIMINAIRE, pas une
 * analyse colorimétrique calibrée. Le BAT reste obligatoire avant
 * production. On affiche un avertissement clair sur la page.
 */

const MIME_TYPES_AUTORISES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
];

const MAX_TAILLE_MO = 10;

export default function AnalyserPhotoPage() {
  const { toast } = useToast();

  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resultat, setResultat] = useState<IAAnalysePhotoResponse | null>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!MIME_TYPES_AUTORISES.includes(f.type)) {
      toast({
        title: "Format non supporté",
        description: `${f.type}. Autorisés : JPEG, PNG, WebP, GIF.`,
        variant: "destructive",
      });
      return;
    }
    if (f.size > MAX_TAILLE_MO * 1024 * 1024) {
      toast({
        title: "Image trop grande",
        description: `Max ${MAX_TAILLE_MO} Mo. Compressez ou redimensionnez.`,
        variant: "destructive",
      });
      return;
    }
    setFile(f);
    setResultat(null);
    // Aperçu local sans upload
    const url = URL.createObjectURL(f);
    setPreviewUrl(url);
  };

  const handleAnalyser = async () => {
    if (!file) return;
    setSubmitting(true);
    try {
      const dataUrl = await readFileAsDataUrl(file);
      const res = await postIAAnalyserPhoto({
        image_base64: dataUrl,
        mime_type: file.type,
      });
      setResultat(res);
      toast({
        title: "Analyse terminée",
        description: `${res.nombre_couleurs_distinctes ?? "?"} couleur(s) détectée(s) — confiance ${res.niveau_confiance}.`,
      });
    } catch (err) {
      toast({
        title: "Analyse impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold">Analyser une photo d&apos;étiquette</h1>
        <p className="text-sm text-muted-foreground">
          Estimation rapide nb couleurs + techniques + matière via Claude API
          multimodal. <strong>Estimation préliminaire uniquement</strong> — le
          BAT reste obligatoire avant production.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>1. Charger une photo</CardTitle>
          <CardDescription>
            JPEG, PNG, WebP ou GIF — max {MAX_TAILLE_MO} Mo.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <input
            type="file"
            accept={MIME_TYPES_AUTORISES.join(",")}
            onChange={handleFileChange}
            className="block w-full text-sm file:mr-4 file:rounded-md file:border-0 file:bg-foreground file:px-4 file:py-2 file:text-sm file:font-medium file:text-background hover:file:bg-foreground/80"
          />

          {previewUrl && (
            <div className="space-y-3">
              <div className="relative aspect-video w-full max-w-md overflow-hidden rounded-md border border-border bg-muted">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={previewUrl}
                  alt="Aperçu de l'étiquette à analyser"
                  className="h-full w-full object-contain"
                />
              </div>
              <Button onClick={handleAnalyser} disabled={submitting}>
                {submitting ? "Analyse en cours…" : "Analyser cette photo"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {resultat && <ResultatsSection resultat={resultat} />}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") resolve(reader.result);
      else reject(new Error("FileReader n'a pas retourné de string"));
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

// ---------------------------------------------------------------------------
// Section résultats
// ---------------------------------------------------------------------------

function ResultatsSection({
  resultat,
}: {
  resultat: IAAnalysePhotoResponse;
}) {
  const r = resultat.resultats_ia;
  const confianceColor: Record<string, string> = {
    haut: "bg-emerald-100 text-emerald-900",
    moyen: "bg-amber-100 text-amber-900",
    faible: "bg-red-100 text-red-900",
  };

  return (
    <section className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h2 className="text-xl font-bold">2. Résultats Claude</h2>
        <span
          className={`rounded px-2 py-1 text-xs font-medium ${confianceColor[r.niveau_confiance] ?? "bg-gray-100"}`}
        >
          Confiance : {r.niveau_confiance}
        </span>
      </header>

      {/* Couleurs détectées */}
      <Card>
        <CardHeader>
          <CardTitle>
            Couleurs détectées ({r.nombre_couleurs_distinctes})
          </CardTitle>
          <CardDescription>
            Min technique flexo : <strong>{r.couleurs_min_technique}</strong>{" "}
            stations · Max si toutes finitions visibles :{" "}
            <strong>{r.couleurs_max_technique}</strong>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            {r.couleurs_detectees.map((c, i) => (
              <CouleurCard key={i} couleur={c} />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Techniques et finitions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Techniques d&apos;impression</CardTitle>
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

      {/* Matière */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Matière estimée</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 sm:grid-cols-3 text-sm">
          <KV label="Type" value={r.matiere_estimee.type} />
          <KV label="Couleur" value={r.matiere_estimee.couleur} />
          <KV
            label="Finition"
            value={r.matiere_estimee.finition_apparente}
          />
          {r.presence_blanc_opaque && (
            <div className="sm:col-span-3 rounded bg-amber-50 px-2 py-1 text-xs text-amber-900">
              ⚠ Blanc opaque détecté derrière les couleurs (matière transparente +
              spot détection verso recommandé pour le moteur d&apos;optimisation).
            </div>
          )}
        </CardContent>
      </Card>

      {/* Limites */}
      {r.limites_analyse.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Limites de cette analyse
            </CardTitle>
            <CardDescription>
              À garder en tête avant de pré-remplir un devis.
            </CardDescription>
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

      <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
        <strong>Rappel :</strong> ce n&apos;est PAS une analyse colorimétrique
        calibrée. Les valeurs Pantone exactes requièrent un spectrophotomètre.
        Le BAT (Bon à Tirer) client reste obligatoire avant production.
      </div>

      <footer className="text-xs text-muted-foreground">
        Analyse #{resultat.id} · {resultat.model_utilise} ·{" "}
        {new Date(resultat.created_at).toLocaleString("fr-FR")}
      </footer>
    </section>
  );
}

function CouleurCard({ couleur }: { couleur: IACouleurDetectee }) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-border p-3">
      <div
        className="h-12 w-12 flex-shrink-0 rounded-md border border-border"
        style={{ backgroundColor: couleur.rgb_approximatif }}
        title={couleur.rgb_approximatif}
      />
      <div className="flex-1 space-y-0.5 text-sm">
        <div className="font-mono">{couleur.rgb_approximatif}</div>
        {couleur.pantone_proche_estime && (
          <div className="text-xs text-muted-foreground">
            ≈ {couleur.pantone_proche_estime}
          </div>
        )}
        <div className="text-xs text-muted-foreground">
          {couleur.surface_pct}% de la surface
        </div>
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
