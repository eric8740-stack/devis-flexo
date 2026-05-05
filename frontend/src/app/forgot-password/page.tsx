"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ForgotPasswordPage() {
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      // POST /api/auth/forgot-password — appelé en direct (pas via apiFetch)
      // car cet endpoint est public + on accepte tout statut sans erreur :
      // l'API renvoie 200 même pour un email inconnu (anti-enumeration).
      await fetch(`${API_URL}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setSent(true);
      toast({
        title: "Demande enregistrée",
        description:
          "Si cet email existe, un lien de réinitialisation vient d'être envoyé.",
      });
    } catch {
      // Le backend retourne toujours 200 — un échec ici est probablement
      // réseau. On affiche un message minimal mais on n'expose pas si
      // l'email existe ou non.
      toast({
        title: "Demande enregistrée",
        description:
          "Si cet email existe, un lien de réinitialisation vient d'être envoyé.",
      });
      setSent(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-[80vh] items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">Mot de passe oublié</CardTitle>
          <CardDescription>
            Entrez votre email — nous vous enverrons un lien pour
            réinitialiser votre mot de passe.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="vous@exemple.fr"
                disabled={sent}
              />
            </div>
            {sent && (
              <p className="text-sm text-muted-foreground">
                Si cet email est associé à un compte, un lien de
                réinitialisation vous a été envoyé. Pensez à vérifier vos
                spams.
              </p>
            )}
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button
              type="submit"
              className="w-full"
              disabled={submitting || sent}
            >
              {submitting
                ? "Envoi…"
                : sent
                  ? "Lien envoyé"
                  : "Envoyer le lien de réinitialisation"}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              <Link
                href="/login"
                className="font-medium text-foreground hover:underline"
              >
                Retour à la connexion
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </main>
  );
}
