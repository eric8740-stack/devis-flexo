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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { ApiError, createAdminUser } from "@/lib/api";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void | Promise<void>;
}

const INITIAL_FORM = {
  email: "",
  password: "",
  nom_entreprise: "",
  nom_contact: "",
  is_admin: false,
};

export function CreateUserDialog({ open, onOpenChange, onCreated }: Props) {
  const { toast } = useToast();
  const [form, setForm] = useState(INITIAL_FORM);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordTooShort =
    form.password.length > 0 && form.password.length < 8;

  const reset = () => {
    setForm(INITIAL_FORM);
    setShowPassword(false);
    setError(null);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (form.password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    setSubmitting(true);
    try {
      await createAdminUser(form);
      toast({
        title: "Compte créé",
        description: `${form.email} (${form.nom_entreprise})`,
      });
      reset();
      onOpenChange(false);
      await onCreated();
    } catch (err) {
      const message =
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Erreur inconnue";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Créer un nouveau compte</DialogTitle>
          <DialogDescription>
            Création manuelle par admin. Le compte est actif immédiatement
            (pas de confirmation email).
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="create-email">Email</Label>
            <Input
              id="create-email"
              type="email"
              required
              value={form.email}
              onChange={(e) =>
                setForm((f) => ({ ...f, email: e.target.value }))
              }
              placeholder="contact@imprimerie.fr"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="create-password">
                Mot de passe (8 caractères min.)
              </Label>
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="text-xs text-muted-foreground hover:text-foreground hover:underline"
              >
                {showPassword ? "Masquer" : "Afficher"}
              </button>
            </div>
            <Input
              id="create-password"
              type={showPassword ? "text" : "password"}
              required
              minLength={8}
              value={form.password}
              onChange={(e) =>
                setForm((f) => ({ ...f, password: e.target.value }))
              }
              aria-invalid={passwordTooShort}
            />
            {passwordTooShort && (
              <p className="text-xs text-destructive">
                Minimum 8 caractères ({form.password.length}/8).
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="create-nom-entreprise">Nom de l&apos;entreprise</Label>
            <Input
              id="create-nom-entreprise"
              type="text"
              required
              minLength={2}
              maxLength={150}
              value={form.nom_entreprise}
              onChange={(e) =>
                setForm((f) => ({ ...f, nom_entreprise: e.target.value }))
              }
              placeholder="Imprimerie Dupont"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="create-nom-contact">Nom du contact</Label>
            <Input
              id="create-nom-contact"
              type="text"
              required
              minLength={2}
              maxLength={150}
              value={form.nom_contact}
              onChange={(e) =>
                setForm((f) => ({ ...f, nom_contact: e.target.value }))
              }
              placeholder="Jean Dupont"
            />
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_admin}
              onChange={(e) =>
                setForm((f) => ({ ...f, is_admin: e.target.checked }))
              }
              className="h-4 w-4 cursor-pointer rounded border border-input accent-foreground"
            />
            <span>
              Compte administrateur{" "}
              <span className="text-xs text-muted-foreground">
                (accès aux endpoints /api/admin/*)
              </span>
            </span>
          </label>

          {error && (
            <div
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
            >
              {error}
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
            >
              Annuler
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Création…" : "Créer le compte"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
