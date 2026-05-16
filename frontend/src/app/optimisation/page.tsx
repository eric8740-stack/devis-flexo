"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  getOptionsDisponibles,
  postOptimisationCalculer,
  type OptimisationCalculerResponse,
  type OptimisationConfigOut,
  type OptionDisponible,
} from "@/lib/api";

/**
 * Simulateur d'optimisation Sprint 13 S13.D (frontend).
 *
 * Page standalone /optimisation : saisie format/couleurs/options + appel
 * POST /api/optimisation/calculer + affichage top 3.
 *
 * Note : le brief mentionne /devis/[id]/optimisation, mais le modèle
 * Devis actuel ne porte pas tous les champs requis (rayon_angles_mm,
 * forme_courbe, contrainte_client). Le rattachement à un devis sauvé
 * arrivera Sprint 14 quand le modèle Devis sera étendu. Pour l'instant
 * cette page est un OUTIL DE SIMULATION standalone : l'utilisateur
 * obtient le top 3 sans devoir d'abord sauver un devis.
 */
export default function OptimisationPage() {
  const { toast } = useToast();

  // Options réellement disponibles pour le tenant (table option_fabrication,
  // scope tenant + catalogue global). Évite le 422 "Option inconnue" qui
  // arrivait quand on listait le catalogue master mais que l'onboarding du
  // tenant n'en avait seedé qu'une partie.
  const [options, setOptions] = useState<OptionDisponible[] | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<Set<string>>(
    new Set()
  );

  // Form state
  const [hauteur, setHauteur] = useState<string>("30");
  const [largeur, setLargeur] = useState<string>("30");
  const [rayonAngles, setRayonAngles] = useState<string>("2");
  const [formeCourbe, setFormeCourbe] = useState(false);
  const [intervalleDevMin, setIntervalleDevMin] = useState<string>("2");
  const [nbCouleurs, setNbCouleurs] = useState<string>("4");
  const [quantite, setQuantite] = useState<string>("10000");
  const [contrainteClientMm, setContrainteClientMm] = useState<string>("0");
  const [matiereTransparente, setMatiereTransparente] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [response, setResponse] = useState<OptimisationCalculerResponse | null>(
    null
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await getOptionsDisponibles();
        if (!cancelled) setOptions(list);
      } catch (err) {
        toast({
          title: "Chargement options impossible",
          description:
            err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [toast]);

  const optionsByCategorie = useMemo(() => {
    if (!options) return {};
    const out: Record<string, OptionDisponible[]> = {};
    for (const o of options) {
      const cat = o.categorie ?? "Autres";
      if (!out[cat]) out[cat] = [];
      out[cat].push(o);
    }
    return out;
  }, [options]);

  const toggleOption = (code: string) => {
    setSelectedOptions((s) => {
      const next = new Set(s);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setResponse(null);
    try {
      const r = await postOptimisationCalculer({
        format: {
          hauteur_mm: parseFloat(hauteur),
          largeur_mm: parseFloat(largeur),
          rayon_angles_mm: parseFloat(rayonAngles),
          forme_courbe: formeCourbe,
        },
        intervalle_dev_min_mm: parseFloat(intervalleDevMin),
        nb_couleurs_impression: parseInt(nbCouleurs, 10),
        quantite: parseInt(quantite, 10),
        matiere_est_transparente: matiereTransparente,
        options_codes: Array.from(selectedOptions),
        contrainte_client: {
          intervalle_dev_min_mm: parseFloat(contrainteClientMm),
        },
      });
      setResponse(r);
      if (r.nb_candidats === 0) {
        toast({
          title: "Aucune configuration viable",
          description:
            r.message_filtrage ??
            "Tous les filtres ont éliminé les configurations.",
          variant: "destructive",
        });
      }
    } catch (err) {
      toast({
        title: "Calcul impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold">Optimisation de pose</h1>
        <p className="text-sm text-muted-foreground">
          Saisissez le contexte du devis et lancez le moteur. Le top 3
          configurations (cylindre × machine × variante) ressort en quelques
          secondes, scoré selon les 6 règles métier ICE.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-2">
        {/* --- Colonne 1 : Format + impression --- */}
        <Card>
          <CardHeader>
            <CardTitle>Format & impression</CardTitle>
            <CardDescription>
              Dimensions étiquette, rayon des angles, couleurs.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="hauteur">Hauteur (dev) — mm</Label>
                <Input
                  id="hauteur"
                  type="number"
                  step="0.1"
                  min={1}
                  value={hauteur}
                  onChange={(e) => setHauteur(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="largeur">Largeur (laize) — mm</Label>
                <Input
                  id="largeur"
                  type="number"
                  step="0.1"
                  min={1}
                  value={largeur}
                  onChange={(e) => setLargeur(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="rayon">Rayon angles — mm</Label>
                <Input
                  id="rayon"
                  type="number"
                  step="0.5"
                  min={0}
                  value={rayonAngles}
                  onChange={(e) => setRayonAngles(e.target.value)}
                />
              </div>
              <div className="flex items-end space-y-2">
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={formeCourbe}
                    onChange={(e) => setFormeCourbe(e.target.checked)}
                    className="h-4 w-4 accent-foreground"
                  />
                  Forme courbe (rond / ovale)
                </label>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="nbcouleurs">Nb couleurs impression</Label>
                <Input
                  id="nbcouleurs"
                  type="number"
                  min={0}
                  max={16}
                  value={nbCouleurs}
                  onChange={(e) => setNbCouleurs(e.target.value)}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  CMJN + Pantone + spot
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="quantite">Quantité</Label>
                <Input
                  id="quantite"
                  type="number"
                  min={1}
                  value={quantite}
                  onChange={(e) => setQuantite(e.target.value)}
                  required
                />
              </div>
            </div>
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={matiereTransparente}
                onChange={(e) => setMatiereTransparente(e.target.checked)}
                className="h-4 w-4 accent-foreground"
              />
              Matière transparente (déclenche spot détection verso)
            </label>
          </CardContent>
        </Card>

        {/* --- Colonne 2 : Contraintes --- */}
        <Card>
          <CardHeader>
            <CardTitle>Contraintes</CardTitle>
            <CardDescription>
              Intervalles minimum imprimerie et client final.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="idmin">
                Intervalle dev min — imprimerie (mm)
              </Label>
              <Input
                id="idmin"
                type="number"
                step="0.1"
                min={0}
                value={intervalleDevMin}
                onChange={(e) => setIntervalleDevMin(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                Typiquement 2 mm (paramètre entreprise).
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="ccmin">
                Intervalle dev min — machine de pose client (mm)
              </Label>
              <Input
                id="ccmin"
                type="number"
                step="0.1"
                min={0}
                value={contrainteClientMm}
                onChange={(e) => setContrainteClientMm(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                0 si pas de contrainte spécifique. Sinon, on prend le MAX
                des deux comme minimum effectif.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* --- Options de fabrication --- */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Options de fabrication</CardTitle>
            <CardDescription>
              Les coefs vitesse/gâche et modules requis seront appliqués
              automatiquement. Décocher si non utilisé.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {options === null && (
              <p className="text-sm text-muted-foreground">
                Chargement…
              </p>
            )}
            {options !== null && options.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Aucune option configurée. Lance l&apos;onboarding express
                depuis Paramètres pour activer ton catalogue.
              </p>
            )}
            {options !== null &&
              options.length > 0 &&
              Object.entries(optionsByCategorie).map(([cat, opts]) => (
                <section key={cat}>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {cat}
                  </h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {opts.map((o) => (
                      <label
                        key={o.code}
                        htmlFor={`opt-${o.code}`}
                        className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-2 text-sm hover:bg-muted/50"
                      >
                        <input
                          id={`opt-${o.code}`}
                          type="checkbox"
                          checked={selectedOptions.has(o.code)}
                          onChange={() => toggleOption(o.code)}
                          className="mt-0.5 h-4 w-4 cursor-pointer accent-foreground"
                        />
                        <div className="flex-1">
                          <div className="font-medium">{o.libelle}</div>
                          <div className="text-xs text-muted-foreground">
                            vit ×{o.coef_vitesse_impact} • gâche ×
                            {o.coef_gache_impact}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </section>
              ))}
          </CardContent>
        </Card>

        <div className="lg:col-span-2">
          <Button
            type="submit"
            disabled={submitting}
            className="w-full sm:w-auto"
          >
            {submitting ? "Calcul en cours…" : "Calculer le top 3"}
          </Button>
        </div>
      </form>

      {response && <ResultsSection response={response} />}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Section résultats
// ---------------------------------------------------------------------------

function ResultsSection({
  response,
}: {
  response: OptimisationCalculerResponse;
}) {
  return (
    <section className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h2 className="text-xl font-bold">
          Top {response.nb_candidats} configuration(s)
        </h2>
        <span className="text-sm text-muted-foreground">
          Intervalle dev min appliqué :{" "}
          <strong>{response.intervalle_dev_min_applique_mm} mm</strong>
        </span>
      </header>

      {response.message_contrainte_client && (
        <div className="rounded-md border border-blue-300 bg-blue-50 p-3 text-sm text-blue-900">
          {response.message_contrainte_client}
        </div>
      )}

      {response.message_filtrage && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          {response.message_filtrage}
        </div>
      )}

      {response.nb_candidats === 0 ? (
        <p className="text-sm text-muted-foreground">
          Aucune configuration viable. Élargissez le parc machines/cylindres,
          ou retirez des options qui exigent des modules absents.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {response.configurations.map((c, idx) => (
            <ConfigCard key={`${c.cylindre_id}-${c.machine_id}-${idx}`} config={c} rank={idx + 1} />
          ))}
        </div>
      )}
    </section>
  );
}

function ConfigCard({
  config,
  rank,
}: {
  config: OptimisationConfigOut;
  rank: number;
}) {
  const qualiteColor: Record<string, string> = {
    parfait: "bg-emerald-100 text-emerald-900",
    bien: "bg-lime-100 text-lime-900",
    complique: "bg-amber-100 text-amber-900",
    mauvais: "bg-orange-100 text-orange-900",
    critique: "bg-red-100 text-red-900",
    inconnu: "bg-gray-100 text-gray-900",
  };
  const color = qualiteColor[config.qualite_echenillage] ?? "bg-gray-100";

  return (
    <Card className={rank === 1 ? "border-2 border-foreground" : ""}>
      <CardHeader>
        <div className="flex items-baseline justify-between">
          <CardTitle className="text-lg">#{rank}</CardTitle>
          <span
            className={`rounded px-2 py-0.5 text-xs font-medium ${color}`}
          >
            {config.qualite_echenillage}
          </span>
        </div>
        <CardDescription>
          Score : <strong>{config.score.toFixed(1)}</strong>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <Line label="Cylindre" value={`#${config.cylindre_id}`} />
        <Line label="Machine" value={`#${config.machine_id}`} />
        <Line
          label="Poses"
          value={`${config.nb_poses_dev} × ${config.nb_poses_laize} = ${config.nb_poses_total}`}
        />
        <Line
          label="Intervalle dev"
          value={`${config.intervalle_dev_reel_mm} mm`}
        />
        <Line
          label="Intervalle laize"
          value={`${config.intervalle_laize_reel_mm} mm`}
        />
        <Line
          label="Largeur plaque"
          value={`${config.largeur_plaque_mm} mm (Z mini ${config.z_mini_effet_banane} mm)`}
        />
        {config.consolidation_atteinte && (
          <div className="rounded bg-emerald-50 px-2 py-1 text-xs text-emerald-900">
            ✓ Consolidation atteinte
          </div>
        )}
        <hr className="border-border" />
        <div className="space-y-1 text-xs text-muted-foreground">
          <Line
            label="Coef vitesse final"
            value={config.coef_vitesse_final.toFixed(3)}
            muted
          />
          <Line
            label="Coef gâche final"
            value={config.coef_gache_final.toFixed(3)}
            muted
          />
          <Line
            label="…dont confort rayon"
            value={`×${config.coef_confort_rayon.toFixed(2)}`}
            muted
          />
          <Line
            label="…dont options"
            value={`vit ×${config.coef_vitesse_options.toFixed(2)} / gâche ×${config.coef_gache_options.toFixed(2)}`}
            muted
          />
        </div>
      </CardContent>
    </Card>
  );
}

function Line({
  label,
  value,
  muted = false,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className={muted ? "" : "text-muted-foreground"}>{label}</span>
      <span className={muted ? "" : "font-medium"}>{value}</span>
    </div>
  );
}
