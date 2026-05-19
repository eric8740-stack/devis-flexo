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
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Mon parc</h1>
        <p className="text-sm text-muted-foreground">
          Tes cylindres magnétiques et tes porte-clichés. Tu peux en ajouter,
          désactiver les anciens, réactiver à volonté. Pas besoin de tout
          configurer — un parc prêt à l&apos;emploi t&apos;a été pré-rempli.
        </p>
      </header>

      <div className="flex gap-1 border-b border-border">
        <button
          type="button"
          onClick={() => switchOnglet("cylindres")}
          className={
            "rounded-t-md px-4 py-2 text-sm font-medium transition-colors " +
            (onglet === "cylindres"
              ? "border-b-2 border-blue-700 text-blue-900"
              : "text-muted-foreground hover:text-foreground")
          }
        >
          🔧 Mes cylindres
        </button>
        <button
          type="button"
          onClick={() => switchOnglet("porte-cliches")}
          className={
            "rounded-t-md px-4 py-2 text-sm font-medium transition-colors " +
            (onglet === "porte-cliches"
              ? "border-b-2 border-blue-700 text-blue-900"
              : "text-muted-foreground hover:text-foreground")
          }
        >
          📐 Mes porte-clichés
        </button>
      </div>

      {onglet === "cylindres" && <CylindresOnglet />}
      {onglet === "porte-cliches" && <PorteClichesOnglet />}
    </main>
  );
}
