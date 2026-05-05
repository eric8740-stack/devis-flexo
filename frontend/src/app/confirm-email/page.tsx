"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Status = "loading" | "missing-token" | "error";

export default function ConfirmEmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<Status>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Garde-fou React strict-mode : useEffect peut tourner deux fois en dev,
  // ce qui poserait un POST en double sur le même token. La première
  // tentative consume le token côté backend, la seconde renverrait 400 et
  // afficherait à tort une erreur. On bloque les rejouages avec un ref.
  const hasRunRef = useRef(false);

  useEffect(() => {
    if (hasRunRef.current) return;
    hasRunRef.current = true;

    if (!token) {
      setStatus("missing-token");
      return;
    }

    const confirm = async () => {
      try {
        const r = await fetch(`${API_URL}/api/auth/confirm-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          throw new Error(err.detail || "Confirmation impossible");
        }
        router.replace("/login?confirmed=true");
      } catch (err) {
        setErrorMessage(err instanceof Error ? err.message : "Erreur inconnue");
        setStatus("error");
      }
    };
    void confirm();
  }, [token, router]);

  return (
    <main className="flex min-h-[80vh] items-center justify-center p-4">
      <Card className="w-full max-w-md">
        {status === "loading" && (
          <>
            <CardHeader>
              <CardTitle className="text-2xl">
                Confirmation de votre email
              </CardTitle>
              <CardDescription>
                Validation du lien en cours…
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Merci de patienter quelques secondes.
              </p>
            </CardContent>
          </>
        )}

        {status === "missing-token" && (
          <>
            <CardHeader>
              <CardTitle className="text-2xl">Lien invalide</CardTitle>
              <CardDescription>
                Le lien de confirmation est incomplet ou expiré.
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button asChild className="w-full">
                <Link href="/login">Retour à la connexion</Link>
              </Button>
            </CardFooter>
          </>
        )}

        {status === "error" && (
          <>
            <CardHeader>
              <CardTitle className="text-2xl">
                Confirmation impossible
              </CardTitle>
              <CardDescription>
                {errorMessage ||
                  "Le lien est peut-être expiré ou déjà utilisé."}
              </CardDescription>
            </CardHeader>
            <CardFooter className="flex flex-col gap-3">
              <Button asChild className="w-full">
                <Link href="/login">Retour à la connexion</Link>
              </Button>
              <Button asChild variant="outline" className="w-full">
                <Link href="/register">Créer un nouveau compte</Link>
              </Button>
            </CardFooter>
          </>
        )}
      </Card>
    </main>
  );
}
