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
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";

export default function RegisterPage() {
  const { register } = useAuth();
  const { toast } = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nomEntreprise, setNomEntreprise] = useState("");
  const [nomContact, setNomContact] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const passwordTooShort = password.length > 0 && password.length < 8;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      toast({
        title: "Mot de passe trop court",
        description: "Minimum 8 caractères.",
        variant: "destructive",
      });
      return;
    }
    setSubmitting(true);
    try {
      await register({
        email,
        password,
        nom_entreprise: nomEntreprise,
        nom_contact: nomContact,
      });
      // Redirection vers /login?registered=true gérée par AuthContext.register
    } catch (err) {
      toast({
        title: "Inscription impossible",
        description:
          err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-[80vh] items-center justify-center p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-2xl">Créer un compte</CardTitle>
          <CardDescription>
            Vous recevrez un email pour confirmer votre adresse.
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
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Mot de passe (8 caractères min.)</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={passwordTooShort}
              />
              {passwordTooShort && (
                <p className="text-xs text-destructive">
                  Minimum 8 caractères ({password.length}/8).
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="nom_entreprise">Nom de votre entreprise</Label>
              <Input
                id="nom_entreprise"
                type="text"
                required
                minLength={2}
                maxLength={150}
                value={nomEntreprise}
                onChange={(e) => setNomEntreprise(e.target.value)}
                placeholder="Imprimerie Dupont"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="nom_contact">Votre nom</Label>
              <Input
                id="nom_contact"
                type="text"
                autoComplete="name"
                required
                minLength={2}
                maxLength={150}
                value={nomContact}
                onChange={(e) => setNomContact(e.target.value)}
                placeholder="Jean Dupont"
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Création…" : "Créer mon compte"}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Déjà un compte ?{" "}
              <Link
                href="/login"
                className="font-medium text-foreground hover:underline"
              >
                Connectez-vous
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </main>
  );
}
