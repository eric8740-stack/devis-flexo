"use client";

/**
 * Onglet "Mes porte-clichés" — Brief #29.
 *
 * Même UX que CylindresOnglet : cards aérées, toggle actif coloré,
 * dialog ajout/modif. Champs métier porte-cliché (reference unique,
 * marque/modele optionnels, laize_utile_mm obligatoire, matière, etc.).
 */
import { useEffect, useState } from "react";

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
  listPorteCliches,
  toggleActifPorteCliche,
  updatePorteCliche,
  type PorteCliche,
} from "@/lib/api";

import { ToggleActif } from "./CylindresOnglet";

export function PorteClichesOnglet() {
  const { toast } = useToast();
  const [items, setItems] = useState<PorteCliche[] | null>(null);
  const [voirInactifs, setVoirInactifs] = useState(false);
  const [recherche, setRecherche] = useState("");
  const [dialogOuvert, setDialogOuvert] = useState(false);
  const [enCoursModif, setEnCoursModif] = useState<PorteCliche | null>(null);

  const rafraichir = async () => {
    try {
      const data = await listPorteCliches(voirInactifs ? null : true);
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
    rafraichir();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voirInactifs]);

  const ouvrirAjout = () => {
    setEnCoursModif(null);
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
        `Désactiver le porte-cliché ${pc.reference} ? Il restera en base, juste masqué.`
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

  const itemsAffiches = (items ?? []).filter((p) => {
    if (!recherche) return true;
    const q = recherche.toLowerCase();
    return (
      p.reference.toLowerCase().includes(q) ||
      (p.marque?.toLowerCase().includes(q) ?? false) ||
      (p.modele?.toLowerCase().includes(q) ?? false) ||
      (p.matiere?.toLowerCase().includes(q) ?? false)
    );
  });

  const nbActifs = (items ?? []).filter((p) => p.actif).length;
  const nbInactifs = (items ?? []).filter((p) => !p.actif).length;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-muted-foreground">
          Les sleeves / supports physiques que tu utilises pour monter tes clichés.
        </div>
        <Button onClick={ouvrirAjout}>+ Ajouter un porte-cliché</Button>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-md border border-border bg-muted/30 p-3 text-sm">
        <label className="flex cursor-pointer items-center gap-1.5">
          <input
            type="checkbox"
            checked={voirInactifs}
            onChange={(e) => setVoirInactifs(e.target.checked)}
            className="h-4 w-4 accent-foreground"
          />
          <span>Voir aussi les désactivés</span>
        </label>
        <Input
          type="search"
          placeholder="Recherche référence, marque, matière…"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {items === null && (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      )}

      {items !== null && itemsAffiches.length === 0 && (
        <EtatVidePorteCliche onAjouter={ouvrirAjout} />
      )}

      <div className="space-y-2">
        {itemsAffiches.map((pc) => (
          <PorteClicheCard
            key={pc.id}
            pc={pc}
            onToggle={() => handleToggle(pc)}
            onModifier={() => {
              setEnCoursModif(pc);
              setDialogOuvert(true);
            }}
            onSupprimer={() => handleSupprimer(pc)}
          />
        ))}
      </div>

      {items !== null && (
        <p className="text-xs text-muted-foreground">
          {nbActifs} porte-cliché{nbActifs > 1 ? "s" : ""} actif
          {nbActifs > 1 ? "s" : ""}
          {nbInactifs > 0 && ` · ${nbInactifs} désactivé${nbInactifs > 1 ? "s" : ""}`}
        </p>
      )}

      <PorteClicheDialog
        ouvert={dialogOuvert}
        onClose={() => setDialogOuvert(false)}
        pc={enCoursModif}
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
        "rounded-lg border bg-white p-4 transition-colors " +
        (pc.actif
          ? "border-border hover:border-blue-300"
          : "border-border bg-muted/30 opacity-60")
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-base font-semibold">{pc.reference}</span>
            {pc.marque && (
              <span className="text-sm text-muted-foreground">
                · {pc.marque}
                {pc.modele && ` ${pc.modele}`}
              </span>
            )}
            <span className="text-sm text-muted-foreground">
              · {pc.laize_utile_mm} mm utiles
            </span>
          </div>
          {(pc.matiere || pc.diametre_interieur_mm) && (
            <p className="mt-1 text-xs text-muted-foreground">
              {pc.matiere && <span>{pc.matiere}</span>}
              {pc.matiere && pc.diametre_interieur_mm && " · "}
              {pc.diametre_interieur_mm && (
                <span>Mandrin {pc.diametre_interieur_mm} mm</span>
              )}
            </p>
          )}
          {pc.notes && (
            <p className="mt-1 text-xs text-muted-foreground italic">
              {pc.notes}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ToggleActif actif={pc.actif} onToggle={onToggle} />
          <Button variant="outline" size="sm" onClick={onModifier}>
            Modifier
          </Button>
          {pc.actif && (
            <Button variant="ghost" size="sm" onClick={onSupprimer}>
              Désactiver
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function EtatVidePorteCliche({ onAjouter }: { onAjouter: () => void }) {
  return (
    <div className="rounded-lg border-2 border-dashed border-border bg-muted/20 p-8 text-center">
      <div className="mb-2 text-3xl">📐</div>
      <p className="text-sm text-muted-foreground">
        Pas encore de porte-cliché — ajoutes-en un en 30 secondes.
      </p>
      <Button className="mt-4" onClick={onAjouter}>
        + Ajouter mon premier porte-cliché
      </Button>
    </div>
  );
}

function PorteClicheDialog({
  ouvert,
  onClose,
  pc,
  onSucces,
}: {
  ouvert: boolean;
  onClose: () => void;
  pc: PorteCliche | null;
  onSucces: () => Promise<void>;
}) {
  const { toast } = useToast();
  const enModif = pc !== null;
  const [reference, setReference] = useState("");
  const [marque, setMarque] = useState("");
  const [modele, setModele] = useState("");
  const [laize, setLaize] = useState<string>("");
  const [diametre, setDiametre] = useState<string>("");
  const [matiere, setMatiere] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (ouvert) {
      setReference(pc?.reference ?? "");
      setMarque(pc?.marque ?? "");
      setModele(pc?.modele ?? "");
      setLaize(pc?.laize_utile_mm ?? "");
      setDiametre(pc?.diametre_interieur_mm ?? "");
      setMatiere(pc?.matiere ?? "");
      setNotes(pc?.notes ?? "");
    }
  }, [ouvert, pc]);

  const handleSubmit = async () => {
    if (!reference.trim()) {
      toast({
        title: "Référence obligatoire",
        description: "Renseigne au moins une référence (ex: PC-220, Sleeve-A).",
        variant: "destructive",
      });
      return;
    }
    const laizeNum = parseFloat(laize);
    if (!Number.isFinite(laizeNum) || laizeNum <= 0) {
      toast({
        title: "Laize utile obligatoire",
        description: "Renseigne la laize utile en mm (nombre positif).",
        variant: "destructive",
      });
      return;
    }
    const diametreNum = diametre ? parseFloat(diametre) : null;
    setSubmitting(true);
    try {
      const payload = {
        reference: reference.trim(),
        marque: marque.trim() || null,
        modele: modele.trim() || null,
        laize_utile_mm: laizeNum,
        diametre_interieur_mm: diametreNum,
        matiere: matiere.trim() || null,
        notes: notes.trim() || null,
      };
      if (enModif && pc) {
        await updatePorteCliche(pc.id, payload);
        toast({ title: "Porte-cliché modifié" });
      } else {
        await createPorteCliche(payload);
        toast({ title: "Porte-cliché ajouté", description: reference });
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
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {enModif ? "Modifier un porte-cliché" : "Ajouter un porte-cliché"}
          </DialogTitle>
          <DialogDescription>
            Référence unique + laize utile suffisent. Le reste t&apos;aide à
            t&apos;y retrouver dans l&apos;atelier.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div className="space-y-2">
            <Label htmlFor="pc-ref">Référence *</Label>
            <Input
              id="pc-ref"
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="ex: PC-220, Sleeve-330"
              maxLength={50}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="pc-marque">Marque</Label>
              <Input
                id="pc-marque"
                type="text"
                value={marque}
                onChange={(e) => setMarque(e.target.value)}
                placeholder="ex: Rotec, DuPont, Flint"
                maxLength={80}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pc-modele">Modèle</Label>
              <Input
                id="pc-modele"
                type="text"
                value={modele}
                onChange={(e) => setModele(e.target.value)}
                placeholder="ex: Cyrel Fast"
                maxLength={80}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="pc-laize">Laize utile (mm) *</Label>
              <Input
                id="pc-laize"
                type="number"
                step="0.1"
                min={1}
                value={laize}
                onChange={(e) => setLaize(e.target.value)}
                placeholder="ex: 220"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pc-diam">Ø mandrin (mm)</Label>
              <Input
                id="pc-diam"
                type="number"
                step="0.1"
                min={1}
                value={diametre}
                onChange={(e) => setDiametre(e.target.value)}
                placeholder="ex: 76"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="pc-matiere">Matière</Label>
            <Input
              id="pc-matiere"
              type="text"
              value={matiere}
              onChange={(e) => setMatiere(e.target.value)}
              placeholder="ex: polyuréthane, carbone, acier"
              maxLength={40}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="pc-notes">Notes</Label>
            <Input
              id="pc-notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Emplacement, état, particularités…"
              maxLength={1000}
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
