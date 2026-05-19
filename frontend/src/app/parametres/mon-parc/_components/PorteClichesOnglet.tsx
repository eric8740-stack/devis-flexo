"use client";

/**
 * Onglet "Mes porte-clichés" — refonte Brief #30.
 *
 * Refonte vs Brief #29 : sémantique métier corrigée. Un porte-cliché en
 * flexo étroite est un cyl engrenage synchronisé au cyl magnétique. 1 PC
 * par couple (machine × cyl mag), `quantite` = exemplaires identiques
 * montés simultanément (= nb_groupes_couleurs de la machine en pratique).
 *
 * UX :
 *   - Dropdown machine en haut filtre la liste (default = première active).
 *   - Cards : nb_dents en gros (titre), quantité en sous-titre.
 *   - Dialog ajout : dropdowns machine + cyl + quantite (default
 *     = machine.nb_groupes_couleurs).
 *   - Dialog modif : input quantité uniquement (machine_id + cylindre_id
 *     sont identifiants, non modifiables).
 *   - Toggle actif coloré réutilisé depuis CylindresOnglet (SACRED layout).
 */
import { useEffect, useMemo, useState } from "react";

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
import { useToast } from "@/hooks/use-toast";
import {
  createPorteCliche,
  deletePorteCliche,
  listCylindres,
  listMachines,
  listPorteCliches,
  toggleActifPorteCliche,
  updatePorteCliche,
  type CylindreParc,
  type Machine,
  type PorteCliche,
} from "@/lib/api";

import { ToggleActif } from "./CylindresOnglet";

const FALLBACK_NB_COULEURS = 8;

export function PorteClichesOnglet() {
  const { toast } = useToast();
  const [items, setItems] = useState<PorteCliche[] | null>(null);
  const [machines, setMachines] = useState<Machine[] | null>(null);
  const [cylindres, setCylindres] = useState<CylindreParc[] | null>(null);
  const [machineFilter, setMachineFilter] = useState<number | null>(null);
  const [voirInactifs, setVoirInactifs] = useState(false);
  const [dialogOuvert, setDialogOuvert] = useState(false);
  const [enCoursModif, setEnCoursModif] = useState<PorteCliche | null>(null);

  // Chargement initial : machines + cylindres actifs (référentiels) +
  // items selon filtre courant.
  useEffect(() => {
    let cancelled = false;
    Promise.all([listMachines(), listCylindres(true)])
      .then(([m, c]) => {
        if (cancelled) return;
        setMachines(m);
        setCylindres(c);
        // Auto-sélection : 1ère machine active pour pré-filtrer la liste.
        if (machineFilter === null && m.length > 0) {
          setMachineFilter(m[0].id);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        toast({
          title: "Chargement référentiels impossible",
          description: err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rafraichir = async () => {
    try {
      const data = await listPorteCliches({
        actif: voirInactifs ? null : true,
        machine_id: machineFilter ?? undefined,
      });
      setItems(data);
    } catch (err) {
      toast({
        title: "Chargement impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    if (machineFilter !== null) rafraichir();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [machineFilter, voirInactifs]);

  const machineActive = useMemo(
    () => (machines ?? []).find((m) => m.id === machineFilter) ?? null,
    [machines, machineFilter]
  );

  const ouvrirAjout = () => {
    setEnCoursModif(null);
    setDialogOuvert(true);
  };

  const ouvrirModif = (pc: PorteCliche) => {
    setEnCoursModif(pc);
    setDialogOuvert(true);
  };

  const handleToggle = async (pc: PorteCliche) => {
    try {
      await toggleActifPorteCliche(pc.id);
      await rafraichir();
    } catch (err) {
      toast({
        title: "Toggle impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const handleSupprimer = async (pc: PorteCliche) => {
    if (
      !confirm(
        `Désactiver le porte-cliché pour ${pc.machine_nom} · cyl ${pc.cylindre_nb_dents} dents ? Il restera en base, juste masqué. Tu pourras le réactiver à tout moment.`
      )
    ) {
      return;
    }
    try {
      await deletePorteCliche(pc.id);
      toast({ title: "Porte-cliché désactivé" });
      await rafraichir();
    } catch (err) {
      toast({
        title: "Désactivation impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const nbActifs = (items ?? []).filter((i) => i.actif).length;
  const nbInactifs = (items ?? []).filter((i) => !i.actif).length;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-muted-foreground">
          Cylindres engrenage synchronisés à tes cyls magnétiques. Un par
          couple machine × cylindre, quantité = nombre de couleurs montées.
        </div>
        <Button
          onClick={ouvrirAjout}
          className="bg-gradient-to-r from-amber-600 to-blue-700 text-white shadow hover:from-amber-700 hover:to-blue-800"
        >
          + Ajouter un porte-cliché
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-md border border-border bg-muted/30 p-3 text-sm">
        <label className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Machine</span>
          <select
            className="rounded border border-input bg-background px-2 py-1 text-sm"
            value={machineFilter ?? ""}
            onChange={(e) =>
              setMachineFilter(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">Toutes</option>
            {(machines ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.nom}
                {m.nb_couleurs ? ` (${m.nb_couleurs} couleurs)` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="flex cursor-pointer items-center gap-1.5">
          <input
            type="checkbox"
            checked={voirInactifs}
            onChange={(e) => setVoirInactifs(e.target.checked)}
            className="h-4 w-4 accent-foreground"
          />
          <span>Voir aussi les désactivés</span>
        </label>
      </div>

      {items === null && (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      )}

      {items !== null && items.length === 0 && (
        <EtatVide
          machineNom={machineActive?.nom ?? null}
          onAjouter={ouvrirAjout}
        />
      )}

      <div className="space-y-2">
        {(items ?? []).map((pc) => (
          <PorteClicheCard
            key={pc.id}
            pc={pc}
            onToggle={() => handleToggle(pc)}
            onModifier={() => ouvrirModif(pc)}
            onSupprimer={() => handleSupprimer(pc)}
          />
        ))}
      </div>

      {items !== null && items.length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 font-medium text-emerald-900">
            ✓ {nbActifs} actif{nbActifs > 1 ? "s" : ""}
          </span>
          {nbInactifs > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-gray-200 px-3 py-1 font-medium text-gray-700">
              {nbInactifs} désactivé{nbInactifs > 1 ? "s" : ""}
            </span>
          )}
        </div>
      )}

      <PorteClicheDialog
        ouvert={dialogOuvert}
        onClose={() => setDialogOuvert(false)}
        pc={enCoursModif}
        machines={machines ?? []}
        cylindres={cylindres ?? []}
        machinePreselectionnee={machineActive}
        onSucces={async () => {
          setDialogOuvert(false);
          await rafraichir();
        }}
      />
    </section>
  );
}

function PorteClicheCard({
  pc,
  onToggle,
  onModifier,
  onSupprimer,
}: {
  pc: PorteCliche;
  onToggle: () => void;
  onModifier: () => void;
  onSupprimer: () => void;
}) {
  return (
    <div
      className={
        "rounded-lg border-l-4 bg-white p-4 shadow-sm transition-all " +
        (pc.actif
          ? "border-l-amber-600 border-y border-r border-y-border border-r-border hover:-translate-y-0.5 hover:shadow-md"
          : "border-l-gray-300 border-y border-r border-y-border border-r-border bg-muted/30 opacity-60")
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-base font-semibold text-ink">
              🔧 {pc.cylindre_nb_dents} dents
            </span>
            <span className="text-sm text-muted-foreground">
              Z = {pc.cylindre_developpe_mm} mm
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            <strong>{pc.quantite}</strong> porte-cliché
            {pc.quantite > 1 ? "s" : ""} disponible
            {pc.quantite > 1 ? "s" : ""} · synchro avec cyl mag{" "}
            {pc.cylindre_nb_dents} dents · sur {pc.machine_nom}
          </p>
          {pc.notes && (
            <p className="mt-1 text-xs text-muted-foreground italic">
              {pc.notes}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ToggleActif actif={pc.actif} onToggle={onToggle} />
          <Button
            size="sm"
            onClick={onModifier}
            className="bg-blue-700 text-white hover:bg-blue-800"
          >
            Modifier qté
          </Button>
          {pc.actif && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onSupprimer}
              className="text-amber-800 hover:bg-amber-50 hover:text-amber-900"
            >
              Désactiver
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function EtatVide({
  machineNom,
  onAjouter,
}: {
  machineNom: string | null;
  onAjouter: () => void;
}) {
  return (
    <div className="rounded-xl border-2 border-dashed border-amber-200 bg-gradient-to-br from-amber-50/60 to-blue-50/40 p-10 text-center">
      <div className="mb-3 text-5xl">📐</div>
      <p className="text-base font-medium text-ink">
        {machineNom
          ? `Pas encore de porte-cliché pour ${machineNom}`
          : "Pas encore de porte-cliché"}
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        Ajoutes-en un en 30 secondes — la quantité par défaut est le nombre
        de couleurs de la machine.
      </p>
      <Button
        size="lg"
        className="mt-5 bg-gradient-to-r from-amber-600 to-blue-700 px-6 text-white shadow hover:from-amber-700 hover:to-blue-800"
        onClick={onAjouter}
      >
        + Ajouter mon premier porte-cliché
      </Button>
    </div>
  );
}

function PorteClicheDialog({
  ouvert,
  onClose,
  pc,
  machines,
  cylindres,
  machinePreselectionnee,
  onSucces,
}: {
  ouvert: boolean;
  onClose: () => void;
  pc: PorteCliche | null;
  machines: Machine[];
  cylindres: CylindreParc[];
  machinePreselectionnee: Machine | null;
  onSucces: () => Promise<void>;
}) {
  const { toast } = useToast();
  const enModif = pc !== null;

  const [machineId, setMachineId] = useState<string>("");
  const [cylindreId, setCylindreId] = useState<string>("");
  const [quantite, setQuantite] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  // Default quantite = nb_couleurs de la machine sélectionnée (création).
  const machineSelectionnee = useMemo(
    () =>
      machines.find((m) => m.id === parseInt(machineId, 10)) ??
      machinePreselectionnee ??
      null,
    [machines, machineId, machinePreselectionnee]
  );
  const quantiteDefault =
    machineSelectionnee?.nb_couleurs ?? FALLBACK_NB_COULEURS;

  useEffect(() => {
    if (!ouvert) return;
    if (pc) {
      setMachineId(String(pc.machine_id));
      setCylindreId(String(pc.cylindre_id));
      setQuantite(String(pc.quantite));
      setNotes(pc.notes ?? "");
    } else {
      setMachineId(machinePreselectionnee ? String(machinePreselectionnee.id) : "");
      setCylindreId("");
      setQuantite("");
      setNotes("");
    }
  }, [ouvert, pc, machinePreselectionnee]);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      if (enModif && pc) {
        const qty = quantite ? parseInt(quantite, 10) : pc.quantite;
        await updatePorteCliche(pc.id, {
          quantite: qty,
          notes: notes || null,
        });
        toast({ title: "Porte-cliché modifié" });
      } else {
        const mid = parseInt(machineId, 10);
        const cid = parseInt(cylindreId, 10);
        if (!Number.isFinite(mid) || !Number.isFinite(cid)) {
          toast({
            title: "Sélection incomplète",
            description: "Choisis une machine et un cylindre.",
            variant: "destructive",
          });
          setSubmitting(false);
          return;
        }
        const qty = quantite ? parseInt(quantite, 10) : undefined;
        await createPorteCliche({
          machine_id: mid,
          cylindre_id: cid,
          quantite: qty,
          notes: notes || null,
        });
        toast({
          title: "Porte-cliché ajouté",
          description: "Disponible pour tes prochains devis.",
        });
      }
      await onSucces();
    } catch (err) {
      toast({
        title: enModif ? "Modification impossible" : "Ajout impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={ouvert} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {enModif ? "Modifier la quantité" : "Ajouter un porte-cliché"}
          </DialogTitle>
          <DialogDescription>
            {enModif
              ? "Tu peux ajuster la quantité d'exemplaires et les notes. La machine et le cylindre ne sont pas modifiables — pour changer de couple, ajoute un nouveau porte-cliché et désactive l'ancien."
              : "Un porte-cliché est synchronisé à un cylindre magnétique par son engrenage. La quantité par défaut = nombre de couleurs de la machine."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {!enModif && (
            <>
              <div className="space-y-2">
                <Label htmlFor="pc-machine">Machine</Label>
                <select
                  id="pc-machine"
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={machineId}
                  onChange={(e) => setMachineId(e.target.value)}
                >
                  <option value="">— Choisis une machine —</option>
                  {machines.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.nom}
                      {m.nb_couleurs ? ` (${m.nb_couleurs} couleurs)` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="pc-cylindre">Cylindre magnétique</Label>
                <select
                  id="pc-cylindre"
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={cylindreId}
                  onChange={(e) => setCylindreId(e.target.value)}
                >
                  <option value="">— Choisis un cylindre —</option>
                  {cylindres.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nb_dents} dents · Z = {c.developpe_mm} mm
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          {enModif && pc && (
            <div className="rounded border border-border bg-muted/30 p-3 text-xs">
              <p>
                <strong>{pc.machine_nom}</strong> · cyl{" "}
                {pc.cylindre_nb_dents} dents
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="pc-qte">
              Quantité {!enModif && `(default ${quantiteDefault})`}
            </Label>
            <Input
              id="pc-qte"
              type="number"
              min={0}
              max={99}
              value={quantite}
              onChange={(e) => setQuantite(e.target.value)}
              placeholder={!enModif ? String(quantiteDefault) : ""}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="pc-notes">Notes (optionnel)</Label>
            <Input
              id="pc-notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Repère atelier, état d'usure, etc."
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Annuler
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting
              ? "Enregistrement…"
              : enModif
                ? "Enregistrer"
                : "Ajouter"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
