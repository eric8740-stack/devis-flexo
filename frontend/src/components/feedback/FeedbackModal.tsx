"use client";

import { usePathname } from "next/navigation";
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
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";

const MAX_MESSAGE_LENGTH = 2000;

const FORMSPREE_URL = process.env.NEXT_PUBLIC_FEEDBACK_FORMSPREE_URL;
const APP_VERSION =
  process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA ?? "dev";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Modale de retour utilisateur (early adopters pilote vendeur de presses).
 *
 * Envoi vers Formspree (`NEXT_PUBLIC_FEEDBACK_FORMSPREE_URL`) avec
 * capture automatique du contexte côté client : email du user (depuis
 * `useAuth`), entreprise courante, page d'origine, commit SHA Vercel,
 * timestamp ISO. Aucune saisie email/identité à la charge de l'utilisateur.
 *
 * Choix design (cf. brief feedback-pilote) :
 *   - 1 seul textarea, pas de catégorisation (< 10 users → Eric trie à la main)
 *   - Toast succès → reset + ferme la modale
 *   - Toast erreur → modale reste ouverte, message préservé pour retry
 *   - Si la variable d'env Formspree n'est pas définie : envoi silencieux
 *     refusé (le FeedbackButton hôte est aussi conditionné, donc en
 *     pratique on n'arrive pas ici sans config). Sécurité ceinture+bretelles.
 */
export function FeedbackModal({ open, onOpenChange }: Props) {
  const { user } = useAuth();
  const { toast } = useToast();
  const pathname = usePathname() ?? "/";

  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const trimmed = message.trim();
  const canSubmit = trimmed.length > 0 && !submitting;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    if (!FORMSPREE_URL) {
      // Garde-fou : ne devrait pas arriver (FeedbackButton vérifie la
      // variable d'env avant de rendre le bouton flottant). Au cas où,
      // on affiche un toast neutre plutôt que de crasher.
      toast({
        title: "Configuration manquante",
        description:
          "Le canal de retour n'est pas configuré sur cet environnement.",
        variant: "destructive",
      });
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        message: trimmed,
        user_email: user?.email ?? "unknown",
        entreprise_id: user?.entreprise_id ?? null,
        entreprise_nom: user?.nom_entreprise ?? "unknown",
        page: pathname,
        app_version: APP_VERSION,
        submitted_at: new Date().toISOString(),
      };
      const response = await fetch(FORMSPREE_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      toast({
        title: "Merci !",
        description: "Retour bien envoyé. Nous y répondons rapidement.",
      });
      setMessage("");
      onOpenChange(false);
    } catch {
      // Réseau down ou Formspree non-2xx : on garde la modale ouverte
      // et le textarea intact pour un retry simple.
      toast({
        title: "Envoi impossible",
        description:
          "Vérifiez votre connexion et réessayez. Votre message est conservé.",
        variant: "destructive",
      });
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
