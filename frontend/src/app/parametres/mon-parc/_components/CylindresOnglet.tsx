"use client";

/**
 * Onglet "Mes cylindres" — Brief #29.
 *
 * Liste sous forme de cards aérées, toggle actif/inactif coloré (vert/gris),
 * dialog ajout/modif avec validation inline, badge "Petit cylindre" pour
 * les ≤ 80 dents (réutilise convention Brief #28).
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
  createCylindre,
  deleteCylindre,
  listCylindres,
  toggleActifCylindre,
  updateCylindre,
  type CylindreParc,
} from "@/lib/api";

const PETIT_CYL_SEUIL_DENTS = 80;

export function CylindresOnglet() {
  const { toast } = useToast();
  const [cyls, setCyls] = useState<CylindreParc[] | null>(null);
  const [voirInactifs, setVoirInactifs] = useState(false);
  const [recherche, setRecherche] = useState("");
  const [dialogOuvert, setDialogOuvert] = useState(false);
  const [cylEnCoursModif, setCylEnCoursModif] = useState<CylindreParc | null>(
    null
  );

  const rafraichir = async () => {
    try {
      const data = await listCylindres(voirInactifs ? null : true);
      setCyls(data);
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
    setCylEnCoursModif(null);
    setDialogOuvert(true);
  };

  const ouvrirModif = (cyl: CylindreParc) => {
    setCylEnCoursModif(cyl);
    setDialogOuvert(true);
  };

  const handleToggle = async (cyl: CylindreParc) => {
    try {
      await toggleActifCylindre(cyl.id);
      await rafraichir();
    } catch (err) {
      toast({
        title: "Toggle impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const handleSupprimer = async (cyl: CylindreParc) => {
    if (
      !confirm(
        `Désactiver le cylindre ${cyl.nb_dents} dents ? Il restera en base, juste masqué de l'optimisation. Tu pourras le réactiver à tout moment.`
      )
    ) {
      return;
    }
    try {
      await deleteCylindre(cyl.id);
      toast({
        title: "Cylindre désactivé",
        description: `Le cylindre ${cyl.nb_dents} dents est désactivé.`,
      });
      await rafraichir();
    } catch (err) {
      toast({
        title: "Désactivation impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const cylsAffiches = (cyls ?? []).filter((c) => {
    if (!recherche) return true;
    const q = recherche.toLowerCase();
    return (
      String(c.nb_dents).includes(q) ||
      c.developpe_mm.includes(q) ||
      (c.notes?.toLowerCase().includes(q) ?? false)
    );
  });

  const nbActifs = (cyls ?? []).filter((c) => c.actif).length;
  const nbInactifs = (cyls ?? []).filter((c) => !c.actif).length;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-muted-foreground">
          Les cylindres que tu utilises sur tes machines flexo.
        </div>
        <Button onClick={ouvrirAjout}>+ Ajouter un cylindre</Button>
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
          placeholder="Recherche dents, notes…"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {cyls === null && (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      )}

      {cyls !== null && cylsAffiches.length === 0 && (
        <EtatVide onAjouter={ouvrirAjout} />
      )}

      <div className="space-y-2">
        {cylsAffiches.map((cyl) => (
          <CylindreCard
            key={cyl.id}
            cyl={cyl}
            onToggle={() => handleToggle(cyl)}
            onModifier={() => ouvrirModif(cyl)}
            onSupprimer={() => handleSupprimer(cyl)}
          />
        ))}
      </div>

      {cyls !== null && (
        <p className="text-xs text-muted-foreground">
          {nbActifs} cylindre{nbActifs > 1 ? "s" : ""} actif
          {nbActifs > 1 ? "s" : ""}
          {nbInactifs > 0 && ` · ${nbInactifs} désactivé${nbInactifs > 1 ? "s" : ""}`}
        </p>
      )}

      <CylindreDialog
        ouvert={dialogOuvert}
        onClose={() => setDialogOuvert(false)}
        cyl={cylEnCoursModif}
        onSucces={async () => {
          setDialogOuvert(false);
          await rafraichir();
        }}
      />
    </section>
  );
}

function CylindreCard({
  cyl,
  onToggle,
  onModifier,
  onSupprimer,
}: {
  cyl: CylindreParc;
  onToggle: () => void;
  onModifier: () => void;
  onSupprimer: () => void;
}) {
  const petit = cyl.nb_dents <= PETIT_CYL_SEUIL_DENTS;
  return (
    <div
      className={
        "rounded-lg border bg-white p-4 transition-colors " +
        (cyl.actif
          ? "border-border hover:border-blue-300"
          : "border-border bg-muted/30 opacity-60")
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-base font-semibold">
              {cyl.nb_dents} dents
            </span>
            <span className="text-sm text-muted-foreground">
              Z = {cyl.developpe_mm} mm
            </span>
            {petit && (
              <span
                title="Cylindre de petit diamètre — vérifie visuellement la planéité du tirage si tu doutes"
                className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-900"
              >
                ℹ️ Petit cylindre
              </span>
            )}
          </div>
          {cyl.notes && (
            <p className="mt-1 text-xs text-muted-foreground">{cyl.notes}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ToggleActif actif={cyl.actif} onToggle={onToggle} />
          <Button variant="outline" size="sm" onClick={onModifier}>
            Modifier
          </Button>
          {cyl.actif && (
            <Button variant="ghost" size="sm" onClick={onSupprimer}>
              Désactiver
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export function ToggleActif({
  actif,
  onToggle,
}: {
  actif: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={
        "relative inline-flex h-6 w-11 cursor-pointer items-center rounded-full transition-colors " +
        (actif ? "bg-emerald-500" : "bg-gray-300")
      }
      title={actif ? "Actif — clique pour désactiver" : "Désactivé — clique pour réactiver"}
    >
      <span
        className={
          "inline-block h-4 w-4 rounded-full bg-white shadow transition-transform " +
          (actif ? "translate-x-6" : "translate-x-1")
        }
      />
    </button>
  );
}

function EtatVide({ onAjouter }: { onAjouter: () => void }) {
  return (
    <div className="rounded-lg border-2 border-dashed border-border bg-muted/20 p-8 text-center">
      <div className="mb-2 text-3xl">🔧</div>
      <p className="text-sm text-muted-foreground">
        Tu n&apos;as pas encore de cylindre — ajoutes-en un en 30 secondes.
      </p>
      <Button className="mt-4" onClick={onAjouter}>
        + Ajouter mon premier cylindre
      </Button>
    </div>
  );
}

function CylindreDialog({
  ouvert,
  onClose,
  cyl,
  onSucces,
}: {
  ouvert: boolean;
  onClose: () => void;
  cyl: CylindreParc | null;
  onSucces: () => Promise<void>;
}) {
  const { toast } = useToast();
  const enModif = cyl !== null;
  const [nbDents, setNbDents] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (ouvert) {
      setNbDents(cyl ? String(cyl.nb_dents) : "");
      setNotes(cyl?.notes ?? "");
    }
  }, [ouvert, cyl]);

  const handleSubmit = async () => {
    const n = parseInt(nbDents, 10);
    if (!Number.isFinite(n) || n < 20 || n > 300) {
      toast({
        title: "Nombre de dents invalide",
        description: "Renseigne un nombre entre 20 et 300 (standard flexo).",
        variant: "destructive",
      });
      return;
    }
    setSubmitting(true);
    try {
      if (enModif && cyl) {
        await updateCylindre(cyl.id, { nb_dents: n, notes: notes || null });
        toast({ title: "Cylindre modifié" });
      } else {
        await createCylindre({ nb_dents: n, notes: notes || null });
        toast({
          title: "Cylindre ajouté",
          description: `Cylindre ${n} dents disponible pour tes prochains devis.`,
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
            {enModif ? "Modifier un cylindre" : "Ajouter un cylindre"}
          </DialogTitle>
          <DialogDescription>
            La nomenclature flexo standard : 1 dent = 3,175 mm de développé.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="cyl-dents">Nombre de dents</Label>
            <Input
              id="cyl-dents"
              type="number"
              min={20}
              max={300}
              value={nbDents}
              onChange={(e) => setNbDents(e.target.value)}
              placeholder="ex: 104"
            />
            {nbDents && Number.isFinite(parseInt(nbDents, 10)) && (
              <p className="text-xs text-muted-foreground">
                Développé calculé :{" "}
                <strong>
                  {(parseInt(nbDents, 10) * 3.175).toFixed(2)} mm
                </strong>
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="cyl-notes">Notes (optionnel)</Label>
            <Input
              id="cyl-notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Repère machine, emplacement…"
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
