"use client";

/**
 * Stock S1 — inventaire des bobines (`/api/bobines`, contrat figé CC1+CC2).
 * Liste + filtres (matière / rangée / statut) · création / édition (ml_restant
 * éditable à la main) · suppression confirmée. Convention emplacement :
 * `rangee.etage.position` (ex. « A.0.25 »). Front pur (le back pilote le CRUD
 * + le scoping tenant). Dégradation propre si back S1 absent (liste vide).
 *
 * Hors S1 : mouvements auto (S2), lien devis↔stock (S3).
 */
import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  ApiError,
  createBobine,
  createMouvement,
  deleteBobine,
  listBobines,
  listMatieres,
  listMouvementsBobine,
  updateBobine,
  type BobineCreate,
  type BobineOut,
  type BobineStatut,
  type MatiereOut,
  type MouvementOut,
  type MouvementType,
} from "@/lib/api";

const STATUTS: { value: BobineStatut; label: string }[] = [
  { value: "en_stock", label: "En stock" },
  { value: "reservee", label: "Réservée" },
  { value: "consommee", label: "Consommée" },
];
const statutLabel = (s: BobineStatut) =>
  STATUTS.find((x) => x.value === s)?.label ?? s;

const STATUT_CLASS: Record<BobineStatut, string> = {
  en_stock: "bg-emerald-100 text-emerald-800",
  reservee: "bg-amber-100 text-amber-800",
  consommee: "bg-muted text-muted-foreground",
};

// S2 — mouvements de stock.
const MVT_LABELS: Record<MouvementType, string> = {
  entree: "Entrée",
  sortie: "Sortie",
  inventaire: "Ajuster (inventaire)",
};
// Libellé du champ ml selon le type (entrée/sortie = delta ; inventaire = cible).
const MVT_ML_LABEL: Record<MouvementType, string> = {
  entree: "ml à ajouter",
  sortie: "ml à sortir",
  inventaire: "nouveau ml restant",
};

interface FormState {
  matiere_id: string;
  laize_mm: string;
  epaisseur_microns: string;
  ml_initial: string;
  ml_restant: string;
  rangee: string;
  etage: string;
  position: string;
  statut: BobineStatut;
  date_reception: string;
  fournisseur: string;
  reference_lot: string;
}

const emptyForm: FormState = {
  matiere_id: "",
  laize_mm: "",
  epaisseur_microns: "",
  ml_initial: "",
  ml_restant: "",
  rangee: "",
  etage: "",
  position: "",
  statut: "en_stock",
  date_reception: "",
  fournisseur: "",
  reference_lot: "",
};

function bobineToForm(b: BobineOut): FormState {
  return {
    matiere_id: String(b.matiere_id),
    laize_mm: String(b.laize_mm),
    epaisseur_microns: String(b.epaisseur_microns),
    ml_initial: String(b.ml_initial),
    ml_restant: String(b.ml_restant),
    rangee: b.rangee,
    etage: String(b.etage),
    position: String(b.position),
    statut: b.statut,
    date_reception: b.date_reception ?? "",
    fournisseur: b.fournisseur ?? "",
    reference_lot: b.reference_lot ?? "",
  };
}

export default function StockPage() {
  const { toast } = useToast();

  const [matieres, setMatieres] = useState<MatiereOut[]>([]);
  const [bobines, setBobines] = useState<BobineOut[]>([]);
  const [loading, setLoading] = useState(true);

  // Filtres.
  const [filtreMatiere, setFiltreMatiere] = useState("");
  const [filtreRangee, setFiltreRangee] = useState("");
  const [filtreStatut, setFiltreStatut] = useState("");

  // Formulaire (création / édition).
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [submitting, setSubmitting] = useState(false);

  // Suppression confirmée.
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  // S3 — suppression bloquée (409 historique) → proposition d'archivage.
  const [archiveBlocked, setArchiveBlocked] = useState<number | null>(null);

  // S2 — mouvement (modal) + historique par bobine.
  const [mvt, setMvt] = useState<{
    bobineId: number;
    type: MouvementType;
  } | null>(null);
  const [mvtMl, setMvtMl] = useState("");
  const [mvtMotif, setMvtMotif] = useState("");
  const [mvtReference, setMvtReference] = useState("");
  const [mvtSubmitting, setMvtSubmitting] = useState(false);
  const [historyOf, setHistoryOf] = useState<number | null>(null);
  const [history, setHistory] = useState<MouvementOut[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const matiereById = useMemo(
    () => new Map(matieres.map((m) => [m.id, m])),
    [matieres],
  );
  const matiereLibelle = (id: number) => matiereById.get(id)?.libelle ?? `#${id}`;

  const reloadBobines = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listBobines({
        matiere_id: filtreMatiere ? Number(filtreMatiere) : undefined,
        rangee: filtreRangee.trim() || undefined,
        statut: (filtreStatut as BobineStatut) || undefined,
      });
      setBobines(data);
    } catch (err) {
      // Dégradation propre : liste vide, pas de crash.
      setBobines([]);
      toast({
        title: "Stock indisponible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [filtreMatiere, filtreRangee, filtreStatut, toast]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mats = await listMatieres();
        if (!cancelled) setMatieres(mats);
      } catch {
        /* le catalogue manquant n'empêche pas l'inventaire */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void reloadBobines();
  }, [reloadBobines]);

  // Matière choisie dans le formulaire → pré-remplit l'épaisseur (éditable).
  const onFormMatiere = (value: string) => {
    const mat = matieres.find((m) => m.id === Number(value));
    setForm((f) => ({
      ...f,
      matiere_id: value,
      epaisseur_microns:
        mat?.epaisseur_microns != null
          ? String(mat.epaisseur_microns)
          : f.epaisseur_microns,
    }));
  };

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm);
    setFormOpen(true);
  };
  const openEdit = (b: BobineOut) => {
    setEditingId(b.id);
    setForm(bobineToForm(b));
    setFormOpen(true);
  };
  const closeForm = () => {
    setFormOpen(false);
    setEditingId(null);
  };

  const formValide =
    form.matiere_id !== "" &&
    parseFloat(form.laize_mm) > 0 &&
    form.rangee.trim() !== "" &&
    form.etage.trim() !== "" &&
    form.position.trim() !== "";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!formValide) return;
    const payload: BobineCreate = {
      matiere_id: Number(form.matiere_id),
      laize_mm: parseInt(form.laize_mm, 10),
      epaisseur_microns: parseInt(form.epaisseur_microns, 10) || 0,
      ml_initial: parseFloat(form.ml_initial) || 0,
      ml_restant:
        form.ml_restant.trim() !== ""
          ? parseFloat(form.ml_restant)
          : parseFloat(form.ml_initial) || 0,
      rangee: form.rangee.trim(),
      etage: parseInt(form.etage, 10) || 0,
      position: parseInt(form.position, 10) || 0,
      statut: form.statut,
      date_reception: form.date_reception.trim() || null,
      fournisseur: form.fournisseur.trim() || null,
      reference_lot: form.reference_lot.trim() || null,
    };
    setSubmitting(true);
    try {
      if (editingId !== null) {
        // S2 — figés en édition : matiere_id / ml_initial / ml_restant (ce
        // dernier s'ajuste via un mouvement « inventaire », plus par PATCH).
        const {
          matiere_id: _m,
          ml_initial: _i,
          ml_restant: _r,
          ...editable
        } = payload;
        void _m;
        void _i;
        void _r;
        await updateBobine(editingId, editable);
        toast({ title: "Bobine modifiée ✓" });
      } else {
        await createBobine(payload);
        toast({ title: "Bobine ajoutée ✓" });
      }
      closeForm();
      await reloadBobines();
    } catch (err) {
      toast({
        title: "Enregistrement impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteBobine(id);
      setConfirmDeleteId(null);
      toast({ title: "Bobine supprimée ✓" });
      await reloadBobines();
    } catch (err) {
      // S3 — guard : bobine avec historique de mouvements → 409, on propose
      // l'archivage (statut « consommée ») plutôt que la suppression.
      if (err instanceof ApiError && err.status === 409) {
        setConfirmDeleteId(null);
        setArchiveBlocked(id);
        toast({
          title: "Suppression bloquée",
          description: "Bobine avec historique de mouvements — archive-la.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Suppression impossible",
          description: err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      }
    }
  };

  // S3 — archive une bobine (statut « consommée ») quand la suppression est
  // bloquée par son historique.
  const handleArchive = async (id: number) => {
    try {
      await updateBobine(id, { statut: "consommee" });
      setArchiveBlocked(null);
      toast({ title: "Bobine archivée ✓" });
      await reloadBobines();
    } catch (err) {
      toast({
        title: "Archivage impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  // S2 — ouvre le modal mouvement (entrée / sortie / inventaire).
  const openMvt = (bobineId: number, type: MouvementType) => {
    setMvt({ bobineId, type });
    setMvtMl("");
    setMvtMotif("");
    setMvtReference("");
  };

  const submitMvt = async (e: FormEvent) => {
    e.preventDefault();
    if (mvt === null) return;
    const ml = parseFloat(mvtMl);
    if (!(ml > 0)) return;
    setMvtSubmitting(true);
    try {
      const res = await createMouvement(mvt.bobineId, {
        type: mvt.type,
        ml,
        motif: mvtMotif.trim() || null,
        reference: mvtReference.trim() || null,
      });
      // Remplace la bobine par sa version à jour (ml_restant recalculé back).
      setBobines((list) =>
        list.map((b) => (b.id === res.bobine.id ? res.bobine : b)),
      );
      setMvt(null);
      toast({ title: `${MVT_LABELS[res.mouvement.type]} enregistrée ✓` });
      // Historique ouvert sur cette bobine → recharge.
      if (historyOf === mvt.bobineId) await loadHistory(mvt.bobineId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        toast({
          title: "Stock insuffisant",
          description: "La sortie dépasse le ml restant de la bobine.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Mouvement impossible",
          description: err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      }
    } finally {
      setMvtSubmitting(false);
    }
  };

  const loadHistory = async (bobineId: number) => {
    setHistoryLoading(true);
    try {
      setHistory(await listMouvementsBobine(bobineId));
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const toggleHistory = async (bobineId: number) => {
    if (historyOf === bobineId) {
      setHistoryOf(null);
      return;
    }
    setHistoryOf(bobineId);
    await loadHistory(bobineId);
  };

  // Rangées présentes (pour le filtre).
  const rangees = useMemo(
    () => Array.from(new Set(bobines.map((b) => b.rangee))).sort(),
    [bobines],
  );

  return (
    <main className="min-h-screen bg-[#FBF7F0]">
      <div className="mx-auto max-w-5xl space-y-5 p-4 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#E85D2F]">
              Stock — inventaire bobines
            </h1>
            <p className="text-sm text-muted-foreground">
              Emplacement = rangée.étage.position (ex. A.0.25). ml restant
              ajusté par mouvement (Entrée / Sortie / Ajuster).
            </p>
          </div>
          <Button
            type="button"
            onClick={openCreate}
            data-testid="stock-new"
            className="bg-[#E85D2F] text-white hover:bg-[#d24f24]"
          >
            + Ajouter une bobine
          </Button>
        </div>

        {/* ── Filtres ───────────────────────────────────────────────── */}
        <Card className="border-border bg-white shadow-sm">
          <CardContent className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Matière</Label>
              <select
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={filtreMatiere}
                onChange={(e) => setFiltreMatiere(e.target.value)}
                data-testid="filtre-matiere"
                aria-label="Filtrer par matière"
              >
                <option value="">Toutes</option>
                {matieres.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.libelle}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Rangée</Label>
              <select
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={filtreRangee}
                onChange={(e) => setFiltreRangee(e.target.value)}
                data-testid="filtre-rangee"
                aria-label="Filtrer par rangée"
              >
                <option value="">Toutes</option>
                {rangees.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Statut</Label>
              <select
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={filtreStatut}
                onChange={(e) => setFiltreStatut(e.target.value)}
                data-testid="filtre-statut"
                aria-label="Filtrer par statut"
              >
                <option value="">Tous</option>
                {STATUTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>

        {/* ── Formulaire création / édition ─────────────────────────── */}
        {formOpen && (
          <Card className="border-[#E85D2F]/30 bg-white shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {editingId !== null
                  ? "Modifier la bobine"
                  : "Ajouter une bobine"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={handleSubmit}
                className="grid grid-cols-1 gap-3 sm:grid-cols-3"
              >
                <Field label="Matière *">
                  <select
                    className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={form.matiere_id}
                    onChange={(e) => onFormMatiere(e.target.value)}
                    disabled={editingId !== null}
                    data-testid="f-matiere"
                    aria-label="Matière"
                  >
                    <option value="">— Choisir —</option>
                    {matieres.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.libelle}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Laize (mm) *">
                  <Input
                    type="number"
                    min={1}
                    value={form.laize_mm}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, laize_mm: e.target.value }))
                    }
                    data-testid="f-laize"
                  />
                </Field>
                <Field label="Épaisseur (µm)">
                  <Input
                    type="number"
                    min={1}
                    value={form.epaisseur_microns}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        epaisseur_microns: e.target.value,
                      }))
                    }
                    data-testid="f-epaisseur"
                  />
                </Field>
                <Field label="ml initial">
                  <Input
                    type="number"
                    min={0}
                    value={form.ml_initial}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, ml_initial: e.target.value }))
                    }
                    disabled={editingId !== null}
                    data-testid="f-ml-initial"
                  />
                </Field>
                <Field
                  label={
                    editingId !== null
                      ? "ml restant (via mouvement)"
                      : "ml restant"
                  }
                >
                  <Input
                    type="number"
                    min={0}
                    value={form.ml_restant}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, ml_restant: e.target.value }))
                    }
                    placeholder="défaut = ml initial"
                    disabled={editingId !== null}
                    data-testid="f-ml-restant"
                  />
                  {editingId !== null && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Ajuste le stock via « Entrée / Sortie / Ajuster » sur la
                      ligne.
                    </p>
                  )}
                </Field>
                <Field label="Statut">
                  <select
                    className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={form.statut}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        statut: e.target.value as BobineStatut,
                      }))
                    }
                    data-testid="f-statut"
                    aria-label="Statut"
                  >
                    {STATUTS.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Rangée *">
                  <Input
                    value={form.rangee}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, rangee: e.target.value }))
                    }
                    placeholder="A"
                    data-testid="f-rangee"
                  />
                </Field>
                <Field label="Étage *">
                  <Input
                    type="number"
                    min={0}
                    value={form.etage}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, etage: e.target.value }))
                    }
                    placeholder="0"
                    data-testid="f-etage"
                  />
                </Field>
                <Field label="Position *">
                  <Input
                    type="number"
                    min={0}
                    value={form.position}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, position: e.target.value }))
                    }
                    placeholder="25"
                    data-testid="f-position"
                  />
                </Field>
                <Field label="Fournisseur">
                  <Input
                    value={form.fournisseur}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, fournisseur: e.target.value }))
                    }
                    data-testid="f-fournisseur"
                  />
                </Field>
                <Field label="Réf. lot">
                  <Input
                    value={form.reference_lot}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, reference_lot: e.target.value }))
                    }
                    data-testid="f-reference-lot"
                  />
                </Field>
                <Field label="Date réception">
                  <Input
                    type="date"
                    value={form.date_reception}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        date_reception: e.target.value,
                      }))
                    }
                    data-testid="f-date-reception"
                  />
                </Field>
                <div className="flex items-end gap-2 sm:col-span-3">
                  <Button
                    type="submit"
                    disabled={!formValide || submitting}
                    data-testid="f-submit"
                    className="bg-[#E85D2F] text-white hover:bg-[#d24f24] disabled:opacity-50"
                  >
                    {submitting
                      ? "Enregistrement…"
                      : editingId !== null
                        ? "Enregistrer"
                        : "Ajouter"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={closeForm}
                    data-testid="f-cancel"
                  >
                    Annuler
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* ── Liste ─────────────────────────────────────────────────── */}
        <Card className="border-border bg-white shadow-sm">
          <CardContent className="p-0">
            {loading ? (
              <p className="p-4 text-sm text-muted-foreground">Chargement…</p>
            ) : bobines.length === 0 ? (
              <p
                data-testid="stock-vide"
                className="p-4 text-sm text-muted-foreground"
              >
                Aucune bobine en stock pour ces filtres.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs text-muted-foreground">
                      <th className="p-3">Matière</th>
                      <th className="p-3">Laize</th>
                      <th className="p-3">Emplacement</th>
                      <th className="p-3">ml restant</th>
                      <th className="p-3">Statut</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bobines.map((b) => (
                      <Fragment key={b.id}>
                        <tr
                          data-testid={`stock-row-${b.id}`}
                          className="border-b border-border"
                        >
                          <td className="p-3">
                            {matiereLibelle(b.matiere_id)}
                          </td>
                          <td className="p-3">{b.laize_mm} mm</td>
                          <td className="p-3 font-mono">
                            {b.emplacement ||
                              `${b.rangee}.${b.etage}.${b.position}`}
                          </td>
                          <td className="p-3" data-testid={`ml-restant-${b.id}`}>
                            {b.ml_restant.toLocaleString("fr-FR", {
                              maximumFractionDigits: 0,
                            })}{" "}
                            ml
                          </td>
                          <td className="p-3">
                            <span
                              className={
                                "rounded px-2 py-0.5 text-xs font-medium " +
                                STATUT_CLASS[b.statut]
                              }
                            >
                              {statutLabel(b.statut)}
                            </span>
                          </td>
                          <td className="p-3">
                            <div className="flex flex-wrap items-center justify-end gap-2 text-xs">
                              <button
                                type="button"
                                onClick={() => openMvt(b.id, "entree")}
                                data-testid={`mvt-entree-${b.id}`}
                                className="rounded border border-emerald-300 px-2 py-1 font-medium text-emerald-800 hover:bg-emerald-50"
                              >
                                Entrée
                              </button>
                              <button
                                type="button"
                                onClick={() => openMvt(b.id, "sortie")}
                                data-testid={`mvt-sortie-${b.id}`}
                                className="rounded border border-amber-300 px-2 py-1 font-medium text-amber-800 hover:bg-amber-50"
                              >
                                Sortie
                              </button>
                              <button
                                type="button"
                                onClick={() => openMvt(b.id, "inventaire")}
                                data-testid={`mvt-ajuster-${b.id}`}
                                className="rounded border border-border px-2 py-1 font-medium hover:bg-muted/50"
                              >
                                Ajuster
                              </button>
                              <button
                                type="button"
                                onClick={() => toggleHistory(b.id)}
                                data-testid={`hist-${b.id}`}
                                aria-expanded={
                                  historyOf === b.id ? "true" : "false"
                                }
                                className="text-muted-foreground hover:text-foreground"
                              >
                                Historique
                              </button>
                              <button
                                type="button"
                                onClick={() => openEdit(b)}
                                data-testid={`edit-${b.id}`}
                                className="font-semibold text-[#B8431D]"
                              >
                                Éditer
                              </button>
                              {archiveBlocked === b.id ? (
                                <span className="inline-flex items-center gap-2 text-amber-800">
                                  Historique — archiver ?
                                  <button
                                    type="button"
                                    onClick={() => handleArchive(b.id)}
                                    data-testid={`archive-${b.id}`}
                                    className="font-semibold text-[#B8431D]"
                                  >
                                    Archiver
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setArchiveBlocked(null)}
                                    className="text-muted-foreground"
                                  >
                                    Non
                                  </button>
                                </span>
                              ) : confirmDeleteId === b.id ? (
                                <span className="inline-flex items-center gap-2">
                                  Supprimer ?
                                  <button
                                    type="button"
                                    onClick={() => handleDelete(b.id)}
                                    data-testid={`del-confirm-${b.id}`}
                                    className="font-semibold text-red-600"
                                  >
                                    Oui
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setConfirmDeleteId(null)}
                                    className="text-muted-foreground"
                                  >
                                    Non
                                  </button>
                                </span>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => setConfirmDeleteId(b.id)}
                                  data-testid={`del-${b.id}`}
                                  className="text-muted-foreground hover:text-red-600"
                                  aria-label="Supprimer"
                                >
                                  ✕
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                        {historyOf === b.id && (
                          <tr
                            data-testid={`hist-row-${b.id}`}
                            className="border-b border-border bg-muted/30"
                          >
                            <td colSpan={6} className="p-3">
                              <p className="mb-1 text-xs font-semibold text-muted-foreground">
                                Historique des mouvements
                              </p>
                              {historyLoading ? (
                                <p className="text-xs text-muted-foreground">
                                  Chargement…
                                </p>
                              ) : history.length === 0 ? (
                                <p className="text-xs text-muted-foreground">
                                  Aucun mouvement enregistré.
                                </p>
                              ) : (
                                <ul className="space-y-1 text-xs">
                                  {history.map((m) => (
                                    <li
                                      key={m.id}
                                      className="flex flex-wrap gap-x-3"
                                    >
                                      <span className="font-semibold">
                                        {MVT_LABELS[m.type]}
                                      </span>
                                      <span className="font-mono">
                                        {m.ml} ml
                                      </span>
                                      <span className="text-muted-foreground">
                                        {new Date(m.date).toLocaleString(
                                          "fr-FR",
                                        )}
                                      </span>
                                      {m.motif && (
                                        <span className="text-muted-foreground">
                                          · {m.motif}
                                        </span>
                                      )}
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Modal mouvement (entrée / sortie / inventaire) ────────── */}
        {mvt && (
          <div
            data-testid="mvt-modal"
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          >
            <Card className="w-full max-w-md border-[#E85D2F]/30 bg-white shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">
                  {MVT_LABELS[mvt.type]} — bobine #{mvt.bobineId}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={submitMvt} className="space-y-3">
                  <Field label={`${MVT_ML_LABEL[mvt.type]} *`}>
                    <Input
                      type="number"
                      min={0.1}
                      step="0.1"
                      value={mvtMl}
                      onChange={(e) => setMvtMl(e.target.value)}
                      data-testid="mvt-ml"
                      autoFocus
                    />
                  </Field>
                  <Field label="Motif">
                    <Input
                      value={mvtMotif}
                      onChange={(e) => setMvtMotif(e.target.value)}
                      placeholder="optionnel"
                      data-testid="mvt-motif"
                    />
                  </Field>
                  <Field label="Référence">
                    <Input
                      value={mvtReference}
                      onChange={(e) => setMvtReference(e.target.value)}
                      placeholder="optionnel"
                      data-testid="mvt-reference"
                    />
                  </Field>
                  <div className="flex gap-2 pt-1">
                    <Button
                      type="submit"
                      disabled={!(parseFloat(mvtMl) > 0) || mvtSubmitting}
                      data-testid="mvt-submit"
                      className="bg-[#E85D2F] text-white hover:bg-[#d24f24] disabled:opacity-50"
                    >
                      {mvtSubmitting ? "Enregistrement…" : "Valider"}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setMvt(null)}
                      data-testid="mvt-cancel"
                    >
                      Annuler
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </main>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}
