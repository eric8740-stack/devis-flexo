"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/parametres", label: "Paramètres" },
  { href: "/clients", label: "Clients" },
  { href: "/fournisseurs", label: "Fournisseurs" },
];

export function Header() {
  const pathname = usePathname();
  return (
    <header className="border-b bg-background">
      <nav className="container mx-auto flex items-center gap-8 p-4">
        <Link href="/" className="text-base font-semibold">
          devis-flexo
        </Link>
        <div className="flex gap-6">
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
