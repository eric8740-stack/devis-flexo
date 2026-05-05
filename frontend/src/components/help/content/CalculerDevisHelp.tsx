export function CalculerDevisHelp() {
  return (
    <div className="space-y-6 text-sm leading-relaxed">

      {/* ─────────────────────────────────────────────
          INTRO MÉTIER
       ────────────────────────────────────────────── */}
      <section>
        <p className="text-base">
          Cette page, c&apos;est <strong>le cœur de l&apos;app</strong>. Tu y construis ton devis flexo
          étape par étape — matière, couleurs, format, outillage, machine, finitions — et tu récupères
          ton prix au mille en moins d&apos;une minute, avec les vrais coûts de ta production.
        </p>
        <p>
          Le formulaire est <strong>pré-rempli sur un cas-test médian</strong> à l&apos;ouverture
          (étiquettes vélin 60×40 mm, 3 poses, 4 couleurs CMJN, Mark Andy P5, tirage 3 000 m).
          Tu peux le modifier librement — un clic sur <em>Calculer le devis</em> en bas et tu as ton résultat.
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          1. MODE DE CALCUL
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">1. Choisir le mode de calcul</h3>
        <img
          src="/help/calculer-devis/01-formulaire-haut.png"
          alt="Vue du haut du formulaire de calcul"
          className="rounded-md border shadow-sm my-3"
        />
        <p>
          Deux modes possibles selon ce que tu cherches :
        </p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Manuel</strong> (par défaut) : tu fixes l&apos;intervalle entre étiquettes
            (3 mm = preset V1a). Le prix au mille est calculé directement à partir de ce paramètre.
            <em> Recommandé pour démarrer.</em>
          </li>
          <li>
            <strong>Matching cylindres</strong> : l&apos;app cherche pour toi les 3 cylindres
            magnétiques les plus économiques compatibles avec ta hauteur (intervalle 2,5 → 15 mm).
            Le HT est identique entre candidats — seul le prix au mille varie selon le cylindre choisi.
          </li>
        </ul>
        <img
          src="/help/calculer-devis/03-mode-matching.png"
          alt="Mode Matching cylindres activé"
          className="rounded-md border shadow-sm my-3"
        />
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Astuce :</strong> commence en mode <em>Manuel</em> à 3 mm pour tes premiers devis.
          Quand tu maîtrises l&apos;outil, passe en <em>Matching</em> pour optimiser le coût sur
          les jobs où tu as une marge de manœuvre sur le format.
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          2. MATIÈRE ET FORMAT (P1)
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">2. Matière et format (poste P1)</h3>
        <p>Le poste P1, c&apos;est ta matière première. Trois champs :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Complexe matière</strong> : tu choisis dans le menu déroulant un complexe configuré
            dans <em>Paramètres &gt; Complexes</em> (vélin, BOPP, PE, etc.).
          </li>
          <li>
            <strong>Laize utile (mm)</strong> : la largeur exploitable de ta bobine.
          </li>
          <li>
            <strong>Tirage (mètres linéaires)</strong> : le nombre de mètres à produire.
          </li>
        </ul>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Piège classique :</strong> si tu choisis un complexe <em>sans grammage</em>
          (typiquement un BOPP ou PE), l&apos;app affiche une <strong>erreur 422</strong> et ne
          peut pas calculer P1. Le moteur dérive le prix au kg depuis <code>prix_m2 × 1000 / grammage</code> —
          sans grammage, pas de calcul. Solution : retourne dans <em>Paramètres &gt; Complexes</em> et
          renseigne le grammage manquant.
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          3. COULEURS (P2 + P3a)
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">3. Couleurs (postes P2 Encres + P3a Clichés)</h3>
        <p>
          Le nombre de couleurs impacte deux postes : la consommation d&apos;encre (P2) et le coût
          des clichés (P3a). Cinq champs distincts :
        </p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>Process CMJN</strong> : les 4 couleurs de quadrichromie classiques.</li>
          <li><strong>Black High Coverage</strong> : noir avec forte couverture (consomme plus d&apos;encre).</li>
          <li><strong>Pantone</strong> : couleurs d&apos;accompagnement (compter chaque référence Pantone).</li>
          <li><strong>Blanc High Opacity</strong> : blanc opacifiant (souvent utilisé sur film transparent).</li>
          <li><strong>Métallisée</strong> : encres argent / or / autres métalliques.</li>
        </ul>
        <p>
          Chaque case attend un nombre. Si tu ne mets pas un type de couleur, laisse 0.
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          4. FORMAT & OUTILLAGE (P3b)
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">4. Format étiquette &amp; outillage (poste P3b)</h3>
        <img
          src="/help/calculer-devis/02-formulaire-bas.png"
          alt="Format, outillage, machine, sous-traitance"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Quatre champs format :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>Format largeur (mm)</strong> et <strong>Format hauteur (mm)</strong> : dimensions de l&apos;étiquette finie.</li>
          <li>
            <strong>Poses largeur</strong> et <strong>Poses dévelop.</strong> : combien d&apos;étiquettes
            tu places par tour de cylindre, en largeur et en développé.
          </li>
        </ul>

        <h4 className="font-semibold mt-4 mb-2">Outil de découpe — 2 cas distincts</h4>

        <p><strong>Cas A — Outil existant (0 €)</strong></p>
        <p className="ml-2">
          L&apos;outil est déjà fabriqué et amorti, P3b est à 0. Tu peux laisser <em>(non référencé)</em> —
          c&apos;est juste pour tracer dans l&apos;audit. À la sélection d&apos;un outil du catalogue,
          les champs <em>Format largeur/hauteur</em> sont préremplis depuis l&apos;outil — tu peux
          toujours les modifier en cas de pose multiple.
        </p>

        <p className="mt-3"><strong>Cas B — Nouvel outil (à fabriquer)</strong></p>
        <img
          src="/help/calculer-devis/04-nouvel-outil.png"
          alt="Configuration d'un nouvel outil à fabriquer"
          className="rounded-md border shadow-sm my-3"
        />
        <p className="ml-2">
          Tu vas devoir faire fabriquer l&apos;outil. Le coût est ajouté au devis :{" "}
          <code>200 € + nb_tracés × 50 €</code>, multiplié par <strong>1,40</strong> si tu coches
          <em> Forme spéciale</em>. Les tracés correspondent au nombre de découpes différentes
          (1 tracé = forme simple, 2+ = formes complexes).
        </p>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Piège :</strong> le surcoût plaque <em>+40 %</em> de la forme spéciale est
          significatif. Coche <em>Forme spéciale</em> uniquement si la découpe est réellement
          atypique (étoile, contour irrégulier, multi-niveaux). Une étiquette rectangulaire ou
          rectangulaire à coins arrondis = forme classique.
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          5. MACHINE (P5 + P7)
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">5. Machine (postes P5 Roulage + P7 Main d&apos;œuvre)</h3>
        <p>
          Tu choisis ta presse flexo dans le menu déroulant. La <strong>vitesse moyenne réaliste</strong> et
          la <strong>durée de calage</strong> sont lues automatiquement depuis la fiche machine
          (configurée dans <em>Paramètres &gt; Machines</em>). Tu n&apos;as rien à saisir ici à part
          le choix de la presse.
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Bon à savoir :</strong> si une machine te manque dans la liste, va dans
          <em> Machines</em> pour la configurer (nb couleurs, vitesse m/min, coût horaire).
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          6. SOUS-TRAITANCE (P6)
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">6. Sous-traitance &amp; finitions (poste P6)</h3>
        <p>
          Si une partie du job part chez un partenaire (pelliculage, gaufrage, dorure à chaud, etc.),
          tu l&apos;ajoutes ici. Choisis le partenaire dans la liste, saisis le montant forfaitaire HT.
        </p>
        <p>
          Tu peux <strong>ajouter plusieurs partenaires</strong> sur le même devis — clique
          <em> + Ajouter un forfait ST</em> pour empiler les forfaits. Utile quand le job a plusieurs
          étapes externes (ex: pelliculage + dorure).
        </p>
        <img
          src="/help/calculer-devis/05-multi-st.png"
          alt="Plusieurs forfaits sous-traitance ajoutés"
          className="rounded-md border shadow-sm my-3"
        />
        <p>
          Pour retirer un forfait, clique <em>Retirer</em> à droite de la ligne.
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          7. OPTIONS AVANCÉES
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">7. Options avancées (calcul automatique par défaut)</h3>
        <p>
          Cette section est repliée par défaut — tu peux la laisser fermée, l&apos;app calcule tout
          en automatique. Tu l&apos;ouvres uniquement pour des cas particuliers :
        </p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Heures dossier</strong> : si tu sais que ce job va prendre plus de temps que la
            moyenne (machine en attente, maintenance pendant le tirage, devis post-prod avec heures réelles).
            Vide = calcul auto depuis machine + paramètres.
          </li>
          <li>
            <strong>Marge</strong> : pour appliquer une marge spécifique à ce devis, en pourcentage
            (exemple : 22 pour +22 %). Vide = marge par défaut de ton entreprise (configurée dans
            <em> Paramètres &gt; Entreprise</em>).
          </li>
        </ul>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Cas typiques d&apos;usage :</strong>
          <ul className="list-disc pl-6 mt-1 space-y-0.5">
            <li>Gros client négocié → marge réduite ponctuelle</li>
            <li>Job urgent en heures sup → heures dossier renseignées manuellement</li>
            <li>Refacturation après prod → tu mets les vraies heures passées pour figer le coût réel</li>
          </ul>
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          8. LANCER LE CALCUL
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">8. Lancer le calcul</h3>
        <p>
          Quand tout est rempli, clique <strong>Calculer le devis</strong> en bas à droite. Tu peux
          aussi cliquer <strong>Réinitialiser le formulaire</strong> pour repartir des valeurs
          par défaut (cas-test médian).
        </p>
        <p className="mt-2">Le résultat affiché te montre :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>Le <strong>HT total</strong> du devis (somme des 7 postes + finitions ST + marge)</li>
          <li>Le <strong>prix au mille</strong> (€ par 1 000 étiquettes) — référence client classique</li>
          <li>Le <strong>détail par poste</strong> P1 à P7 — pour comprendre d&apos;où vient ton prix</li>
        </ul>
        <p>
          Tu peux ensuite <strong>sauvegarder le devis</strong> (il apparaîtra dans la page
          <em> Devis</em>) et <strong>générer un PDF</strong> à envoyer à ton client.
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          PIÈGES CLASSIQUES (récap)
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Les 4 pièges classiques</h3>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 space-y-3">
          <div>
            <strong>1. Complexe sans grammage (BOPP, PE) → erreur 422.</strong>{" "}
            Renseigne le grammage dans <em>Paramètres &gt; Complexes</em> avant de lancer le devis.
          </div>
          <div>
            <strong>2. Confondre &laquo; outil existant &raquo; et &laquo; nouvel outil &raquo;.</strong>{" "}
            Outil existant = 0 €, déjà amorti. Nouvel outil = facturation au client (200 € minimum).
          </div>
          <div>
            <strong>3. Cocher Forme spéciale par défaut.</strong> Le +40 % sur la plaque est
            significatif — coche uniquement si la découpe est vraiment atypique.
          </div>
          <div>
            <strong>4. Renseigner les heures dossier pour rien.</strong> Laisse vide tant que tu n&apos;es
            pas dans un cas particulier — l&apos;app calcule mieux que toi en automatique pour les jobs
            standards.
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          MOT DE LA FIN
       ────────────────────────────────────────────── */}
      <section>
        <p className="text-sm italic text-muted-foreground">
          Tu peux toujours faire un essai, regarder le résultat, modifier un paramètre et recalculer.
          C&apos;est fait pour ça — explore, joue avec les valeurs, c&apos;est comme ça que tu vas
          apprivoiser l&apos;outil.
        </p>
      </section>

    </div>
  )
}
