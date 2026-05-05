"use client";

import { HelpCircle } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface HelpButtonProps {
  /** Affiché dans le header de la modale, préfixé par "Aide — ". */
  title: string;
  /** Contenu de la documentation, en JSX riche (titres, paragraphes, images). */
  children: React.ReactNode;
}

/**
 * Bouton « Aide » discret à placer à côté du titre H1 d'une page métier.
 * Au clic, ouvre une modale shadcn Dialog avec le contenu fourni en
 * children — typiquement un composant `<XxxHelp />` issu de
 * `components/help/content/`.
 *
 * Le footer rappelle l'existence du bouton FAB feedback (cf. Sprint 12
 * post-pilote) : si la doc ne couvre pas la question, l'utilisateur sait
 * où écrire — et chaque feedback récurrent enrichira ensuite la doc.
 *
 * Pas de FAB ici : le bas-droite est déjà occupé par FeedbackButton, donc
 * on choisit l'ancrage au titre (variant ghost, taille sm) pour rester
 * discret tout en étant à portée d'œil.
 */
export function HelpButton({ title, children }: HelpButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => setOpen(true)}
        aria-label={`Aide — ${title}`}
        className="gap-1"
      >
        <HelpCircle className="h-4 w-4" aria-hidden="true" />
        <span className="hidden sm:inline">Aide</span>
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[80vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Aide — {title}</DialogTitle>
          </DialogHeader>

          <div className="prose prose-sm max-w-none py-4">{children}</div>

          <DialogFooter className="border-t pt-4 text-sm text-muted-foreground">
            Une question pas couverte ici ? Cliquez sur la bulle
            {" "}💬{" "}
            en bas à droite pour nous écrire — on lit chaque message.
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
