"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  // Sprint 3 — fonctionnalité phare en tête
  { href: "/devis/nouveau", label: "Calculer un devis" },
  { href: "/parametres", label: "Paramètres" },
  { href: "/clients", label: "Clients" },
  { href: "/fournisseurs", label: "Fournisseurs" },
  // Sprint 2
  { href: "/machines", label: "Machines" },
  { href: "/operations-finition", label: "Op. finition" },
  { href: "/partenaires-st", label: "Partenaires ST" },
  { href: "/charges-mensuelles", label: "Charges" },
  { href: "/complexes", label: "Complexes" },
  { href: "/catalogue", label: "Catalogue" },
];

export function Header() {
  const pathname = usePathname();
  return (
    <header className="border-b bg-background">
      <nav className="container mx-auto flex flex-wrap items-center gap-x-6 gap-y-2 p-4">
        <Link href="/" className="text-base font-semibold">
          devis-flexo
        </Link>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          {NAV_ITEMS.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
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
      </nav>
    </header>
  );
}
