"use client";

import Image from "next/image";
import { useSearchParams } from "next/navigation";
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
  getDevisDetail,
  getOptionsDisponibles,
  listMatieres,
  postOptimisationCalculer,
  type MatiereOut,
  type OptionDisponible,
  type SensEnroulement,
} from "@/lib/api";

import { BriefClientForm } from "./_components/BriefClientForm";
import { CoherenceBobineAlerte } from "./_components/CoherenceBobineAlerte";
import { MatcherOutilButton } from "./_components/MatcherOutilButton";
import { OptimisationChiffrage } from "./_components/OptimisationChiffrage";
import { OptimisationPoseCandidats } from "./_components/OptimisationPoseCandidats";
import { OptimisationPoseDetailLots } from "./_components/OptimisationPoseDetailLots";
import {
  OptimisationPoseProvider,
  useOptimisationPose,
} from "./_components/OptimisationPoseStore";
import { OptimisationRebobinage } from "./_components/OptimisationRebobinage";
import { sensAutoForTypeEntree } from "./_components/sens-auto-vierge";

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
// Diamètres mandrin courants flexo. Standard flexo = 40 et 76 mm (annotés
// dans l'UI). Les autres (25, 38, 50) sont disponibles pour cas spéciaux.
const MANDRIN_OPTIONS = [25, 38, 40, 50, 76] as const;
const MANDRIN_STANDARDS_FLEXO = new Set([40, 76]);

/**
 * 10 sens d'enroulement convention métier flexo :
 *   SE1-4 : face EXTÉRIEUR (étiquettes vers l'extérieur de la bobine)
 *           orientations 0° / 180° / 270° / 90° du A
 *   SE5-8 : face INTÉRIEUR (étiquettes vers l'intérieur de la bobine)
 *           bobine inversée (sens de défilement opposé)
 *   SE0 / SE9 : bobines livrées VIERGES (sans impression). SE0 = face
 *           extérieur, SE9 = face intérieur. Pas de cliché → pas
 *           d'orientation à représenter (rotationA = 0).
 * Le `rotationA` indique la rotation du A en degrés.
 * Le `face` "ext" / "int" change l'orientation de la bobine sur le picto.
 */
type SEOption = {
  code: SensEnroulement;
  rotationA: 0 | 90 | 180 | 270;
  face: "ext" | "int";
  label: string;
};

// Libellés flexo exacts (cf guide métier). `affichage` est le nom court
// utilisé dans l'UI ("Sens 1" plutôt que "SE1"). `code` reste SE0-9 pour
// rester cohérent avec la BDD/API/persistence existante.
const SE_OPTIONS: (SEOption & { affichage: string })[] = [
  { code: "SE1", rotationA: 0, face: "ext", affichage: "Sens 1", label: "0° Extérieur · droite avant" },
  { code: "SE2", rotationA: 180, face: "ext", affichage: "Sens 2", label: "180° Extérieur · gauche avant" },
  { code: "SE3", rotationA: 270, face: "ext", affichage: "Sens 3", label: "270° Extérieur · pied avant" },
  { code: "SE4", rotationA: 90, face: "ext", affichage: "Sens 4", label: "90° Extérieur · tête avant" },
  { code: "SE0", rotationA: 0, face: "ext", affichage: "Sens 0", label: "0° Extérieur · sans impression" },
  { code: "SE5", rotationA: 0, face: "int", affichage: "Sens 5", label: "0° Intérieur · droite avant" },
  { code: "SE6", rotationA: 180, face: "int", affichage: "Sens 6", label: "180° Intérieur · gauche avant" },
  { code: "SE7", rotationA: 270, face: "int", affichage: "Sens 7", label: "270° Intérieur · pied avant" },
  { code: "SE8", rotationA: 90, face: "int", affichage: "Sens 8", label: "90° Intérieur · tête avant" },
  { code: "SE9", rotationA: 0, face: "int", affichage: "Sens 9", label: "0° Intérieur · sans impression" },
];

/**
 * Pictogramme bobine pour la sélection du sens d'enroulement.
 * Utilise les illustrations PNG style atelier flexo pro (annotations
 * métier complètes) servies depuis `/assets/bobines/sens-N.png`.
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

/**
 * Sprint 13 avenant — orchestrateur workflow 3 étapes (Saisie → Candidats
 * → DetailLots). Le state machine est porté par OptimisationPoseStore
 * (React Context). Voir _components/.
 */
export default function OptimisationPage() {
  return (
    <OptimisationPoseProvider>
      <OptimisationPageInner />
    </OptimisationPoseProvider>
  );
}

function OptimisationPageInner() {
  const { etape, hydrateFromDevisExistant } = useOptimisationPose();
  const searchParams = useSearchParams();
  const devisIdParam = searchParams.get("devis_id");
  const { toast } = useToast();

  const [hydrationLoading, setHydrationLoading] = useState(false);
  const [hydrationError, setHydrationError] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  // Brief #33 commit 3 — détection mode édition via ?devis_id=X. Fetch
  // le devis et hydrate le store (selection + candidats + état étape 4
  // + bascule sur "chiffrage" ouverte par défaut).
  useEffect(() => {
    if (!devisIdParam || hydrated || hydrationLoading) return;
    const id = parseInt(devisIdParam, 10);
    if (Number.isNaN(id)) {
      setHydrationError("Identifiant de devis invalide dans l'URL.");
      return;
    }
    setHydrationLoading(true);
    getDevisDetail(id)
      .then((devis) => {
        if (!devis.lots_production || devis.lots_production.length === 0) {
          // Devis legacy mono-config (sans lots) : on ne peut pas éditer
          // via /optimisation. Redirection clean vers la page détail.
          setHydrationError(
            `Le devis ${devis.numero} est un devis legacy mono-config ; édite-le depuis sa page détail (rubrique manuelle).`
          );
          return;
        }
        hydrateFromDevisExistant(devis);
        setHydrated(true);
      })
      .catch((err) => {
        setHydrationError(
          err instanceof Error ? err.message : "Chargement du devis impossible"
        );
        toast({
          title: "Édition impossible",
          description:
            err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      })
      .finally(() => setHydrationLoading(false));
  }, [devisIdParam, hydrated, hydrationLoading, hydrateFromDevisExistant, toast]);

  if (devisIdParam && hydrationLoading) {
    return (
      <main className="mx-auto max-w-6xl space-y-4 p-6">
        <p className="text-sm text-muted-foreground">
          Chargement du devis #{devisIdParam}…
        </p>
      </main>
    );
  }
  if (devisIdParam && hydrationError) {
    return (
      <main className="mx-auto max-w-6xl space-y-4 p-6">
        <div className="rounded-lg border-2 border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {hydrationError}
        </div>
      </main>
    );
  }

  return (
    <>
      {etape === "saisie" && <OptimisationPoseSaisie />}
      {etape === "candidats" && <OptimisationPoseCandidats />}
      {etape === "detail" && <OptimisationPoseDetailLots />}
      {etape === "rebobinage" && <OptimisationRebobinage />}
      {etape === "chiffrage" && <OptimisationChiffrage />}
    </>
  );
}

function OptimisationPoseSaisie() {
  const {
    goCandidats,
    setNbCouleursImpression,
    setOptimWarnings,
    briefClient,
  } = useOptimisationPose();
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
  // Pré-remplissage Q ajustée : si l'URL contient ?q=N (venu du
  // bouton « Appliquer cette quantité » d'un scénario C du planificateur
  // de bobines), on initialise la saisie avec cette valeur. Sinon, défaut
  // historique 10000. L'init est paresseuse (n'évalue qu'au 1er mount).
  const searchParamsSaisie = useSearchParams();
  const [quantite, setQuantite] = useState<string>(() => {
    const qParam = searchParamsSaisie.get("q");
    if (qParam) {
      const n = parseInt(qParam, 10);
      if (Number.isFinite(n) && n > 0) return String(n);
    }
    return "10000";
  });
  // Sprint 13 avenant : default 2 mm (typique machine de pose client). 0 si
  // pas de contrainte client spécifique.
  const [contrainteClientMm, setContrainteClientMm] = useState<string>("2");

  // Sprint 13 avenant : forçage nb poses laize.
  // mode "auto" = comportement standard (moteur teste max, max-1, max-2).
  // mode "force" = blocage sur N poses laize, intervalle laize résultant calculé.
  const [nbPosesLaizeMode, setNbPosesLaizeMode] = useState<"auto" | "force">(
    "auto"
  );
  const [nbPosesLaizeForce, setNbPosesLaizeForce] = useState<string>("3");
  const [matiereTransparente, setMatiereTransparente] = useState(false);

  // BAT — params volatile MVP 9.1
  const [mandrin, setMandrin] = useState<number>(76);
  const [sensEnroulement, setSensEnroulement] = useState<SensEnroulement>("SE1");
  const [epaisseurMatiere, setEpaisseurMatiere] = useState<string>("150");

  // Auto-sélection SE0/SE9 quand le client envoie un rouleau vierge. La face
  // (Ext/Int) est dérivée du sens courant : SE1-4 → SE0, SE5-8 → SE9. Au
  // retour vers un type imprimable, SE0→SE1 et SE9→SE5. Pas de verrouillage :
  // l'utilisateur peut toujours cliquer manuellement un autre sens après.
  useEffect(() => {
    setSensEnroulement((prev) =>
      sensAutoForTypeEntree(prev, briefClient.type_entree_fichier),
    );
  }, [briefClient.type_entree_fichier]);

  // Souveraineté commerciale + matière
  const [matieres, setMatieres] = useState<MatiereOut[] | null>(null);
  const [matiereId, setMatiereId] = useState<number | null>(null);
  const [forcerEpaisseur, setForcerEpaisseur] = useState(false);
  const [motifEpaisseur, setMotifEpaisseur] = useState("");
  const [forcerIntervalleLaize, setForcerIntervalleLaize] = useState(false);
  const [intervalleLaizeForce, setIntervalleLaizeForce] = useState<string>("5");
  const [motifIntervalleLaize, setMotifIntervalleLaize] = useState("");
  const [forcerIntervalleDev, setForcerIntervalleDev] = useState(false);
  const [intervalleDevForce, setIntervalleDevForce] = useState<string>("2");
  const [motifIntervalleDev, setMotifIntervalleDev] = useState("");
  const [lacetsAsymetriques, setLacetsAsymetriques] = useState(false);
  const [lacetDroit, setLacetDroit] = useState<string>("2.5");
  const [lacetGauche, setLacetGauche] = useState<string>("2.5");
  // L1 — bord latéral / surplus extérieur (mm), SYMÉTRIQUE. Non forcé → on
  // envoie null ; le backend applique son défaut (chute latérale mini) et le
  // renvoie comme `geometrie_laize.bord_lateral_mm`. Le défaut effectif vient
  // donc de la réponse /calculer (pas d'appel entreprise séparé) ; on s'en
  // sert pour pré-remplir le champ override + l'afficher en non forcé.
  const [bordDefautMoteur, setBordDefautMoteur] = useState<number | null>(null);
  const [forcerBord, setForcerBord] = useState(false);
  const [bordLateral, setBordLateral] = useState<string>("");

  const [submitting, setSubmitting] = useState(false);
  // Brief #28 : `response` state retiré — l'étape 2 (OptimisationPoseCandidats)
  // affiche désormais TOUS les candidats via le store ; plus aucun rendu
  // inline en étape saisie.

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [opts, mats] = await Promise.all([
          getOptionsDisponibles(),
          listMatieres(),
        ]);
        if (!cancelled) {
          setOptions(opts);
          setMatieres(mats);
        }
      } catch (err) {
        toast({
          title: "Chargement impossible",
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

  // Quand on sélectionne une matière : auto-fill épaisseur + transparence
  // (read-only synchronisé, la matière prime sur la saisie manuelle).
  const matiereSelectionnee = useMemo(
    () => matieres?.find((m) => m.id === matiereId) ?? null,
    [matieres, matiereId]
  );
  useEffect(() => {
    if (matiereSelectionnee) {
      if (matiereSelectionnee.epaisseur_microns) {
        setEpaisseurMatiere(String(matiereSelectionnee.epaisseur_microns));
      }
      setMatiereTransparente(matiereSelectionnee.est_transparent);
    }
  }, [matiereSelectionnee]);

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
        // Souveraineté commerciale
        matiere_id: matiereId,
        epaisseur_matiere_force_um: forcerEpaisseur
          ? parseInt(epaisseurMatiere, 10)
          : null,
        motif_forcage_epaisseur: forcerEpaisseur ? motifEpaisseur : null,
        intervalle_laize_force_mm: forcerIntervalleLaize
          ? parseFloat(intervalleLaizeForce)
          : null,
        motif_forcage_intervalle_laize: forcerIntervalleLaize
          ? motifIntervalleLaize
          : null,
        intervalle_dev_force_mm: forcerIntervalleDev
          ? parseFloat(intervalleDevForce)
          : null,
        motif_forcage_intervalle_dev: forcerIntervalleDev
          ? motifIntervalleDev
          : null,
        lacets_asymetriques: lacetsAsymetriques,
        lacet_droit_mm: lacetsAsymetriques ? parseFloat(lacetDroit) : null,
        lacet_gauche_mm: lacetsAsymetriques ? parseFloat(lacetGauche) : null,
        nb_poses_laize_force:
          nbPosesLaizeMode === "force"
            ? parseInt(nbPosesLaizeForce, 10)
            : null,
        // L1 — bord latéral : null si non forcé (backend applique le défaut
        // entreprise → non-régression stricte), sinon la valeur saisie.
        bord_lateral_mm: forcerBord ? parseFloat(bordLateral) : null,
      });
      if (r.nb_candidats === 0) {
        toast({
          title: "Aucune configuration viable",
          description:
            r.message_filtrage ??
            "Tous les filtres ont éliminé les configurations.",
          variant: "destructive",
        });
      } else {
        // Fix couleurs — propage le nb couleurs impression saisi ici
        // jusqu'au chiffrage (payload_input.nb_couleurs). Le moteur backend
        // s'en sert pour le Poste 2 Encres.
        setNbCouleursImpression(parseInt(nbCouleurs, 10) || 0);
        // Fix forçage laize — propage les warnings non bloquants (ex.
        // valeur forcée hors recommandation moteur, motif manquant) pour
        // affichage en bandeau orange à l'étape candidats.
        setOptimWarnings(r.warnings ?? []);
        // L1 — le bord latéral EFFECTIF (surcharge si forcée, sinon défaut
        // entreprise appliqué par le back) revient dans `geometrie_laize`. On
        // le mémorise pour l'affichage "non forcé" + pré-remplir le champ
        // override tant que l'opérateur n'a pas saisi sa propre valeur.
        const bordEffectif =
          r.configurations[0]?.geometrie_laize?.bord_lateral_mm;
        if (typeof bordEffectif === "number") {
          setBordDefautMoteur(bordEffectif);
          if (!forcerBord) setBordLateral(String(bordEffectif));
        }
        // Sprint 13 avenant : push les candidats dans le store et bascule
        // vers étape 2 (tableau multi-sélection).
        goCandidats(
          r.configurations,
          parseInt(quantite, 10),
          parseFloat(laize),
          parseFloat(dev),
          mandrin,
        );
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
          métier flexo et enrichi des valeurs BAT (laize papier, ml total,
          rendement, ø bobine).
        </p>
      </header>

      {/* Sprint 14 Lot 3/4.3 — Brief client unifié, monté AVANT les contraintes
          techniques. State porté par OptimisationPoseProvider (Lot 4.2). */}
      <BriefClientForm />

      {/* Alerte cohérence Ø ext ↔ nb étiquettes/bobine.
          Source de vérité = backend (calcul_diametre_bobine, VUE B 242 mm).
          Non bloquante, debouncée 400 ms. Affichée uniquement quand tous les
          inputs nécessaires sont renseignés. Ecart_dev approximé via
          `intervalleDevMin` saisi (proxy avant exécution du moteur). */}
      {/* Fix cohérence ε — on passe l'épaisseur de la **matière saisie**
          (champ éditable, auto-synchronisé depuis le catalogue dès qu'une
          matière a `epaisseur_microns`), et NON le seul `epaisseur_microns`
          brut du catalogue. Sans ce câblage : pour un papier (où
          `epaisseur_microns` est NULL côté catalogue, le papier se
          caractérisant au grammage), le check retombait sur 150 µm
          fallback alors que l'opérateur avait pourtant saisi une valeur
          réaliste dans le champ Épaisseur. */}
      <CoherenceBobineAlerte
        devEtiqMm={parseFloat(dev) || 0}
        ecartDevMm={parseFloat(intervalleDevMin) || 0}
        mandrinMm={mandrin}
        epaisseurCatalogueUm={
          parseFloat(epaisseurMatiere) > 0
            ? parseFloat(epaisseurMatiere)
            : null
        }
      />

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
            <div className="grid grid-cols-2 items-end gap-4">
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
            <div className="grid grid-cols-2 items-end gap-4">
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
            <div className="grid grid-cols-2 items-start gap-4">
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
                Par défaut 2 mm. Mettre 0 si pas de contrainte. Sinon
                MAX(min imprimeur, min client) appliqué.
              </p>
            </div>

            {/* Sprint 13 avenant — Nb poses laize Auto/Forcer */}
            <div className="space-y-2">
              <Label>Nb poses laize</Label>
              <div className="flex flex-wrap items-center gap-4 text-sm">
                <label className="flex cursor-pointer items-center gap-1">
                  <input
                    type="radio"
                    name="nbPosesLaizeMode"
                    checked={nbPosesLaizeMode === "auto"}
                    onChange={() => setNbPosesLaizeMode("auto")}
                    className="accent-foreground"
                  />
                  <span>Auto</span>
                </label>
                <label className="flex cursor-pointer items-center gap-1">
                  <input
                    type="radio"
                    name="nbPosesLaizeMode"
                    checked={nbPosesLaizeMode === "force"}
                    onChange={() => setNbPosesLaizeMode("force")}
                    className="accent-foreground"
                  />
                  <span>Forcer</span>
                </label>
                <Input
                  type="number"
                  min={1}
                  max={20}
                  value={nbPosesLaizeForce}
                  onChange={(e) => setNbPosesLaizeForce(e.target.value)}
                  disabled={nbPosesLaizeMode === "auto"}
                  className="w-20"
                />
                <span className="text-xs text-muted-foreground">poses</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Auto = le moteur teste les variantes optimales. Forcer = se
                bloque sur N poses laize (intervalle laize calculé).
              </p>
            </div>

            <div className="space-y-2">
              <Label>Ø Mandrin bobine fille (mm)</Label>
              <div className="flex flex-wrap gap-3 text-sm">
                {MANDRIN_OPTIONS.map((m) => {
                  const isStandard = MANDRIN_STANDARDS_FLEXO.has(m);
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
                          (standard flexo)
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
              <Label htmlFor="matiere">Matière</Label>
              <select
                id="matiere"
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={matiereId ?? ""}
                onChange={(e) =>
                  setMatiereId(e.target.value ? Number(e.target.value) : null)
                }
              >
                <option value="">— Sélectionner —</option>
                {(matieres ?? []).map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.libelle}
                    {m.epaisseur_microns ? ` (${m.epaisseur_microns} µm)` : ""}
                  </option>
                ))}
              </select>
              {matiereSelectionnee && (
                <div className="rounded border border-border bg-muted/30 p-2 text-xs">
                  <div className="font-medium">{matiereSelectionnee.libelle}</div>
                  <div className="text-muted-foreground">
                    {matiereSelectionnee.epaisseur_microns
                      ? `Épaisseur ${matiereSelectionnee.epaisseur_microns} µm · `
                      : ""}
                    {matiereSelectionnee.opacite_pct
                      ? `Opacité ${matiereSelectionnee.opacite_pct} %`
                      : ""}
                    {matiereSelectionnee.est_transparent && (
                      <span className="ml-1 font-semibold text-amber-900">
                        · Matière transparente (spot verso activé)
                      </span>
                    )}
                  </div>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Auto-remplit l&apos;épaisseur + transparence (champs read-only
                ci-dessous quand matière sélectionnée).
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
                disabled={matiereSelectionnee !== null && !forcerEpaisseur}
              />
              {matiereSelectionnee && (
                <p className="text-xs text-muted-foreground">
                  Catalogue : {matiereSelectionnee.epaisseur_microns ?? "—"} µm
                </p>
              )}
              <label className="flex cursor-pointer items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  className="h-4 w-4 cursor-pointer accent-foreground"
                  checked={forcerEpaisseur}
                  onChange={(e) => setForcerEpaisseur(e.target.checked)}
                  disabled={matiereSelectionnee === null}
                />
                Forcer une autre valeur (motif obligatoire)
              </label>
              {forcerEpaisseur && (
                <textarea
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  rows={2}
                  placeholder="Motif (10 caractères minimum)"
                  value={motifEpaisseur}
                  onChange={(e) => setMotifEpaisseur(e.target.value)}
                />
              )}
            </div>

            <div className="space-y-2">
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 cursor-pointer accent-foreground"
                  checked={forcerIntervalleLaize}
                  onChange={(e) => setForcerIntervalleLaize(e.target.checked)}
                />
                Forcer intervalle laize (Règle 7 souveraineté)
              </label>
              {forcerIntervalleLaize && (
                <>
                  <Input
                    type="number"
                    step="0.1"
                    min={0}
                    value={intervalleLaizeForce}
                    onChange={(e) => setIntervalleLaizeForce(e.target.value)}
                  />
                  <textarea
                    className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    rows={2}
                    placeholder="Motif (10 caractères minimum)"
                    value={motifIntervalleLaize}
                    onChange={(e) => setMotifIntervalleLaize(e.target.value)}
                  />
                </>
              )}
            </div>

            <div className="space-y-2">
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 cursor-pointer accent-foreground"
                  checked={forcerIntervalleDev}
                  onChange={(e) => setForcerIntervalleDev(e.target.checked)}
                />
                Forcer intervalle dev (Règle 7 souveraineté)
              </label>
              {forcerIntervalleDev && (
                <>
                  <Input
                    type="number"
                    step="0.1"
                    min={0}
                    value={intervalleDevForce}
                    onChange={(e) => setIntervalleDevForce(e.target.value)}
                  />
                  <textarea
                    className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    rows={2}
                    placeholder="Motif (10 caractères minimum)"
                    value={motifIntervalleDev}
                    onChange={(e) => setMotifIntervalleDev(e.target.value)}
                  />
                </>
              )}
            </div>

            <div className="space-y-2">
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 cursor-pointer accent-foreground"
                  checked={lacetsAsymetriques}
                  onChange={(e) => setLacetsAsymetriques(e.target.checked)}
                />
                Lacets asymétriques (bobine fille rebobinage spécifique)
              </label>
              {!lacetsAsymetriques && (
                <p className="text-xs text-muted-foreground">
                  Par défaut symétriques (= intervalle laize / 2 de chaque côté).
                </p>
              )}
              {lacetsAsymetriques && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label htmlFor="lacet-d" className="text-xs">
                      Lacet droit (mm)
                    </Label>
                    <Input
                      id="lacet-d"
                      type="number"
                      step="0.1"
                      min={0.5}
                      value={lacetDroit}
                      onChange={(e) => setLacetDroit(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="lacet-g" className="text-xs">
                      Lacet gauche (mm)
                    </Label>
                    <Input
                      id="lacet-g"
                      type="number"
                      step="0.1"
                      min={0.5}
                      value={lacetGauche}
                      onChange={(e) => setLacetGauche(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* L1 — Bord latéral / surplus extérieur (SYMÉTRIQUE). Concept
                distinct des lacets ci-dessus (intervalle/2). Défaut = chute
                latérale mini entreprise ; éditable si forcé. Pas de motif
                (contrat L1). Asymétrie g/d hors L1. */}
            <div className="space-y-2">
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 cursor-pointer accent-foreground"
                  checked={forcerBord}
                  onChange={(e) => setForcerBord(e.target.checked)}
                  data-testid="forcer-bord-lateral"
                />
                Forcer le bord latéral / surplus extérieur
              </label>
              {!forcerBord && (
                <p className="text-xs text-muted-foreground">
                  Par défaut, le moteur applique la chute latérale mini de
                  l&apos;entreprise des 2 côtés
                  {bordDefautMoteur !== null
                    ? ` (${bordDefautMoteur} mm appliqué au dernier calcul)`
                    : " (valeur visible dans la décompo après calcul)"}
                  . Coche pour saisir une autre valeur.
                </p>
              )}
              {forcerBord && (
                <div>
                  <Label htmlFor="bord-lateral" className="text-xs">
                    Bord latéral / surplus extérieur (mm) — symétrique, appliqué
                    des 2 côtés
                  </Label>
                  <Input
                    id="bord-lateral"
                    data-testid="bord-lateral-input"
                    type="number"
                    step="0.1"
                    min={0}
                    value={bordLateral}
                    onChange={(e) => setBordLateral(e.target.value)}
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    Surplus de matière de chaque côté de l&apos;impression. La
                    laize papier réelle = laize imprimée + 2 × bord latéral.
                    N&apos;impacte pas le prix en l&apos;état.
                  </p>
                </div>
              )}
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

        {/* Sprint 14 Lot 4.5 — Matcher outil : vérifie si un cylindre du parc
            convient déjà au format saisi, avant de lancer l'optim complète. */}
        <div className="lg:col-span-2">
          <MatcherOutilButton
            laizeEtiqMm={parseFloat(laize) || 0}
            devEtiqMm={parseFloat(dev) || 0}
            intervalleDevMm={parseFloat(intervalleDevMin) || 0}
            intervalleLaizeMm={
              forcerIntervalleLaize ? parseFloat(intervalleLaizeForce) || 0 : 0
            }
          />
        </div>

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

    </main>
  );
}
