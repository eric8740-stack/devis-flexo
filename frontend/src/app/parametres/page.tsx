import Link from "next/link";

// Brief #29 : page d'accueil Paramètres. Auparavant simple redirect
// vers /parametres/tarifs ; désormais affiche une card joyeuse "Mon parc"
// (accès discret au CRUD cylindres + porte-clichés) + une carte de
// raccourcis vers les autres sections, conformément à la philosophie
// UX "CRUD parc = option, pas obligation, aucune entrée sidebar".
export default function ParametresIndex() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Bienvenue dans tes paramètres</h2>
        <p className="text-sm text-muted-foreground">
          Tout ce qui personnalise tes devis : tarifs, options, parc matériel.
          Aucune obligation de configurer avant ton premier devis — tu as déjà
          un parc démo prêt à l&apos;emploi.
        </p>
      </div>

      <Link
        href="/parametres/mon-parc"
        className="block rounded-lg border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-amber-50 p-6 transition-colors hover:border-blue-400 hover:shadow-sm"
      >
        <div className="flex items-start gap-4">
          <div className="text-4xl">🔧</div>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-blue-900">
              Mon parc
            </h3>
            <p className="mt-1 text-sm text-blue-900/80">
              Tes cylindres magnétiques et tes porte-clichés (sleeves). Ajoute,
              désactive, retrouve facilement ce que tu utilises sur tes machines.
            </p>
            <p className="mt-2 text-xs text-blue-900/60">
              Pré-rempli avec un parc démo standard flexo · accès direct à tout
              moment depuis cette page.
            </p>
          </div>
          <div className="text-2xl text-blue-700">→</div>
        </div>
      </Link>

      <div className="rounded-md border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
        Tu peux aussi explorer les sections classiques dans la barre de gauche
        (tarifs, entreprise, options de fabrication, etc.).
      </div>
    </div>
  );
}
