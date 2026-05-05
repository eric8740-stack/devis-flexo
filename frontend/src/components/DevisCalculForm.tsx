"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ApiError,
  ENCRES_LIBELLES,
  ENCRES_TYPES,
  calculerDevis,
  listComplexes,
  listMachines,
  listOutilsDecoupe,
  listPartenairesST,
  type Complexe,
  type DevisCalculResult,
  type DevisInput,
  type EncreType,
  type Machine,
  type ModeCalcul,
  type OutilDecoupeRead,
  type PartenaireST,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// State du formulaire — séparé du DevisInput pour gérer les inputs vides
// (state interne en string, conversion au submit).
// ---------------------------------------------------------------------------

interface FormState {
  complexe_id: number;
  laize_utile_mm: number;
  ml_total: number;
  nb_couleurs_par_type: Record<EncreType, number>;
  machine_id: number;
  // Sprint 5 Lot 5d — format / outillage
  format_etiquette_largeur_mm: number;
  format_etiquette_hauteur_mm: number;
  nb_poses_largeur: number;
  nb_poses_developpement: number;
  outil_decoupe_existant: boolean;
  outil_decoupe_id: number | null;
  forme_speciale: boolean;
  nb_traces_complexite: number;
  // Sprint 7 Lot 7f — mode de calcul + intervalle conditionnel
  mode_calcul: ModeCalcul;
  intervalle_mm: number; // visible/utilisé seulement si mode='manuel'
  // Sous-traitance + overrides
  forfaits_st: { partenaire_st_id: number; montant_eur: string }[];
  heures_dossier_override: string;
  pct_marge_override_pct: string; // saisi en % (0-200), divisé /100 au submit
}

// Pré-remplissage cas V1a médian (Sprint 5 Lot 5c, total HT attendu 1449.09 €).
const PREFILL_V1A: FormState = {
  complexe_id: 31,
  laize_utile_mm: 220,
  ml_total: 3000,
  nb_couleurs_par_type: {
    process_cmj: 4,
    process_black_hc: 0,
    pantone: 1,
    blanc_high_opaque: 0,
    metallise: 0,
  },
  machine_id: 1,
  // V1a : format 60×40, 3p1d (cohérent laize 220 = 3×60 + 2×20),
  // outil existant non référencé.
  format_etiquette_largeur_mm: 60,
  format_etiquette_hauteur_mm: 40,
  nb_poses_largeur: 3,
  nb_poses_developpement: 1,
  outil_decoupe_existant: true,
  outil_decoupe_id: null,
  forme_speciale: false,
  nb_traces_complexite: 1,
  mode_calcul: "manuel",
  intervalle_mm: 3,
  forfaits_st: [{ partenaire_st_id: 1, montant_eur: "50.00" }],
  heures_dossier_override: "",
  pct_marge_override_pct: "",
};

// Sprint 4 Lot 4d — mapping inverse DevisInput → FormState pour pré-remplir
// le formulaire en édition (route /devis/[id]/edit).
function devisInputToFormState(input: DevisInput): FormState {
  const couleurs: Record<EncreType, number> = {
    process_cmj: 0,
    process_black_hc: 0,
    pantone: 0,
    blanc_high_opaque: 0,
    metallise: 0,
  };
  for (const [k, v] of Object.entries(input.nb_couleurs_par_type ?? {})) {
    if (k in couleurs) couleurs[k as EncreType] = v;
  }
  return {
    complexe_id: input.complexe_id,
    laize_utile_mm: input.laize_utile_mm,
    ml_total: input.ml_total,
    nb_couleurs_par_type: couleurs,
    machine_id: input.machine_id,
    format_etiquette_largeur_mm: input.format_etiquette_largeur_mm ?? 60,
    format_etiquette_hauteur_mm: input.format_etiquette_hauteur_mm ?? 40,
    nb_poses_largeur: input.nb_poses_largeur ?? 1,
    nb_poses_developpement: input.nb_poses_developpement ?? 1,
    outil_decoupe_existant: input.outil_decoupe_existant ?? true,
    outil_decoupe_id: input.outil_decoupe_id ?? null,
    forme_speciale: input.forme_speciale ?? false,
    nb_traces_complexite: input.nb_traces_complexite ?? 1,
    mode_calcul: input.mode_calcul ?? "manuel",
    intervalle_mm: input.intervalle_mm ? parseFloat(input.intervalle_mm) : 3,
    forfaits_st: input.forfaits_st.map((f) => ({
      partenaire_st_id: f.partenaire_st_id,
      montant_eur: f.montant_eur,
    })),
    heures_dossier_override: input.heures_dossier_override ?? "",
    pct_marge_override_pct: input.pct_marge_override
      ? (parseFloat(input.pct_marge_override) * 100).toFixed(2).replace(/\.?0+$/, "")
      : "",
  };
}

interface DevisCalculFormProps {
  // Sprint 4 Lot 4d : onResult expose aussi le payload_input envoyé à l'API
  // pour permettre au parent de le sauvegarder via POST /api/devis.
  onResult: (result: DevisCalculResult | null, input?: DevisInput) => void;
  // Sprint 4 Lot 4d : pré-remplissage en édition (depuis devis.payload_input).
  initialPayloadInput?: DevisInput | null;
}

export function DevisCalculForm({
  onResult,
  initialPayloadInput,
}: DevisCalculFormProps) {
  const [data, setData] = useState<FormState>(() =>
    initialPayloadInput ? devisInputToFormState(initialPayloadInput) : PREFILL_V1A
  );
  const [complexes, setComplexes] = useState<Complexe[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [partenaires, setPartenaires] = useState<PartenaireST[]>([]);
  const [outils, setOutils] = useState<OutilDecoupeRead[]>([]);
  const [isLoadingLists, setIsLoadingLists] = useState(true);
  const [listsError, setListsError] = useState<string | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Charger les 4 listes au mount, en parallèle.
  useEffect(() => {
    Promise.all([
      listComplexes(),
      listMachines(),
      listPartenairesST(),
      listOutilsDecoupe(),
    ])
      .then(([cx, mx, px, ox]) => {
        setComplexes(cx);
        setMachines(mx);
        setPartenaires(px);
        setOutils(ox);
      })
      .catch((err: unknown) => {
        setListsError(
          err instanceof Error
            ? err.message
            : "Erreur de chargement des référentiels"
        );
      })
      .finally(() => setIsLoadingLists(false));
  }, []);

  const setField = <K extends keyof FormState>(field: K, value: FormState[K]) =>
    setData((prev) => ({ ...prev, [field]: value }));

  const setCouleur = (type: EncreType, n: number) =>
    setData((prev) => ({
      ...prev,
      nb_couleurs_par_type: { ...prev.nb_couleurs_par_type, [type]: n },
    }));

  const addForfait = () => {
    const firstId = partenaires[0]?.id ?? 1;
    setData((prev) => ({
      ...prev,
      forfaits_st: [
        ...prev.forfaits_st,
        { partenaire_st_id: firstId, montant_eur: "0" },
      ],
    }));
  };

  const removeForfait = (idx: number) =>
    setData((prev) => ({
      ...prev,
      forfaits_st: prev.forfaits_st.filter((_, i) => i !== idx),
    }));

  const updateForfait = (
    idx: number,
    patch: Partial<FormState["forfaits_st"][number]>
  ) =>
    setData((prev) => ({
      ...prev,
      forfaits_st: prev.forfaits_st.map((f, i) =>
        i === idx ? { ...f, ...patch } : f
      ),
    }));

  const reset = () => {
    setData(PREFILL_V1A);
    setError(null);
    onResult(null);
  };

  // Convertit le state UI en payload backend.
  const buildPayload = (): DevisInput => {
    // Filtre les couleurs à 0 pour ne pas envoyer de bruit au moteur.
    const couleurs: Record<string, number> = {};
    for (const [k, v] of Object.entries(data.nb_couleurs_par_type)) {
      if (v > 0) couleurs[k] = v;
    }

    return {
      complexe_id: data.complexe_id,
      laize_utile_mm: data.laize_utile_mm,
      ml_total: data.ml_total,
      nb_couleurs_par_type: couleurs,
      machine_id: data.machine_id,
      // S5 — format / outillage
      format_etiquette_largeur_mm: data.format_etiquette_largeur_mm,
      format_etiquette_hauteur_mm: data.format_etiquette_hauteur_mm,
      nb_poses_largeur: data.nb_poses_largeur,
      nb_poses_developpement: data.nb_poses_developpement,
      outil_decoupe_existant: data.outil_decoupe_existant,
      outil_decoupe_id: data.outil_decoupe_existant
        ? data.outil_decoupe_id
        : null,
      forme_speciale: data.forme_speciale,
      nb_traces_complexite: data.nb_traces_complexite,
      // Sprint 7 — mode + intervalle conditionnel
      mode_calcul: data.mode_calcul,
      // En mode 'matching', intervalle_mm DOIT être null (validateur backend)
      intervalle_mm:
        data.mode_calcul === "manuel" ? String(data.intervalle_mm) : null,
      forfaits_st: data.forfaits_st.map((f) => ({
        partenaire_st_id: f.partenaire_st_id,
        montant_eur: f.montant_eur || "0",
      })),
      heures_dossier_override: data.heures_dossier_override
        ? data.heures_dossier_override
        : null,
      // UI saisie en % (18) → API attend Decimal (0.18). Vide = pas d'override.
      pct_marge_override: data.pct_marge_override_pct
        ? (parseFloat(data.pct_marge_override_pct) / 100).toFixed(4)
        : null,
    };
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsCalculating(true);
    try {
      const payload = buildPayload();
      const result = await calculerDevis(payload);
      onResult(result, payload);
      // Scroll doux vers les résultats si l'utilisateur est en haut de page.
      setTimeout(() => {
        document
          .getElementById("devis-result")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    } catch (err) {
      onResult(null);
      if (err instanceof ApiError) {
        setError(`Erreur : ${err.message.split(" → ").pop() ?? err.message}`);
      } else {
        setError(
          err instanceof Error ? err.message : "Erreur serveur inconnue"
        );
      }
    } finally {
      setIsCalculating(false);
    }
  };

  if (isLoadingLists) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Chargement des référentiels…
        </CardContent>
      </Card>
    );
  }

  if (listsError) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-destructive">
          {listsError}
        </CardContent>
      </Card>
    );
  }

  // Style des selects natifs (aligné sur ClientForm.tsx)
  const selectClass =
    "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

  return (
    <form onSubmit={handleSubmit} className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Mode de calcul</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={data.mode_calcul === "manuel" ? "default" : "outline"}
              size="sm"
              onClick={() => setField("mode_calcul", "manuel")}
            >
              Manuel
            </Button>
            <Button
              type="button"
              variant={data.mode_calcul === "matching" ? "default" : "outline"}
              size="sm"
              onClick={() => setField("mode_calcul", "matching")}
            >
              Matching cylindres
            </Button>
          </div>

          {data.mode_calcul === "manuel" ? (
            <div className="grid gap-3 sm:grid-cols-[200px_1fr] sm:items-end">
              <div className="grid gap-2">
                <Label htmlFor="intervalle_mm">
                  Intervalle entre étiquettes (mm)
                </Label>
                <Input
                  id="intervalle_mm"
                  type="number"
                  min={2.5}
                  max={15}
                  step="0.1"
                  value={data.intervalle_mm}
                  onChange={(e) =>
                    setField(
                      "intervalle_mm",
                      Math.min(15, Math.max(2.5, Number(e.target.value) || 3))
                    )
                  }
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Mode manuel : vous fixez l&apos;intervalle (default 3 mm = preset
                V1a). Le prix au mille est calculé directement à partir de ce
                paramètre, sans matcher de cylindre.
              </p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              Mode matching : l&apos;app cherche les 3 cylindres magnétiques les
              plus économiques compatibles avec votre format hauteur (intervalle
              entre 2,5 et 15 mm) et la largeur de plaque (effet banane). Le HT
              est identique entre candidats — seul le prix au mille varie selon
              le cylindre choisi.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Matière et format (P1)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid gap-2">
            <Label htmlFor="complexe_id">Complexe matière *</Label>
            <select
              id="complexe_id"
              className={selectClass}
              value={data.complexe_id}
              onChange={(e) => setField("complexe_id", Number(e.target.value))}
            >
              {complexes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.reference} — {c.face_matiere ?? c.famille}
                  {c.grammage_g_m2 ? ` · ${c.grammage_g_m2} g/m²` : ""} ·{" "}
                  {c.prix_m2_eur} €/m²
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              Le moteur dérive le prix kg depuis prix_m2 × 1000 / grammage.
              Les complexes sans grammage (BOPP, PE…) ne sont pas calculables
              en P1 et déclenchent une erreur 422.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="laize_utile_mm">Laize utile (mm) *</Label>
              <Input
                id="laize_utile_mm"
                type="number"
                min={50}
                max={370}
                required
                value={data.laize_utile_mm}
                onChange={(e) =>
                  setField("laize_utile_mm", Number(e.target.value))
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ml_total">Tirage (mètres linéaires) *</Label>
              <Input
                id="ml_total"
                type="number"
                min={100}
                required
                value={data.ml_total}
                onChange={(e) => setField("ml_total", Number(e.target.value))}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Couleurs (P2 Encres + P3a Clichés)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ENCRES_TYPES.map((type) => (
            <div key={type} className="grid gap-2">
              <Label htmlFor={`couleur-${type}`}>{ENCRES_LIBELLES[type]}</Label>
              <Input
                id={`couleur-${type}`}
                type="number"
                min={0}
                max={12}
                value={data.nb_couleurs_par_type[type]}
                onChange={(e) =>
                  setCouleur(type, Math.max(0, Number(e.target.value) || 0))
                }
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Format & Outillage (P3b Découpe + prix au mille)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="grid gap-2">
              <Label htmlFor="format_l">Format largeur (mm) *</Label>
              <Input
                id="format_l"
                type="number"
                min={1}
                required
                value={data.format_etiquette_largeur_mm}
                onChange={(e) =>
                  setField(
                    "format_etiquette_largeur_mm",
                    Math.max(1, Number(e.target.value) || 1)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="format_h">Format hauteur (mm) *</Label>
              <Input
                id="format_h"
                type="number"
                min={1}
                required
                value={data.format_etiquette_hauteur_mm}
                onChange={(e) =>
                  setField(
                    "format_etiquette_hauteur_mm",
                    Math.max(1, Number(e.target.value) || 1)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="poses_l">Poses largeur *</Label>
              <Input
                id="poses_l"
                type="number"
                min={1}
                required
                value={data.nb_poses_largeur}
                onChange={(e) =>
                  setField(
                    "nb_poses_largeur",
                    Math.max(1, Number(e.target.value) || 1)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="poses_d">Poses dévelop. *</Label>
              <Input
                id="poses_d"
                type="number"
                min={1}
                required
                value={data.nb_poses_developpement}
                onChange={(e) =>
                  setField(
                    "nb_poses_developpement",
                    Math.max(1, Number(e.target.value) || 1)
                  )
                }
              />
            </div>
          </div>

          <div className="grid gap-3">
            <Label>Outil de découpe</Label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant={data.outil_decoupe_existant ? "default" : "outline"}
                size="sm"
                onClick={() => setField("outil_decoupe_existant", true)}
              >
                Outil existant (0 €)
              </Button>
              <Button
                type="button"
                variant={!data.outil_decoupe_existant ? "default" : "outline"}
                size="sm"
                onClick={() => setField("outil_decoupe_existant", false)}
              >
                Nouvel outil (à fabriquer)
              </Button>
            </div>

            {data.outil_decoupe_existant ? (
              <div className="grid gap-2">
                <Label htmlFor="outil_id">
                  Outil du catalogue (optionnel — None = générique)
                </Label>
                <select
                  id="outil_id"
                  className={selectClass}
                  value={data.outil_decoupe_id ?? ""}
                  onChange={(e) => {
                    // Sprint 12 mini-fix UX-2 : à la sélection d'un outil
                    // existant, on synchronise les champs Format avec ses
                    // dimensions pour éviter l'incohérence (ex. choisir un
                    // outil 50×210 alors que le format saisi est 60×40).
                    // L'utilisateur peut toujours modifier ensuite (cas
                    // pose multiple, ré-utilisation d'outil sur format
                    // dérivé). Le choix "(non référencé)" ne touche à rien.
                    const selectedId = e.target.value
                      ? Number(e.target.value)
                      : null;
                    const outil =
                      selectedId !== null
                        ? outils.find((o) => o.id === selectedId) ?? null
                        : null;
                    setData((prev) => ({
                      ...prev,
                      outil_decoupe_id: selectedId,
                      ...(outil
                        ? {
                            format_etiquette_largeur_mm: Number(outil.format_l_mm),
                            format_etiquette_hauteur_mm: Number(outil.format_h_mm),
                          }
                        : {}),
                    }));
                  }}
                >
                  <option value="">(non référencé)</option>
                  {outils.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.libelle} ({o.format_l_mm}×{o.format_h_mm},{" "}
                      {o.nb_poses_l}p×{o.nb_poses_h}d
                      {o.forme_speciale ? ", forme spé" : ""})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  Outil existant = déjà amorti, P3b = 0 €. L&apos;identifiant
                  sert uniquement à tracer dans l&apos;audit. À la sélection,
                  les champs <em>Format largeur/hauteur</em> sont préremplis
                  depuis l&apos;outil — modifiables si pose multiple.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="nb_traces">Nombre de tracés (1-10)</Label>
                  <Input
                    id="nb_traces"
                    type="number"
                    min={1}
                    max={10}
                    value={data.nb_traces_complexite}
                    onChange={(e) =>
                      setField(
                        "nb_traces_complexite",
                        Math.min(10, Math.max(1, Number(e.target.value) || 1))
                      )
                    }
                  />
                </div>
                <div className="flex items-end">
                  <label className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="h-4 w-4"
                      checked={data.forme_speciale}
                      onChange={(e) =>
                        setField("forme_speciale", e.target.checked)
                      }
                    />
                    Forme spéciale (surcoût plaque +40 %)
                  </label>
                </div>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Nouvel outil : 200 € + nb_traces × 50 € (× 1.40 si forme
              spéciale).
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Machine (P5 Roulage + P7 MO)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          <Label htmlFor="machine_id">Presse flexo *</Label>
          <select
            id="machine_id"
            className={selectClass}
            value={data.machine_id}
            onChange={(e) => setField("machine_id", Number(e.target.value))}
          >
            {machines.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nom}
                {m.vitesse_moyenne_m_h
                  ? ` · vitesse moyenne ${Math.round(
                      m.vitesse_moyenne_m_h / 60
                    )} m/min`
                  : ""}
                {!m.actif ? " (inactif)" : ""}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">
            La vitesse moyenne réaliste et la durée de calage sont lues
            directement depuis le seed machine côté backend.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Sous-traitance (P6 Finitions)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          {data.forfaits_st.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Aucun forfait sous-traitance. Cliquez « + Ajouter » pour
              renseigner un partenaire.
            </p>
          )}
          {data.forfaits_st.map((f, idx) => (
            <div
              key={idx}
              className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[1fr_140px_auto]"
            >
              <div className="grid gap-2">
                <Label htmlFor={`forfait-st-${idx}`}>Partenaire ST</Label>
                <select
                  id={`forfait-st-${idx}`}
                  className={selectClass}
                  value={f.partenaire_st_id}
                  onChange={(e) =>
                    updateForfait(idx, {
                      partenaire_st_id: Number(e.target.value),
                    })
                  }
                >
                  {partenaires.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.raison_sociale}
                      {p.prestation_type ? ` (${p.prestation_type})` : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor={`forfait-montant-${idx}`}>Montant €</Label>
                <Input
                  id={`forfait-montant-${idx}`}
                  type="number"
                  min={0}
                  step="0.01"
                  value={f.montant_eur}
                  onChange={(e) =>
                    updateForfait(idx, { montant_eur: e.target.value })
                  }
                />
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeForfait(idx)}
              >
                Retirer
              </Button>
            </div>
          ))}
          <div>
            <Button type="button" variant="outline" size="sm" onClick={addForfait}>
              + Ajouter un forfait ST
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Sprint 12 mini-fix UX-5 : on déplace la Card "Overrides" dans un
          bloc dépliable (<details> natif, 0 dep) pour ne pas alourdir
          le formulaire pour 99 % des cas (= calcul auto). On clarifie
          aussi le champ "Heures dossier" avec une description visible
          (préféré à un tooltip survol pour l'accessibilité mobile). */}
      <details className="group rounded-xl border bg-card text-card-foreground shadow">
        <summary className="flex cursor-pointer list-none items-center justify-between p-6 font-semibold transition-colors hover:bg-muted/30 [&::-webkit-details-marker]:hidden">
          <span>
            Options avancées{" "}
            <span className="text-sm font-normal text-muted-foreground">
              (laisser vide = calcul automatique)
            </span>
          </span>
          <span
            className="text-muted-foreground transition-transform group-open:rotate-180"
            aria-hidden="true"
          >
            ▼
          </span>
        </summary>
        <div className="grid grid-cols-1 gap-4 px-6 pb-6 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="heures_override">Heures dossier</Label>
            <Input
              id="heures_override"
              type="number"
              min={0}
              step="0.25"
              placeholder="ex: 2,5"
              value={data.heures_dossier_override}
              onChange={(e) =>
                setField("heures_dossier_override", e.target.value)
              }
            />
            <p className="text-xs text-muted-foreground">
              Vide = l&apos;application calcule automatiquement les heures
              à partir de la machine et des paramètres du devis. À remplir
              uniquement en cas particulier (attente machine, maintenance
              pendant le job, devis post-prod avec heures réelles).
            </p>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="marge_override">Marge</Label>
            <Input
              id="marge_override"
              type="number"
              min={0}
              max={200}
              step="0.5"
              placeholder="ex: 22"
              value={data.pct_marge_override_pct}
              onChange={(e) =>
                setField("pct_marge_override_pct", e.target.value)
              }
            />
            <p className="text-xs text-muted-foreground">
              Vide = marge par défaut de l&apos;entreprise (configurée dans
              <em> Paramètres &gt; Entreprise</em>). À renseigner en pourcentage
              (ex&nbsp;: 22 pour +22 %).
            </p>
          </div>
        </div>
      </details>

      {error && (
        <div
          role="alert"
          className="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive"
        >
          <strong>Erreur :</strong> {error}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={reset}
          disabled={isCalculating}
        >
          🗑 Réinitialiser le formulaire
        </Button>
        <Button type="submit" disabled={isCalculating}>
          {isCalculating ? "Calcul en cours…" : "Calculer le devis"}
        </Button>
      </div>
    </form>
  );
}
