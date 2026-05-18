"use client";

import Image from "next/image";
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
import { SchemaImplantation } from "@/components/SchemaImplantation";
import { useToast } from "@/hooks/use-toast";
import {
  getOptionsDisponibles,
  postOptimisationCalculer,
  type OptimisationCalculerResponse,
  type OptimisationConfigOut,
  type OptionDisponible,
  type SensEnroulement,
} from "@/lib/api";

/**
 * Simulateur d'optimisation FlexoCompare — PR #9.1 BAT MVP.
 *
 * Convention métier flexo : on parle TOUJOURS d'une étiquette en laize × dev
 * (largeur × hauteur dans l'orientation presse). Donc l'UI saisit la laize
 * en PREMIER puis le développé, et les libellés résultats sont "poses
 * laize × dev". Avant PR #9.1 c'était inversé — contre-métier.
 *
 * Côté API, on garde les noms historiques `largeur_mm` (= laize) et
 * `hauteur_mm` (= dev) pour ne pas casser la DB / cost_engine. C'est juste
 * un mapping UI : laize→largeur, dev→hauteur.
 */
// Diamètres mandrin courants flexo. ICE standard = 40 et 76 mm (annotés
// dans l'UI). Les autres (25, 38, 50) sont disponibles pour cas spéciaux.
const MANDRIN_OPTIONS = [25, 38, 40, 50, 76] as const;
const MANDRIN_STANDARDS_ICE = new Set([40, 76]);

/**
 * 8 sens d'enroulement convention métier flexo :
 *   SE1-4 : face EXTÉRIEUR (étiquettes vers l'extérieur de la bobine)
 *           orientations 0° / 180° / 270° / 90° du A
 *   SE5-8 : face INTÉRIEUR (étiquettes vers l'intérieur de la bobine)
 *           bobine inversée (sens de défilement opposé)
 * Le `rotationA` indique la rotation du A en degrés.
 * Le `face` "ext" / "int" change l'orientation de la bobine sur le picto.
 */
type SEOption = {
  code: SensEnroulement;
  rotationA: 0 | 90 | 180 | 270;
  face: "ext" | "int";
  label: string;
};

// Libellés ICE exact (cf guide métier Eric). `affichage` est le nom court
// utilisé dans l'UI ("Sens 1" plutôt que "SE1"). `code` reste SE1-8 pour
// rester cohérent avec la BDD/API/persistence existante.
const SE_OPTIONS: (SEOption & { affichage: string })[] = [
  { code: "SE1", rotationA: 0, face: "ext", affichage: "Sens 1", label: "0° Extérieur · droite avant" },
  { code: "SE2", rotationA: 180, face: "ext", affichage: "Sens 2", label: "180° Extérieur · gauche avant" },
  { code: "SE3", rotationA: 270, face: "ext", affichage: "Sens 3", label: "270° Extérieur · pied avant" },
  { code: "SE4", rotationA: 90, face: "ext", affichage: "Sens 4", label: "90° Extérieur · tête avant" },
  { code: "SE5", rotationA: 0, face: "int", affichage: "Sens 5", label: "0° Intérieur · droite avant" },
  { code: "SE6", rotationA: 180, face: "int", affichage: "Sens 6", label: "180° Intérieur · gauche avant" },
  { code: "SE7", rotationA: 270, face: "int", affichage: "Sens 7", label: "270° Intérieur · pied avant" },
  { code: "SE8", rotationA: 90, face: "int", affichage: "Sens 8", label: "90° Intérieur · tête avant" },
];

/**
 * Pictogramme bobine pour la sélection du sens d'enroulement.
 * Utilise les illustrations PNG produites par Eric (style atelier ICE pro,
 * annotations métier complètes) servies depuis `/assets/bobines/sens-N.png`.
 * Next.js `<Image>` gère la compression automatique (WebP/AVIF) selon le
 * navigateur, donc pas besoin d'optimiser les sources.
 */
function SEPictogramme({ code }: { code: SensEnroulement }) {
  const idx = parseInt(code.replace("SE", ""), 10);
  return (
    <Image
      src={`/assets/bobines/sens-${idx}.png`}
      alt={`Bobine ${code}`}
      width={120}
      height={120}
      className="inline-block rounded border border-border bg-white"
    />
  );
}

export default function OptimisationPage() {
  const { toast } = useToast();

  const [options, setOptions] = useState<OptionDisponible[] | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<Set<string>>(
    new Set()
  );

  // Format étiquette : laize d'abord, dev ensuite (convention métier)
  const [laize, setLaize] = useState<string>("100");
  const [dev, setDev] = useState<string>("80");
  const [rayonAngles, setRayonAngles] = useState<string>("2");
  const [formeCourbe, setFormeCourbe] = useState(false);
  const [intervalleDevMin, setIntervalleDevMin] = useState<string>("2");
  const [nbCouleurs, setNbCouleurs] = useState<string>("4");
  const [quantite, setQuantite] = useState<string>("10000");
  const [contrainteClientMm, setContrainteClientMm] = useState<string>("0");
  const [matiereTransparente, setMatiereTransparente] = useState(false);

  // BAT — params volatile MVP 9.1
  const [mandrin, setMandrin] = useState<number>(76);
  const [sensEnroulement, setSensEnroulement] = useState<SensEnroulement>("SE1");
  const [epaisseurMatiere, setEpaisseurMatiere] = useState<string>("150");

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
          // API : laize = largeur_mm, dev = hauteur_mm (compat historique)
          largeur_mm: parseFloat(laize),
          hauteur_mm: parseFloat(dev),
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
        mandrin_mm: mandrin,
        sens_enroulement: sensEnroulement,
        epaisseur_matiere_um: parseFloat(epaisseurMatiere),
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
          Saisissez l&apos;étiquette en <strong>laize × développé</strong>{" "}
          (convention métier flexo) et le contexte de production. Le top 3
          configurations cylindre × machine ressort scoré sur les 6 règles
          métier ICE et enrichi des valeurs BAT (laize papier, ml total,
          rendement, ø bobine).
        </p>
      </header>

      <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-2">
        {/* --- Colonne 1 : Format + impression --- */}
        <Card>
          <CardHeader>
            <CardTitle>Format & impression</CardTitle>
            <CardDescription>
              Dimensions étiquette (laize × dev), rayon des angles, couleurs.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="laize">Laize (largeur étiquette) — mm</Label>
                <Input
                  id="laize"
                  type="number"
                  step="0.1"
                  min={1}
                  value={laize}
                  onChange={(e) => setLaize(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dev">Développé (hauteur étiquette) — mm</Label>
                <Input
                  id="dev"
                  type="number"
                  step="0.1"
                  min={1}
                  value={dev}
                  onChange={(e) => setDev(e.target.value)}
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

        {/* --- Colonne 2 : Contraintes + BAT --- */}
        <Card>
          <CardHeader>
            <CardTitle>Contraintes & bobine</CardTitle>
            <CardDescription>
              Intervalles imprimeur/client, mandrin, sens enroulement,
              épaisseur matière (pour estimer ø bobine).
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
            <div className="space-y-2">
              <Label>Ø Mandrin bobine fille (mm)</Label>
              <div className="flex flex-wrap gap-3 text-sm">
                {MANDRIN_OPTIONS.map((m) => {
                  const isStandard = MANDRIN_STANDARDS_ICE.has(m);
                  return (
                    <label
                      key={m}
                      className="flex cursor-pointer items-center gap-1"
                    >
                      <input
                        type="radio"
                        name="mandrin"
                        checked={mandrin === m}
                        onChange={() => setMandrin(m)}
                        className="accent-foreground"
                      />
                      <span className={isStandard ? "font-medium" : ""}>
                        {m}
                      </span>
                      {isStandard && (
                        <span className="text-[10px] text-muted-foreground">
                          (ICE standard)
                        </span>
                      )}
                    </label>
                  );
                })}
              </div>
            </div>
            <div className="space-y-3">
              <Label>Sens enroulement (8 sens, convention métier)</Label>
              {(["ext", "int"] as const).map((face) => (
                <div key={face} className="space-y-1">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Sens {face === "ext" ? "extérieur" : "intérieur"}
                  </p>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {SE_OPTIONS.filter((o) => o.face === face).map((opt) => {
                      const selected = sensEnroulement === opt.code;
                      return (
                        <label
                          key={opt.code}
                          className={
                            "flex cursor-pointer flex-col items-center gap-1 rounded-md border p-2 text-xs transition-colors " +
                            (selected
                              ? "border-foreground bg-muted/50"
                              : "border-border hover:bg-muted/30")
                          }
                        >
                          <input
                            type="radio"
                            name="sens-enroulement"
                            checked={selected}
                            onChange={() => setSensEnroulement(opt.code)}
                            className="sr-only"
                          />
                          <SEPictogramme code={opt.code} />
                          <span className="font-medium">{opt.affichage}</span>
                          <span className="text-[10px] leading-tight text-muted-foreground">
                            {opt.label}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              ))}
              <p className="text-xs text-muted-foreground">
                Le pictogramme reproduit la convention atelier : bobine à gauche
                (face ext) ou à droite (face int), avec rotation du A finale.
                Application au schéma résultat à venir en PR 9.2.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="epaisseur">Épaisseur matière totale (µm)</Label>
              <Input
                id="epaisseur"
                type="number"
                step="1"
                min={10}
                max={1000}
                value={epaisseurMatiere}
                onChange={(e) => setEpaisseurMatiere(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Étiquette + liner adhésif. Default 150 µm (papier vélin
                standard). Utilisé pour estimer le ø bobine.
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
              <p className="text-sm text-muted-foreground">Chargement…</p>
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

      {response && (
        <ResultsSection
          response={response}
          laizeEtiq={parseFloat(laize)}
          devEtiq={parseFloat(dev)}
          mandrin={mandrin}
        />
      )}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Section résultats
// ---------------------------------------------------------------------------

function ResultsSection({
  response,
  laizeEtiq,
  devEtiq,
  mandrin,
}: {
  response: OptimisationCalculerResponse;
  laizeEtiq: number;
  devEtiq: number;
  mandrin: number;
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
        <div className="grid gap-4">
          {response.configurations.map((c, idx) => (
            <ConfigCard
              key={`${c.cylindre_id}-${c.nb_poses_dev}-${c.nb_poses_laize}-${idx}`}
              config={c}
              rank={idx + 1}
              laizeEtiq={laizeEtiq}
              devEtiq={devEtiq}
              mandrin={mandrin}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function ConfigCard({
  config,
  rank,
  laizeEtiq,
  devEtiq,
  mandrin,
}: {
  config: OptimisationConfigOut;
  rank: number;
  laizeEtiq: number;
  devEtiq: number;
  mandrin: number;
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
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div className="flex items-baseline gap-3">
            <CardTitle className="text-lg">#{rank}</CardTitle>
            <span
              className={`rounded px-2 py-0.5 text-xs font-medium ${color}`}
            >
              {config.qualite_echenillage}
            </span>
          </div>
          <span className="text-sm text-muted-foreground">
            Score : <strong>{config.score.toFixed(1)}</strong>
          </span>
        </div>
        <CardDescription>
          <strong>Cylindre {config.nb_dents_cylindre} dents</strong>
          {" · "}Z = {config.z_cylindre_mm} mm · Compatible avec{" "}
          <strong>
            {config.noms_machines_compatibles.length > 0
              ? config.noms_machines_compatibles.join(", ")
              : `machine #${config.machine_id}`}
          </strong>
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-2 text-sm">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Pose
          </h4>
          <Line
            label="Poses laize × dev"
            value={`${config.nb_poses_laize} × ${config.nb_poses_dev} = ${config.nb_poses_total} étiquettes / tour`}
            strong
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
            label="Laize plaque"
            value={`${config.laize_plaque_mm} mm`}
          />
          {config.consolidation_atteinte && (
            <div className="mt-1 rounded bg-emerald-50 px-2 py-1 text-xs text-emerald-900">
              ✓ Consolidation atteinte
            </div>
          )}
        </div>

        <div className="space-y-2 text-sm">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Matière & bobine
          </h4>
          <Line
            label="Laize papier"
            value={`${config.laize_papier_mm} mm`}
            strong
          />
          <Line
            label="Chute latérale (chaque côté)"
            value={`${config.chute_laterale_reelle_mm} mm`}
          />
          <Line
            label="Mètres linéaires total"
            value={`${config.ml_total_m} m`}
          />
          <Line label="m² consommé" value={`${config.m2_consomme} m²`} />
          <Line
            label="Rendement matière"
            value={`${config.rendement_pct}%`}
            strong
          />
          <Line
            label="ø bobine estimé"
            value={`${config.diametre_bobine_mm} mm`}
          />
          <Line
            label="Laize liner (vue client)"
            value={`${config.laize_liner_mm} mm`}
          />
          <Line
            label="Sens d'enroulement"
            value={formatSensEnroulement(config.sens_enroulement)}
          />
        </div>

        <div className="lg:col-span-2 text-xs text-muted-foreground">
          <span className="font-semibold">Coefs cumulés —</span> vitesse ×
          {config.coef_vitesse_final.toFixed(3)} / gâche ×
          {config.coef_gache_final.toFixed(3)} · confort rayon ×
          {config.coef_confort_rayon.toFixed(2)} · options vit ×
          {config.coef_vitesse_options.toFixed(2)} / gâche ×
          {config.coef_gache_options.toFixed(2)}
        </div>

        {/* Schéma BAT — 3 vues (plaque + bobine + bobine fille) */}
        <div className="lg:col-span-2">
          <SchemaImplantation
            config={config}
            laizeEtiqMm={laizeEtiq}
            devEtiqMm={devEtiq}
            mandrinMm={mandrin}
          />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Convertit un code interne SE1..SE8 en libellé ICE affiché ("Sens 1 — 0°
 * Extérieur · droite avant"). Code interne préservé pour la BDD/API.
 */
function formatSensEnroulement(code: SensEnroulement): string {
  const opt = SE_OPTIONS.find((o) => o.code === code);
  return opt ? `${opt.affichage} — ${opt.label}` : code;
}

function Line({
  label,
  value,
  strong = false,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className={strong ? "font-semibold" : "font-medium"}>{value}</span>
    </div>
  );
}
