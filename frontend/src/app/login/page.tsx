"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

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

export default function LoginPage() {
  const { login } = useAuth();
  const { toast } = useToast();
  const searchParams = useSearchParams();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Toasts d'arrivée selon la query param (registered / reset / confirmed)
  useEffect(() => {
    if (searchParams.get("registered") === "true") {
      toast({
        title: "Inscription réussie",
        description:
          "Vérifiez votre email pour confirmer votre adresse avant de vous connecter.",
      });
    } else if (searchParams.get("reset") === "true") {
      toast({
        title: "Mot de passe réinitialisé",
        description: "Connectez-vous avec votre nouveau mot de passe.",
      });
    } else if (searchParams.get("confirmed") === "true") {
      toast({
        title: "Email confirmé",
        description: "Vous pouvez maintenant vous connecter.",
      });
    }
    // toast et searchParams sont stables/snapshots, pas besoin d'autres deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login({ email, password });
      // Redirection vers /devis gérée par AuthContext.login
    } catch (err) {
      toast({
        title: "Connexion impossible",
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
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">Connexion à Devis Flexo</CardTitle>
          <CardDescription>
            Entrez vos identifiants pour accéder à votre espace.
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
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Mot de passe</Label>
                <Link
                  href="/forgot-password"
                  className="text-xs text-muted-foreground hover:text-foreground hover:underline"
                >
                  Oublié ?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Connexion…" : "Se connecter"}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Pas encore de compte ?{" "}
              <Link
                href="/register"
                className="font-medium text-foreground hover:underline"
              >
                Inscrivez-vous
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </main>
  );
}
