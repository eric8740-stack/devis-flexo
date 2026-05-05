export function ProduitsClientsHelp() {
  return (
    <div className="space-y-6 text-sm leading-relaxed">

      {/* INTRO MÉTIER */}
      <section>
        <p className="text-base">
          Cette page, c&apos;est <strong>ton catalogue de produits récurrents</strong> par client —
          les étiquettes types que tes clients commandent régulièrement, avec leurs paramètres
          mémorisés (format, couleurs, matière, prix unitaire de référence). L&apos;objectif :
          gagner du temps sur les renouvellements de commande sans tout re-saisir à chaque devis.
        </p>
        <p>
          Quand un client refait sa commande annuelle de millésime ou sa série mensuelle de
          confitures, tu retrouves vite ses spécifications, et tu peux créer un nouveau devis
          avec les mêmes paramètres en quelques clics.
        </p>
      </section>

      {/* VUE D'ENSEMBLE LISTE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Vue d&apos;ensemble — la liste de tes produits</h3>
        <img
          src="/help/produits-clients/01-liste-produits-clients.png"
          alt="Liste du catalogue produits clients"
          className="rounded-md border shadow-sm my-3"
        />
        <p>La page liste tes produits avec, pour chacun :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>#</strong> : ordre d&apos;ajout</li>
          <li><strong>Code</strong> : ton code produit interne (ex: <code>VIN_75CL_2025</code>, <code>CONF_FRAISE_TX</code>)</li>
          <li><strong>Désignation</strong> : description complète et parlante (ex: « Étiquette bouteille 75cl millésime 2025 »)</li>
          <li><strong>Client (ID)</strong> : à quel client appartient ce produit (ID numérique)</li>
          <li><strong>Format</strong> : dimensions LxH en mm (ex: 75x100)</li>
          <li><strong>Couleurs</strong> : nombre de couleurs imprimées</li>
          <li><strong>Prix unit. (€)</strong> : prix unitaire de référence (par étiquette)</li>
          <li><strong>Fréquence</strong> : périodicité de la commande (annuelle / trimestrielle / mensuelle / ponctuelle)</li>
          <li><strong>Actions</strong> : crayon = éditer, poubelle = supprimer</li>
        </ul>
      </section>

      {/* FILTRE PAR CLIENT */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Le filtre par ID client</h3>
        <p>
          En haut de page, tu trouves un champ <em>Filtrer par ID client</em>. Saisis l&apos;ID
          numérique d&apos;un client (que tu trouves dans la page <em>Clients</em>) et clique{" "}
          <strong>Filtrer</strong> — la liste affiche uniquement les produits de ce client.
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Quand l&apos;utiliser :</strong> dès que tu auras 30+ produits dans le catalogue,
          ce filtre devient indispensable. Avant un appel client, filtre par son ID pour avoir sous
          les yeux tous ses produits récurrents — gain de temps assuré.
        </div>
      </section>

      {/* LES 4 FRÉQUENCES */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Les 4 fréquences disponibles</h3>
        <p>La fréquence indique à quelle périodicité ce produit est commandé par le client :</p>
        <div className="my-3 overflow-x-auto">
          <table className="text-xs border-collapse border border-gray-300 w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-300 px-2 py-1 text-left">Fréquence</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Quand l&apos;utiliser</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Exemples typiques</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">annuelle</td>
                <td className="border border-gray-300 px-2 py-1">Commande 1 fois par an</td>
                <td className="border border-gray-300 px-2 py-1">Étiquettes vin avec millésime, calendriers</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">trimestrielle</td>
                <td className="border border-gray-300 px-2 py-1">Commande tous les 3 mois</td>
                <td className="border border-gray-300 px-2 py-1">Confitures saisonnières, séries cosmétiques</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">mensuelle</td>
                <td className="border border-gray-300 px-2 py-1">Commande chaque mois</td>
                <td className="border border-gray-300 px-2 py-1">Production récurrente, codes-barres logistique</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">ponctuelle</td>
                <td className="border border-gray-300 px-2 py-1">Commande unique ou imprévisible</td>
                <td className="border border-gray-300 px-2 py-1">Tests, événementiel, lancement produit</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          La fréquence n&apos;impacte pas le calcul du devis directement, mais elle te sert pour
          tes statistiques internes (volume mensuel/annuel par client) et pour anticiper tes
          renouvellements.
        </p>
      </section>

      {/* CONVENTION NOMENCLATURE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Convention de nomenclature pour le Code produit</h3>
        <p>
          Avec 50+ produits dans ton catalogue, une nomenclature claire devient essentielle.
          Voici la convention conseillée, illustrée par les exemples du seed :
        </p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><code>VIN_75CL_2025</code> → secteur (VIN) _ contenance (75CL) _ millésime (2025)</li>
          <li><code>CONF_FRAISE_TX</code> → secteur (CONF) _ parfum (FRAISE) _ format (TX)</li>
          <li><code>COSM_FLACON_NATURE</code> → secteur (COSM) _ contenant (FLACON) _ gamme (NATURE)</li>
        </ul>
        <p>
          <strong>Format conseillé</strong> : <em>SECTEUR_CARACTÉRISTIQUE_VARIANTE</em> en majuscules
          séparés par des underscores. Évite les espaces et caractères spéciaux pour un copier-coller
          facile.
        </p>
      </section>

      {/* AJOUTER UN PRODUIT */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Ajouter un nouveau produit</h3>
        <p>Clique <strong>+ Nouveau produit</strong> en haut à droite. Le formulaire s&apos;ouvre :</p>
        <img
          src="/help/produits-clients/02-formulaire-produit.png"
          alt="Formulaire de création d'un produit catalogue"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Voici chaque champ en détail :</p>

        <h4 className="font-semibold mt-4 mb-1">Code produit <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Ton code interne court et structuré pour identifier ce produit (ex: <code>VIN_75CL_2025</code>).
          Suis la nomenclature ci-dessus pour t&apos;y retrouver rapidement.
        </p>

        <h4 className="font-semibold mt-4 mb-1">ID Client (FK) <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          ID numérique du client à qui ce produit appartient. Tu dois le récupérer manuellement
          depuis la page <em>Clients</em>.
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Astuce :</strong> avant de saisir un nouveau produit, ouvre la page{" "}
          <em>Clients</em> dans un onglet séparé pour avoir la liste des IDs sous les yeux.
          Tu pourras alors reporter rapidement les bons identifiants côté produit.
        </div>

        <h4 className="font-semibold mt-4 mb-1">Désignation <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Description complète et parlante du produit, comme tu la communiquerais à ton client.
          Exemples : <em>« Étiquette bouteille 75cl millésime 2025 »</em>,{" "}
          <em>« Étiquette pot 250g confiture fraise »</em>. C&apos;est ce qui sera affiché dans
          ton devis et qui parle à ton interlocuteur.
        </p>

        <h4 className="font-semibold mt-4 mb-1">ID Machine (FK) (optionnel)</h4>
        <p className="ml-2">
          ID de la machine sur laquelle ce produit est habituellement imprimé. Utile si tu as
          plusieurs presses et que certains produits sont systématiquement orientés vers une
          machine précise (ex: les étiquettes UV vont toujours sur la Mark Andy).
        </p>

        <h4 className="font-semibold mt-4 mb-1">Format (mm) (optionnel)</h4>
        <p className="ml-2">
          Dimensions de l&apos;étiquette en mm, format <em>LxH</em> (largeur × hauteur).
          Exemple : <code>75x100</code> pour une étiquette de 75 mm de large et 100 mm de haut.
          Mémoriser ce format évite de devoir le re-saisir à chaque renouvellement.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Nb couleurs (optionnel)</h4>
        <p className="ml-2">
          Nombre de couleurs imprimées sur ce produit (typiquement 1 à 8). Aide à anticiper les
          temps de calage et le coût de production lors d&apos;un nouveau devis.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Matière (optionnel)</h4>
        <p className="ml-2">
          Le complexe utilisé habituellement pour ce produit (ex: « VELIN_STANDARD_80 »,
          « BOPP_BLANC_50 »). Tu peux saisir la référence du complexe ou un libellé descriptif.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Prix unitaire (€) (optionnel)</h4>
        <p className="ml-2">
          Prix unitaire de référence par étiquette (ex: 0,0850 € pour une étiquette vin standard).
          C&apos;est la <strong>valeur de référence historique</strong>. Au moment du devis tu peux
          ajuster en fonction des conditions du moment (volume, urgence, évolution des coûts matière).
        </p>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Attention :</strong> ce prix est un <em>repère historique</em>. Mets-le à jour
          régulièrement (au moins une fois par an) si les coûts évoluent — un prix unitaire qui
          date de 2 ans peut sous-estimer ta marge réelle de 10-20 %.
        </div>

        <h4 className="font-semibold mt-4 mb-1">Fréquence (optionnel)</h4>
        <p className="ml-2">
          Sélectionne dans le dropdown la périodicité typique de commande
          (<em>annuelle / trimestrielle / mensuelle / ponctuelle</em>). Utile pour tes statistiques
          internes et pour anticiper tes renouvellements.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Statut</h4>
        <p className="ml-2">
          <em>Actif</em> par défaut. Mets à <em>inactif</em> si le produit n&apos;est plus
          commandé (le client a arrêté la gamme par ex.) sans le supprimer — tu gardes
          l&apos;historique.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Commentaire (optionnel)</h4>
        <p className="ml-2">
          Note libre pour rappeler des particularités : <em>« nécessite vernis UV obligatoire »</em>,
          <em> « tirage habituel 5000 m »</em>, <em>« attention BAT obligatoire avant chaque édition »</em>,
          <em> « client préfère bobine mère 4000 m »</em>, etc.
        </p>

        <p className="mt-3">
          Quand tout est rempli, clique <strong>Créer</strong>. Le produit apparaît dans le catalogue
          et devient retrouvable via le filtre par ID client.
        </p>
      </section>

      {/* COMMENT ÇA S'INTÈGRE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Comment ça s&apos;intègre dans ton workflow</h3>
        <p>
          Pour l&apos;instant, ce catalogue sert de <strong>base de référence</strong> pour
          retrouver rapidement les paramètres d&apos;un produit récurrent quand un client te
          recontacte. Tu consultes la fiche, tu notes les paramètres (format, couleurs, matière,
          prix unitaire de référence), et tu crées un nouveau devis avec les mêmes spécifications
          dans <em>Calculer un devis</em>.
        </p>
        <p>
          C&apos;est aussi un excellent outil de <strong>traçabilité commerciale</strong> :
          combien de produits par client, à quelle fréquence, quel volume estimé sur l&apos;année.
          Avec un catalogue tenu à jour, tu peux préparer tes campagnes de relance commerciale et
          tes prévisions de production.
        </p>
      </section>

      {/* MODIFIER OU SUPPRIMER */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Modifier ou supprimer un produit</h3>
        <p>Sur la liste, dans la colonne <em>Actions</em> :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>Crayon ✏️</strong> = éditer le produit. Pré-rempli avec les valeurs actuelles.</li>
          <li><strong>Poubelle 🗑️</strong> = supprimer définitivement. À utiliser avec précaution.</li>
        </ul>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Suppression vs Désactivation :</strong> si le produit a déjà été utilisé sur
          des devis sauvegardés, mieux vaut passer son <em>Statut</em> à <em>inactif</em> que le
          supprimer. Tu masques le produit sans casser l&apos;historique.
        </div>
      </section>

      {/* PIÈGES CLASSIQUES */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Les 4 pièges classiques</h3>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 space-y-3">
          <div>
            <strong>1. Confondre Code produit et Désignation.</strong> <em>Code</em> = ta nomenclature
            courte interne (<code>VIN_75CL_2025</code>). <em>Désignation</em> = description longue
            et parlante (« Étiquette bouteille 75cl millésime 2025 »). Le code est pour toi,
            la désignation est pour ton client.
          </div>
          <div>
            <strong>2. Ne pas mettre à jour le prix unitaire.</strong> Si le prix unitaire date
            de 2 ans, il sous-estime probablement tes coûts actuels de 10-20 %. Bloque-toi 1h par
            an pour ré-évaluer tous tes prix de référence.
          </div>
          <div>
            <strong>3. Saisir une fréquence incohérente.</strong> Si tu mets « annuelle » sur un
            produit en réalité ponctuel (test, événementiel), tu pollues tes statistiques de volume
            prévu. Préfère <em>ponctuelle</em> par défaut quand tu hésites.
          </div>
          <div>
            <strong>4. Ne pas utiliser le filtre par ID client.</strong> À partir de 30+ produits,
            scroller la liste devient une perte de temps. Avant chaque appel client, filtre par
            son ID — gain de temps immédiat.
          </div>
        </div>
      </section>

      {/* MOT DE LA FIN */}
      <section>
        <p className="text-sm italic text-muted-foreground">
          Ton catalogue produits, c&apos;est la mémoire commerciale de ton entreprise — bien tenu
          à jour, il te fait gagner un temps fou sur les renouvellements et te donne une vision
          claire de la valeur récurrente que tu produis pour chacun de tes clients.
        </p>
      </section>

    </div>
  )
}
