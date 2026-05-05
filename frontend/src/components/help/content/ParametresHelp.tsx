export function ParametresHelp() {
  return (
    <div className="space-y-6 text-sm leading-relaxed">

      {/* ─────────────────────────────────────────────
          INTRO MÉTIER
       ────────────────────────────────────────────── */}
      <section>
        <p className="text-base">
          Cette page, c&apos;est <strong>l&apos;ADN tarifaire de ton entreprise</strong>. Tu y règles
          les prix de référence des différents postes du moteur de coût — clichés, calage, roulage,
          finitions, main d&apos;œuvre — et c&apos;est ce qui va déterminer le résultat de tous tes devis.
        </p>
        <p>
          Une fois bien configurée, tu n&apos;y reviens que ponctuellement, quand tes tarifs évoluent
          (revalorisation annuelle, nouveau coût horaire après investissement machine, etc.).
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          COMMENT ÇA MARCHE
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Comment ça marche</h3>
        <p>
          La page est organisée en <strong>onglets — un onglet par poste paramétrable</strong>.
          Tu choisis l&apos;onglet du poste à modifier, tu changes les valeurs, et tu cliques
          <strong> Sauvegarder Poste X</strong> en bas de l&apos;onglet pour valider.
        </p>
        <p>
          Chaque champ a des <strong>bornes min/max</strong> affichées à droite. Si tu sors des
          bornes, l&apos;app refuse la sauvegarde — c&apos;est un garde-fou contre les fautes de frappe.
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 À savoir :</strong> il n&apos;y a pas d&apos;onglet pour <em>Poste 2 — Encres</em>.
          C&apos;est normal : le coût des encres est calculé automatiquement par le moteur en fonction
          du nombre de couleurs et de la couverture saisis dans <em>Calculer un devis</em>. Tu n&apos;as
          rien à paramétrer côté tarif pour P2.
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          POSTE 1 — MATIÈRE (P1)
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Poste 1 — Matière (P1)</h3>
        <img
          src="/help/parametres/01-poste1-matiere.png"
          alt="Onglet Poste 1 Matière"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Deux paramètres :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Prix matière par kilo (€/kg)</strong> — c&apos;est le prix par défaut utilisé{" "}
            <em>si le complexe choisi sur le devis n&apos;a pas son propre prix</em> renseigné.
            Plage : 0,80 → 5,00 €/kg.
          </li>
          <li>
            <strong>Marge de confort en roulage / surface support (mm)</strong> — la marge ajoutée
            à la laize utile pour calculer la surface support réelle (avec dispositions de bobines, etc.).
            Plage : 5 → 30 mm.
          </li>
        </ul>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Bon réflexe :</strong> renseigne les vrais prix matière dans tes complexes
          (<em>Paramètres &gt; Complexes</em>) — ce sera plus précis. La valeur défaut ici sert
          uniquement de filet de sécurité pour les complexes sans prix renseigné.
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          POSTE 3 — OUTILLAGE / CLICHÉS
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Poste 3 — Outillage / Clichés (P3a + P3b)</h3>
        <img
          src="/help/parametres/02-poste3-outillage-cliches.png"
          alt="Onglet Poste 3 Outillage / Clichés"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Quatre paramètres regroupés ici car liés à la fabrication des outils &amp; plaques :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Prix d&apos;un cliché par couleur (€/couleur)</strong> — multiplié par le nombre
            de couleurs total saisi sur le devis (P3a). Plage : 25 → 100 €/couleur.
          </li>
          <li>
            <strong>Coût outil neuf forfait fixe (€)</strong> — la base si tu coches{" "}
            <em>Nouvel outil (à fabriquer)</em> sur le devis. Plage : 80 → 800 €.
          </li>
          <li>
            <strong>Coût par tracé de complexité (€)</strong> — additionnel pour chaque tracé de
            l&apos;outil neuf. Plage : 15 → 250 €.
          </li>
          <li>
            <strong>Majoration forme spéciale (×)</strong> — multiplicateur appliqué au coût outil
            neuf si la forme est cochée comme spéciale. Plage : 1,0 → 3,0.
          </li>
        </ul>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Attention :</strong> ces paramètres impactent <em>tous tes devis avec nouvel outil</em>.
          Une modification ici a un effet immédiat sur tes prochains devis — fais une revue cohérente
          si tu modifies (par exemple : si tu augmentes le coût de base, vérifie aussi la majoration
          forme spéciale en parallèle).
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          POSTE 4 — MISE EN ROUTE / CALAGE
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Poste 4 — Mise en route / Calage (P4)</h3>
        <img
          src="/help/parametres/03-poste4-calage.png"
          alt="Onglet Poste 4 Mise en route / Calage"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Un seul paramètre :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Calage forfaitaire par devis (€/devis)</strong> — un forfait fixe appliqué une
            fois sur chaque devis pour la mise en route et le calage. Indépendant du tirage.
            Plage : 100 → 600 €.
          </li>
        </ul>
        <p>
          Ce poste représente le coût fixe de démarrage de la presse qui est dilué sur le tirage
          (plus le tirage est gros, plus le P4 par mille devient faible — c&apos;est mécanique).
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          POSTE 5 — ROULAGE PRESSE
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Poste 5 — Roulage presse (P5)</h3>
        <img
          src="/help/parametres/04-poste5-roulage.png"
          alt="Onglet Poste 5 Roulage presse"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Un paramètre :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Prix horaire de roulage presse (€/h)</strong> — le coût horaire machine
            multiplié par la durée de roulage calculée par l&apos;app (en fonction du tirage et
            de la vitesse de la machine choisie). Plage : 200 → 800 €/h.
          </li>
        </ul>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Cohérence à vérifier :</strong> ce prix horaire P5 doit être cohérent avec les
          coûts horaires que tu renseignes dans <em>Machines</em>. Si tu modifies P5 ici, vérifie
          que tes machines référentes restent à jour aussi.
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          POSTE 6 — FINITIONS
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Poste 6 — Finitions (P6)</h3>
        <img
          src="/help/parametres/05-poste6-finitions.png"
          alt="Onglet Poste 6 Finitions"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Un paramètre :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Prix finitions par m² (€/m²)</strong> — tarif des opérations de finition standard
            (vernissage en ligne, etc.) appliqué à la surface produite. Plage : 0,03 → 0,50 €/m².
          </li>
        </ul>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 À ne pas confondre :</strong> P6 ici = <em>finitions intégrées à ton process</em>
          (au m²). Les <em>finitions sous-traitées</em> (pelliculage, dorure, etc.) se gèrent à part
          dans <em>Calculer un devis &gt; Sous-traitance</em> avec un montant forfaitaire par partenaire.
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          POSTE 7 — MAIN D'ŒUVRE
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Poste 7 — Main d&apos;œuvre (P7)</h3>
        <img
          src="/help/parametres/06-poste7-main-doeuvre.png"
          alt="Onglet Poste 7 Main d'œuvre"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Un paramètre :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Prix horaire main d&apos;œuvre opérateur (€/h)</strong> — le coût horaire de
            l&apos;opérateur machine, utilisé pour le calage et le roulage. Plage : 40 → 120 €/h.
          </li>
        </ul>
        <p>
          C&apos;est ton vrai coût horaire chargé (salaire + charges sociales + congés, etc.), pas
          le brut. Si tu travailles seul, c&apos;est ton coût horaire à toi.
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          PIÈGES CLASSIQUES
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Les 3 pièges classiques</h3>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 space-y-3">
          <div>
            <strong>1. Modifier sans sauvegarder.</strong> Chaque onglet a son propre bouton
            <em> Sauvegarder Poste X</em>. Si tu changes des valeurs sur P3 puis que tu cliques sur
            l&apos;onglet P5 sans sauvegarder, tes modifications de P3 sont perdues. Réflexe :
            sauvegarde avant de changer d&apos;onglet.
          </div>
          <div>
            <strong>2. Sortir des bornes min/max.</strong> Si tu saisis une valeur hors plage
            (par exemple 1 000 €/h en P5 alors que le max est 800), l&apos;app refuse. Vérifie les
            bornes affichées à droite de chaque champ.
          </div>
          <div>
            <strong>3. Modifier P5 (roulage) sans aligner avec Machines.</strong> Le coût horaire de
            roulage doit rester cohérent avec les coûts horaires saisis dans
            <em> Paramètres &gt; Machines</em>. Sinon tu peux te retrouver avec des écarts entre tes
            machines individuelles et le tarif global.
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          MOT DE LA FIN
       ────────────────────────────────────────────── */}
      <section>
        <p className="text-sm italic text-muted-foreground">
          Cette page, tu la configureras une fois bien à fond au démarrage avec moi en visio,
          et après tu la laisseras tranquille — tu y reviendras 1 ou 2 fois par an quand tes coûts
          réels auront évolué. C&apos;est l&apos;équivalent d&apos;un règlement de tarif chez ton
          comptable : on règle, on revoit ponctuellement.
        </p>
      </section>

    </div>
  )
}
