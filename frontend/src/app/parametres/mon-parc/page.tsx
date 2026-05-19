"use client";

/**
 * /parametres/mon-parc — Brief #29.
 *
 * Hub paramètres parc avec 2 onglets : Cylindres + Porte-clichés.
 * UX simple, joyeuse, tutoiement systématique. Cards aérées, toggle
 * actif coloré, dialog ajout/modif. Pas d'entrée sidebar séparée —
 * accès via card "Mon parc" depuis /parametres.
 */
import { useEffect, useState } from "react";

import { CylindresOnglet } from "./_components/CylindresOnglet";
import { PorteClichesOnglet } from "./_components/PorteClichesOnglet";

type Onglet = "cylindres" | "porte-cliches";

export default function MonParcPage() {
  const [onglet, setOnglet] = useState<Onglet>("cylindres");

  // Sync l'onglet courant avec le hash de l'URL (#cylindres ou #porte-cliches)
  // → liens directs partageables, retour navigation OK.
  useEffect(() => {
    const fromHash = window.location.hash.replace("#", "");
    if (fromHash === "porte-cliches" || fromHash === "cylindres") {
      setOnglet(fromHash);
    }
  }, []);

  const switchOnglet = (next: Onglet) => {
    setOnglet(next);
    if (typeof window !== "undefined") {
      history.replaceState(null, "", `#${next}`);
    }
  };

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      {/* Header coloré (Brief #30 §8) : éclat accent + sous-titre tutoyé. */}
      <header className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50/60 via-amber-50/40 to-white p-6 shadow-sm">
        <h1 className="bg-gradient-to-r from-blue-800 to-amber-700 bg-clip-text text-3xl font-bold text-transparent">
          Mon parc
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Tes cylindres magnétiques et tes porte-clichés. Tu peux en ajouter,
          désactiver les anciens, réactiver à volonté. Pas besoin de tout
          configurer — un parc prêt à l&apos;emploi t&apos;a été pré-rempli ✨
        </p>
      </header>

      {/* Tabs avec underline gradient pour le tab actif. */}
      <div className="flex gap-1 border-b border-border">
        {(["cylindres", "porte-cliches"] as const).map((key) => {
          const actif = onglet === key;
          const label =
            key === "cylindres" ? "🔧 Mes cylindres" : "📐 Mes porte-clichés";
          return (
            <button
              key={key}
              type="button"
              onClick={() => switchOnglet(key)}
              className={
                "relative rounded-t-md px-4 py-2 text-sm font-medium transition-colors " +
                (actif
                  ? "text-blue-900"
                  : "text-muted-foreground hover:text-foreground")
              }
            >
              {label}
              {actif && (
                <span
                  className="absolute inset-x-0 -bottom-px h-0.5 rounded-t bg-gradient-to-r from-blue-700 to-amber-600"
                  aria-hidden="true"
                />
              )}
            </button>
          );
        })}
      </div>

      {onglet === "cylindres" && <CylindresOnglet />}
      {onglet === "porte-cliches" && <PorteClichesOnglet />}
    </main>
  );
}
