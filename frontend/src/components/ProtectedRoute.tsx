"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/contexts/AuthContext";

// Routes accessibles sans authentification.
const PUBLIC_ROUTES = [
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/confirm-email",
];

// Routes réservées aux admins (`is_admin=True`). Sinon redirect /devis.
const ADMIN_ROUTES = ["/admin"];

function isPublic(pathname: string): boolean {
  return PUBLIC_ROUTES.some(
    (r) => pathname === r || pathname.startsWith(`${r}/`)
  );
}

function isAdminRoute(pathname: string): boolean {
  return ADMIN_ROUTES.some((r) => pathname === r || pathname.startsWith(`${r}/`));
}

/**
 * Wrapper côté client qui :
 *  - affiche un placeholder pendant la lecture initiale du token
 *  - redirige vers /login si la route est privée et pas authentifié
 *  - redirige vers /devis si admin-only et user non-admin
 *
 * À placer dans le layout (au-dessus de `{children}`).
 *
 * Note : Next.js middleware (edge) n'a pas accès à localStorage, on protège
 * donc côté client. Pour un MVP c'est acceptable ; on durcira avec cookie
 * HttpOnly si besoin plus tard.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();
  const pathname = usePathname() || "/";

  useEffect(() => {
    if (isLoading) return;
    if (!isPublic(pathname) && !isAuthenticated) {
      router.replace("/login");
      return;
    }
    if (isAdminRoute(pathname) && !user?.is_admin) {
      router.replace("/devis");
    }
  }, [isLoading, isAuthenticated, user, pathname, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-muted-foreground">
        Chargement…
      </div>
    );
  }

  // Pendant la redirection (frame intermédiaire avant que router.replace
  // ne change la route), on évite d'afficher le contenu privé.
  if (!isPublic(pathname) && !isAuthenticated) {
    return null;
  }
  if (isAdminRoute(pathname) && !user?.is_admin) {
    return null;
  }

  return <>{children}</>;
}
