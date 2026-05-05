"use client";

import { MessageCircle } from "lucide-react";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { FeedbackModal } from "@/components/feedback/FeedbackModal";
import { useAuth } from "@/contexts/AuthContext";

const FORMSPREE_URL = process.env.NEXT_PUBLIC_FEEDBACK_FORMSPREE_URL;

/**
 * Bouton flottant (FAB) "Signaler un problème / Suggérer", fixé en
 * bas-droite. Ouvre `FeedbackModal` au clic.
 *
 * Conditions de montage (return null silencieux sinon) :
 *   - User authentifié (via `useAuth`) — pas de feedback anonyme
 *   - Pas sur `/admin/*` (Eric, l'unique admin, ne s'envoie pas du
 *     feedback à lui-même — cf. brief décision #3)
 *   - Variable d'env `NEXT_PUBLIC_FEEDBACK_FORMSPREE_URL` définie. Si
 *     absente (preview/dev sans config), on n'affiche pas le bouton :
 *     pas de crash, pas de panneau cassé.
 *
 * Robustesse : on n'expose ce bouton que sur les pages où il a un sens
 * commercial (= client connecté à son espace). `ProtectedRoute` (S12-E)
 * gère déjà la redirection /login pour les routes privées, donc en
 * pratique on est ici uniquement sur des pages authentifiées.
 */
export function FeedbackButton() {
  const { isAuthenticated } = useAuth();
  const pathname = usePathname() ?? "/";
  const [open, setOpen] = useState(false);

  if (!FORMSPREE_URL) return null;
  if (!isAuthenticated) return null;
  if (pathname === "/admin" || pathname.startsWith("/admin/")) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Signaler un problème ou suggérer"
        title="Signaler un problème ou suggérer"
        className="fixed bottom-6 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105 hover:shadow-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <MessageCircle className="h-5 w-5" aria-hidden="true" />
      </button>
      <FeedbackModal open={open} onOpenChange={setOpen} />
    </>
  );
}
