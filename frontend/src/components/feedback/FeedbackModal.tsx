"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

const MAX_MESSAGE_LENGTH = 2000;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Modale de retour utilisateur (early adopters pilote vendeur de presses).
 *
 * Stade Commit 1 : UI seule. La logique d'envoi vers Formspree + la
 * capture du contexte (email, entreprise, page, app_version) arrive en
 * Commit 2. Le `FeedbackButton` flottant qui pilote `open` arrive en
 * Commit 3.
 *
 * Choix design (cf. brief feedback-pilote) :
 *   - 1 seul textarea, pas de catégorisation (10 users max → tri manuel)
 *   - Bouton "Envoyer" disabled tant que vide ou en cours d'envoi
 *   - Friction zéro : pas de captcha, pas de champs cachés, pas d'email
 *     à saisir (capturé automatiquement Commit 2 depuis useAuth())
 */
export function FeedbackModal({ open, onOpenChange }: Props) {
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const trimmed = message.trim();
  const canSubmit = trimmed.length > 0 && !submitting;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      // TODO Commit 2 : POST vers NEXT_PUBLIC_FEEDBACK_FORMSPREE_URL
      // avec capture contexte (user_email, entreprise_slug, page,
      // app_version, submitted_at) + toasts succès/erreur.
      // Pour l'instant on simule juste pour valider le rendu UI.
      await new Promise((resolve) => setTimeout(resolve, 200));
      setMessage("");
      onOpenChange(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          // Si on ferme via Cancel/escape/overlay : on garde le message en
          // local au cas où l'utilisateur le rouvre par erreur. Le reset
          // n'a lieu qu'à un envoi réussi.
        }
        onOpenChange(o);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Un retour à nous faire ?</DialogTitle>
          <DialogDescription>
            Bug, suggestion, question — tout est utile pour améliorer
            l&apos;application.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="feedback-message">Votre message</Label>
            <textarea
              id="feedback-message"
              required
              rows={5}
              maxLength={MAX_MESSAGE_LENGTH}
              placeholder="Décrivez en quelques mots…"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              disabled={submitting}
            />
            <p className="text-xs text-muted-foreground">
              {trimmed.length}/{MAX_MESSAGE_LENGTH} caractères. Votre email
              et la page courante sont automatiquement joints au message
              pour faciliter le suivi.
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
            >
              Annuler
            </Button>
            <Button type="submit" disabled={!canSubmit}>
              {submitting ? "Envoi…" : "Envoyer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
