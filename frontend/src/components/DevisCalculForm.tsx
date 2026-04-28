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
  listPartenairesST,
  type Complexe,
  type DevisInput,
  type DevisOutput,
  type EncreType,
  type Machine,
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
  forfaits_st: { partenaire_st_id: number; montant_eur: string }[];
  heures_dossier_override: string;
  pct_marge_override_pct: string; // saisi en % (0-200), divisé /100 au submit
}

// Pré-remplissage cas V1 médian (figé Lot 3d, total HT attendu 1449.09 €).
const PREFILL_V1: FormState = {
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
  forfaits_st: [{ partenaire_st_id: 1, montant_eur: "50.00" }],
  heures_dossier_override: "",
  pct_marge_override_pct: "",
};

interface DevisCalculFormProps {
  onResult: (result: DevisOutput | null) => void;
}

export function DevisCalculForm({ onResult }: DevisCalculFormProps) {
  const [data, setData] = useState<FormState>(PREFILL_V1);
  const [complexes, setComplexes] = useState<Complexe[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [partenaires, setPartenaires] = useState<PartenaireST[]>([]);
  const [isLoadingLists, setIsLoadingLists] = useState(true);
  const [listsError, setListsError] = useState<string | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Charger les 3 listes au mount, en parallèle.
  useEffect(() => {
    Promise.all([listComplexes(), listMachines(), listPartenairesST()])
      .then(([cx, mx, px]) => {
        setComplexes(cx);
        setMachines(mx);
        setPartenaires(px);
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
    setData(PREFILL_V1);
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
      const result = await calculerDevis(buildPayload());
      onResult(result);
      // Scroll doux vers les résultats si l'utilisateur est en haut de page.
      setTimeout(() => {
        document
          .getElementById("devis-result")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    } catch (err) {
      onResult(null);
      if (err instanceof ApiError) {
        setError(`Erreur ${err.status} : ${err.message.split(" → ").pop() ?? err.message}`);
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
          <CardTitle>Couleurs (P2 Encres + P3 Clichés)</CardTitle>
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
                {m.vitesse_max_m_min
                  ? ` · vitesse max ${m.vitesse_max_m_min} m/min`
                  : ""}
                {m.statut !== "actif" ? ` (${m.statut})` : ""}
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

      <Card>
        <CardHeader>
          <CardTitle>Overrides (optionnels)</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="heures_override">
              Heures dossier (vide = dérivé machine)
            </Label>
            <Input
              id="heures_override"
              type="number"
              min={0}
              step="0.25"
              placeholder="ex: 2.5"
              value={data.heures_dossier_override}
              onChange={(e) =>
                setField("heures_dossier_override", e.target.value)
              }
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="marge_override">
              Marge (% — vide = défaut entreprise)
            </Label>
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
          </div>
        </CardContent>
      </Card>

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
