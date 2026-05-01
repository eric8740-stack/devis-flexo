"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const PARAMETRES_NAV = [
  // Sprint 9 v2 — priorité 1 : tarifs (paramétrabilité)
  { href: "/parametres/tarifs", label: "Tarifs" },
  // Sprint 0-1 — entreprise (déplacée depuis /parametres mono-page)
  { href: "/parametres/entreprise", label: "Entreprise" },
  // Liens externes vers les CRUD existants (catalogues + charges)
  { href: "/parametres/outils", label: "Outils de découpe" },
  { href: "/machines", label: "Machines" },
  { href: "/complexes", label: "Matières (complexes)" },
  { href: "/partenaires-st", label: "Partenaires ST" },
  { href: "/charges-mensuelles", label: "Charges mensuelles" },
];

export default function ParametresLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  return (
    <main className="container mx-auto p-8">
      <h1 className="mb-6 text-2xl font-semibold">Paramètres</h1>
      <div className="flex flex-col gap-8 md:flex-row md:gap-12">
        <aside className="md:w-56 md:shrink-0">
          <nav className="flex flex-col gap-1 text-sm">
            {PARAMETRES_NAV.map(({ href, label }) => {
              const active =
                pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "rounded-md px-3 py-2 transition-colors",
                    active
                      ? "bg-accent font-medium text-accent-foreground"
                      : "text-muted-foreground hover:bg-accent/50"
                  )}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <section className="min-w-0 flex-1">{children}</section>
      </div>
    </main>
  );
}
