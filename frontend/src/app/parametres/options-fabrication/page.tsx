"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import {
  createOptionFromMaster,
  deleteOptionFabrication,
  getOnboardingCatalogueDefaults,
  listOptionsFabrication,
  updateOptionFabrication,
  type OnboardingOptionDefault,
  type OptionFabricationTenant,
  type OptionFabricationUpdatePayload,
} from "@/lib/api";

function formatFacturation(opt: OptionFabricationTenant): string {
  const parts: string[] = [];
  if (opt.forfait_eur && Number(opt.forfait_eur) > 0)
    parts.push(`Forfait ${opt.forfait_eur} €`);
  if (opt.prix_au_m2_eur && Number(opt.prix_au_m2_eur) > 0)
    parts.push(`${opt.prix_au_m2_eur} €/m²`);
  if (opt.prix_au_mille_eur && Number(opt.prix_au_mille_eur) > 0)
    parts.push(`${opt.prix_au_mille_eur} €/mille`);
  if (opt.cout_consommable_eur && Number(opt.cout_consommable_eur) > 0)
    parts.push(`Conso ${opt.cout_consommable_eur} €`);
  return parts.length ? parts.join(" · ") : "—";
}

export default function OptionsFabricationPage() {
  const { toast } = useToast();

  const [options, setOptions] = useState<OptionFabricationTenant[] | null>(
    null
  );
  const [master, setMaster] = useState<OnboardingOptionDefault[] | null>(null);
  const [editing, setEditing] = useState<OptionFabricationTenant | null>(null);
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    const [tenant, cat] = await Promise.all([
      listOptionsFabrication(),
      getOnboardingCatalogueDefaults(),
    ]);
    setOptions(tenant);
    setMaster(cat.options);
  }, []);

  useEffect(() => {
    load().catch((err) => {
      toast({
        title: "Chargement impossible",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    });
  }, [load, toast]);

  const codesAjoutables = useMemo(() => {
    if (!master || !options) return [];
    const present = new Set(options.map((o) => o.code));
    return master.filter((m) => !present.has(m.code));
  }, [master, options]);

  const handleToggleActif = useCallback(
    async (opt: OptionFabricationTenant) => {
      try {
        await updateOptionFabrication(opt.id, { actif: !opt.actif });
        await load();
      } catch (err) {
        toast({
          title: "Mise à jour impossible",
          description: err instanceof Error ? err.message : String(err),
          variant: "destructive",
        });
      }
    },
    [load, toast]
  );

  const handleAdd = useCallback(
    async (code: string) => {
      try {
        await createOptionFromMaster(code);
        await load();
        setAdding(false);
        toast({ title: "Option ajoutée", description: code });
      } catch (err) {
        toast({
          title: "Ajout impossible",
          description: err instanceof Error ? err.message : String(err),
          variant: "destructive",
        });
      }
    },
    [load, toast]
  );

  const handleSaveEdition = useCallback(
    async (id: number, payload: OptionFabricationUpdatePayload) => {
      try {
        await updateOptionFabrication(id, payload);
        await load();
        setEditing(null);
        toast({ title: "Option mise à jour" });
      } catch (err) {
        toast({
          title: "Sauvegarde impossible",
          description: err instanceof Error ? err.message : String(err),
          variant: "destructive",
        });
      }
    },
    [load, toast]
  );

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await deleteOptionFabrication(id);
        await load();
        setEditing(null);
        toast({ title: "Option désactivée" });
      } catch (err) {
        toast({
          title: "Suppression impossible",
          description: err instanceof Error ? err.message : String(err),
          variant: "destructive",
        });
      }
    },
    [load, toast]
  );

  if (options === null || master === null) {
    return <p className="text-sm text-muted-foreground">Chargement…</p>;
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          Active les options de fabrication proposées par tes presses. Le moteur
          d&apos;optimisation n&apos;utilisera que les options listées ici (et
          actives). La désactivation est réversible : les devis passés
          conservent leur snapshot.
        </p>
        <Button
          type="button"
          onClick={() => setAdding(true)}
          disabled={codesAjoutables.length === 0}
        >
          Ajouter une option du catalogue
        </Button>
      </div>

      {options.length === 0 ? (
        <p className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          Aucune option activée pour le moment. Clique sur « Ajouter une option
          du catalogue » pour piocher dans les 21 options Sprint 13.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Libellé</TableHead>
              <TableHead>Catégorie</TableHead>
              <TableHead className="text-right">Coef vitesse</TableHead>
              <TableHead className="text-right">Coef gâche</TableHead>
              <TableHead>Facturation</TableHead>
              <TableHead className="text-center">Actif</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {options.map((opt) => (
              <TableRow
                key={opt.id}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => setEditing(opt)}
              >
                <TableCell className="font-medium">{opt.libelle}</TableCell>
                <TableCell className="text-muted-foreground">
                  {opt.categorie ?? "—"}
                </TableCell>
                <TableCell className="text-right">
                  ×{Number(opt.coef_vitesse_impact).toFixed(2)}
                </TableCell>
                <TableCell className="text-right">
                  ×{Number(opt.coef_gache_impact).toFixed(2)}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatFacturation(opt)}
                </TableCell>
                <TableCell
                  className="text-center"
                  onClick={(e) => e.stopPropagation()}
                >
                  <label className="inline-flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={opt.actif}
                      onChange={() => void handleToggleActif(opt)}
                      className="h-4 w-4 cursor-pointer accent-foreground"
                    />
                  </label>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <AddOptionDialog
        open={adding}
        onOpenChange={setAdding}
        codes={codesAjoutables}
        onPick={(code) => void handleAdd(code)}
      />

      {editing && (
        <EditOptionDialog
          option={editing}
          onClose={() => setEditing(null)}
          onSave={(payload) => void handleSaveEdition(editing.id, payload)}
          onDelete={() => void handleDelete(editing.id)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dialog : ajouter une option depuis le catalogue master
// ---------------------------------------------------------------------------

interface AddOptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  codes: OnboardingOptionDefault[];
  onPick: (code: string) => void;
}

function AddOptionDialog({
  open,
  onOpenChange,
  codes,
  onPick,
}: AddOptionDialogProps) {
  const [selected, setSelected] = useState<string>("");
  const detail = useMemo(
    () => codes.find((c) => c.code === selected) ?? null,
    [codes, selected]
  );

  useEffect(() => {
    if (!open) setSelected("");
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ajouter une option du catalogue</DialogTitle>
          <DialogDescription>
            Sélectionne une option non encore activée pour ton entreprise. Les
            coefs et modules requis seront copiés depuis le catalogue Sprint
            13 ; tu pourras ensuite ajuster les coefs et renseigner la
            tarification.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <Label htmlFor="pick-option">Option à activer</Label>
          <select
            id="pick-option"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">— Choisis une option —</option>
            {codes.map((c) => (
              <option key={c.code} value={c.code}>
                {c.libelle}
                {c.categorie ? ` (${c.categorie})` : ""}
              </option>
            ))}
          </select>
          {detail && detail.description && (
            <p className="text-xs text-muted-foreground">{detail.description}</p>
          )}
          {detail && (
            <p className="text-xs text-muted-foreground">
              Coefs recommandés : vitesse ×{detail.coef_vitesse_impact ?? 1.0}{" "}
              · gâche ×{detail.coef_gache_impact ?? 1.0}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Annuler
          </Button>
          <Button
            type="button"
            disabled={!selected}
            onClick={() => selected && onPick(selected)}
          >
            Activer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Dialog : éditer une option tenant
// ---------------------------------------------------------------------------

interface EditOptionDialogProps {
  option: OptionFabricationTenant;
  onClose: () => void;
  onSave: (payload: OptionFabricationUpdatePayload) => void;
  onDelete: () => void;
}

function EditOptionDialog({
  option,
  onClose,
  onSave,
  onDelete,
}: EditOptionDialogProps) {
  const [coefVit, setCoefVit] = useState(option.coef_vitesse_impact);
  const [coefGac, setCoefGac] = useState(option.coef_gache_impact);
  const [forfait, setForfait] = useState(option.forfait_eur ?? "");
  const [prixM2, setPrixM2] = useState(option.prix_au_m2_eur ?? "");
  const [prixMille, setPrixMille] = useState(option.prix_au_mille_eur ?? "");
  const [coutConso, setCoutConso] = useState(option.cout_consommable_eur ?? "");

  const rec = option.valeur_recommandee_origine;

  const submit = () => {
    const payload: OptionFabricationUpdatePayload = {
      coef_vitesse_impact: coefVit,
      coef_gache_impact: coefGac,
      forfait_eur: forfait === "" ? null : forfait,
      prix_au_m2_eur: prixM2 === "" ? null : prixM2,
      prix_au_mille_eur: prixMille === "" ? null : prixMille,
      cout_consommable_eur: coutConso === "" ? null : coutConso,
    };
    onSave(payload);
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{option.libelle}</DialogTitle>
          <DialogDescription>
            {option.description ?? "Édite coefficients et tarification."}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1">
              <Label htmlFor="coef-vit">Coef vitesse</Label>
              <Input
                id="coef-vit"
                type="number"
                step="0.01"
                value={coefVit}
                onChange={(e) => setCoefVit(e.target.value)}
              />
              {rec && (
                <span className="text-xs text-muted-foreground">
                  recommandé : {rec.coef_vitesse_impact.toFixed(2)}
                </span>
              )}
            </div>
            <div className="grid gap-1">
              <Label htmlFor="coef-gac">Coef gâche</Label>
              <Input
                id="coef-gac"
                type="number"
                step="0.01"
                value={coefGac}
                onChange={(e) => setCoefGac(e.target.value)}
              />
              {rec && (
                <span className="text-xs text-muted-foreground">
                  recommandé : {rec.coef_gache_impact.toFixed(2)}
                </span>
              )}
            </div>
          </div>

          <div>
            <h4 className="mb-2 text-sm font-semibold">Tarification</h4>
            <p className="mb-3 text-xs text-muted-foreground">
              Remplis uniquement les champs qui s&apos;appliquent à cette option
              (ex. forfait ET conso pour la dorure, prix au m² pour le
              pelliculage).
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1">
                <Label htmlFor="forfait">Forfait (€)</Label>
                <Input
                  id="forfait"
                  type="number"
                  step="0.01"
                  min="0"
                  value={forfait}
                  onChange={(e) => setForfait(e.target.value)}
                />
              </div>
              <div className="grid gap-1">
                <Label htmlFor="prix-m2">Prix au m² (€)</Label>
                <Input
                  id="prix-m2"
                  type="number"
                  step="0.0001"
                  min="0"
                  value={prixM2}
                  onChange={(e) => setPrixM2(e.target.value)}
                />
              </div>
              <div className="grid gap-1">
                <Label htmlFor="prix-mille">Prix au mille (€)</Label>
                <Input
                  id="prix-mille"
                  type="number"
                  step="0.01"
                  min="0"
                  value={prixMille}
                  onChange={(e) => setPrixMille(e.target.value)}
                />
              </div>
              <div className="grid gap-1">
                <Label htmlFor="cout-conso">Coût consommable (€)</Label>
                <Input
                  id="cout-conso"
                  type="number"
                  step="0.01"
                  min="0"
                  value={coutConso}
                  onChange={(e) => setCoutConso(e.target.value)}
                />
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="flex !justify-between">
          <Button type="button" variant="outline" onClick={onDelete}>
            Désactiver
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
            <Button type="button" onClick={submit}>
              Enregistrer
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
