"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  // Sprint 3 — fonctionnalité phare en tête
  { href: "/devis/nouveau", label: "Calculer un devis" },
  // Sprint 4 — devis sauvegardés
  { href: "/devis", label: "Devis" },
  { href: "/parametres", label: "Paramètres" },
  { href: "/clients", label: "Clients" },
  { href: "/fournisseurs", label: "Fournisseurs" },
  // Sprint 2
  { href: "/machines", label: "Machines" },
  { href: "/operations-finition", label: "Op. finition" },
  { href: "/partenaires-st", label: "Partenaires ST" },
  { href: "/charges-mensuelles", label: "Charges" },
  { href: "/complexes", label: "Complexes" },
  // Sprint 12 mini-fix UX-1 : "Catalogue" trop générique, créait confusion
  // avec "Outils de découpe" (sidebar Paramètres). On précise le concept
  // métier : ce sont les produits récurrents commandés PAR LES CLIENTS,
  // pas les outils techniques de production.
  { href: "/catalogue", label: "Produits clients" },
];

const ADMIN_NAV_ITEM = { href: "/admin", label: "Admin" };

export function Header() {
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  // Best-match : on choisit le href le PLUS LONG qui matche le pathname.
  // Évite que /devis/nouveau active à la fois /devis et /devis/nouveau.
  const visibleNav = isAuthenticated
    ? user?.is_admin
      ? [...NAV_ITEMS, ADMIN_NAV_ITEM]
      : NAV_ITEMS
    : [];
  const activeHref = visibleNav
    .filter(
      ({ href }) => pathname === href || pathname.startsWith(`${href}/`)
    )
    .reduce<string | null>(
      (best, { href }) =>
        best === null || href.length > best.length ? href : best,
      null
    );

  return (
    <header className="border-b bg-background">
      <nav className="container mx-auto flex flex-wrap items-center gap-x-6 gap-y-2 p-4">
        <Link href="/" className="text-base font-semibold">
          devis-flexo
        </Link>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          {visibleNav.map(({ href, label }) => {
            const active = href === activeHref;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "text-sm transition-colors hover:text-foreground",
                  active
                    ? "font-medium text-foreground"
                    : "text-muted-foreground"
                )}
              >
                {label}
              </Link>
            );
          })}
        </div>

        {/* Zone droite : auth */}
        <div className="ml-auto flex items-center gap-3">
          {isLoading ? null : isAuthenticated ? (
            <>
              <span className="text-sm text-muted-foreground">
                {user?.email}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
                aria-label="Se déconnecter"
              >
                Déconnexion
              </Button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                Connexion
              </Link>
              <Link
                href="/register"
                className="text-sm font-medium text-foreground transition-colors hover:underline"
              >
                Inscription
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
