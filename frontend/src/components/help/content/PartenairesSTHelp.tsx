export function PartenairesSTHelp() {
  return (
    <div className="space-y-6 text-sm leading-relaxed">

      {/* INTRO MÉTIER */}
      <section>
        <p className="text-base">
          Cette page, c&apos;est <strong>ton réseau de partenaires sous-traitants</strong> — les
          entreprises externes auxquelles tu confies certaines opérations que tu ne fais pas en
          interne (pelliculage spécifique, dorure complexe, découpe forme particulière, etc.).
          Chaque partenaire est référencé avec ses coordonnées, son délai moyen et ta note qualité.
        </p>
        <p>
          C&apos;est différent de ta liste d&apos;<em>opérations de finition internes</em> (Op. finition),
          où tu référenceras tout ce que tu fais <strong>sur ton propre matériel</strong>. Ici on parle
          uniquement de ce qui sort de l&apos;atelier pour aller chez quelqu&apos;un d&apos;autre.
        </p>
      </section>

      {/* RAPPEL DISTINCTION */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Rappel — 3 endroits qui parlent de finitions</h3>
        <div className="my-3 overflow-x-auto">
          <table className="text-xs border-collapse border border-gray-300 w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-300 px-2 py-1 text-left">Endroit</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Type</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Tarif comment ?</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">Op. finition</td>
                <td className="border border-gray-300 px-2 py-1">Catalogue interne sur tes machines</td>
                <td className="border border-gray-300 px-2 py-1">Coût + temps unitaires en BDD</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">Paramètres &gt; P6</td>
                <td className="border border-gray-300 px-2 py-1">Prix fixe au m² du moteur</td>
                <td className="border border-gray-300 px-2 py-1">Tarif global du moteur</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">Partenaires ST (cette page)</td>
                <td className="border border-gray-300 px-2 py-1"><strong>Sous-traitance externe</strong></td>
                <td className="border border-gray-300 px-2 py-1"><strong>Montant forfaitaire saisi à chaque devis</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs italic text-muted-foreground">
          Point important : sur cette page, tu ne saisis <strong>aucun prix</strong> à l&apos;avance.
          Le tarif est saisi au cas par cas dans <em>Calculer un devis &gt; Sous-traitance</em>,
          parce qu&apos;il dépend du job spécifique (volume, complexité, type d&apos;étiquette).
        </p>
      </section>

      {/* VUE D'ENSEMBLE LISTE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Vue d&apos;ensemble — la liste de tes partenaires</h3>
        <img
          src="/help/partenaires-st/01-liste-partenaires-st.png"
          alt="Liste des partenaires sous-traitance"
          className="rounded-md border shadow-sm my-3"
        />
        <p>La page liste tes partenaires avec, pour chacun :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>#</strong> : ordre d&apos;ajout</li>
          <li><strong>Raison sociale</strong> : nom commercial du partenaire (ex: « Pelliculage Express SARL »)</li>
          <li><strong>Prestation</strong> : type de service qu&apos;il propose (<code>finition</code>, <code>dorure</code>, <code>decoupe</code>...)</li>
          <li><strong>Délai (j)</strong> : délai moyen en jours pour récupérer le travail terminé</li>
          <li><strong>Qualité (1-5)</strong> : ta note interne — comme un système d&apos;étoiles</li>
          <li><strong>Statut</strong> : <em>Actif</em> = sélectionnable dans Calculer un devis</li>
          <li><strong>Actions</strong> : crayon = éditer, poubelle = supprimer</li>
        </ul>
        <p>
          La case <em>Afficher les partenaires inactifs</em> en haut te permet de retrouver ceux que
          tu n&apos;utilises plus mais que tu veux garder en historique (ex: partenaire qui a fermé,
          ou qualité dégradée).
        </p>
      </section>

      {/* AJOUTER UN PARTENAIRE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Ajouter un nouveau partenaire</h3>
        <p>Clique <strong>+ Nouveau partenaire</strong> en haut à droite. Le formulaire s&apos;ouvre :</p>
        <img
          src="/help/partenaires-st/02-formulaire-partenaire.png"
          alt="Formulaire de création d'un partenaire sous-traitance"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Voici chaque champ en détail :</p>

        <h4 className="font-semibold mt-4 mb-1">Raison sociale <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Nom commercial du partenaire — exactement comme il apparaît sur ses factures. Exemples :
          <em> « Pelliculage Express SARL »</em>, <em>« Dorure Lyonnaise »</em>,
          <em> « Découpe Numérique Pro »</em>. Ce libellé sera affiché dans le dropdown de
          Calculer un devis &gt; Sous-traitance.
        </p>

        <h4 className="font-semibold mt-4 mb-1">SIRET (optionnel)</h4>
        <p className="ml-2">
          Numéro SIRET de l&apos;entreprise — utile pour traçabilité administrative et compta.
          Format : 14 chiffres sans espaces.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Contact (optionnel)</h4>
        <p className="ml-2">
          Nom du contact direct chez ce partenaire — la personne que tu appelles habituellement
          (ex: <em>« M. Dupont, responsable production »</em>). T&apos;évite de chercher dans tes
          mails à chaque besoin.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Téléphone (optionnel)</h4>
        <p className="ml-2">
          Le numéro direct ou standard du partenaire. Format libre.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Email (optionnel)</h4>
        <p className="ml-2">
          Email du contact ou adresse générique de l&apos;entreprise (ex: contact@pelliculage-express.fr).
        </p>

        <h4 className="font-semibold mt-4 mb-1">Type de prestation</h4>
        <p className="ml-2">
          Dropdown qui catégorise ce que fait le partenaire : <code>finition</code>,{" "}
          <code>dorure</code>, <code>decoupe</code>, etc. Sert à filtrer rapidement quand tu as
          plusieurs partenaires : par exemple, si un client demande de la dorure, tu vois directement
          tes partenaires « dorure ».
        </p>

        <h4 className="font-semibold mt-4 mb-1">Délai moyen (jours)</h4>
        <p className="ml-2">
          Le nombre de jours typique pour récupérer le travail terminé après envoi. Important pour
          anticiper tes délais de production globaux et pour informer ton client final. Si un partenaire
          est lent (10+ jours), c&apos;est aussi un signal que tu veux peut-être trouver une alternative.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Note qualité (1-5)</h4>
        <p className="ml-2">
          Ta note interne sur la qualité du partenaire — comme un système d&apos;étoiles. Échelle
          conseillée :
        </p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>5</strong> : qualité irréprochable, partenaire de référence</li>
          <li><strong>4</strong> : très bon, défauts mineurs occasionnels</li>
          <li><strong>3</strong> : correct, à surveiller</li>
          <li><strong>2</strong> : qualité aléatoire, dépannage uniquement</li>
          <li><strong>1</strong> : à éviter, garde la fiche pour mémoire</li>
        </ul>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Astuce :</strong> ré-évalue tes partenaires une fois par an. La qualité d&apos;un
          sous-traitant peut évoluer (changement d&apos;équipe, nouvelle machine, changement de
          dirigeant…). Tenir tes notes à jour t&apos;évite de retomber sur les mêmes mauvaises
          surprises.
        </div>

        <h4 className="font-semibold mt-4 mb-1">Actif (case à cocher)</h4>
        <p className="ml-2">
          Cochée par défaut. <strong>Décoche-la</strong> si tu veux masquer ce partenaire dans le
          dropdown de Calculer un devis sans supprimer la fiche (ex: partenaire en panne longue,
          relation suspendue temporairement). L&apos;historique des devis qui ont fait appel à ce
          partenaire reste intact.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Commentaire (optionnel)</h4>
        <p className="ml-2">
          Note libre pour toi-même. Très utile pour rappeler des particularités : <em>« min de
          commande 1000 m² »</em>, <em>« facturation à 30 jours fin de mois »</em>,
          <em> « préfère commande par mail uniquement »</em>, <em>« attention délai +2 jours en
          juillet/août »</em>, etc.
        </p>

        <p className="mt-3">
          Quand tout est rempli, clique <strong>Créer</strong>. Le partenaire apparaît dans la liste
          et devient sélectionnable dans Calculer un devis (si Actif coché).
        </p>
      </section>

      {/* COMMENT C'EST UTILISÉ */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Comment c&apos;est utilisé dans un devis</h3>
        <p>
          Au moment de faire un devis, dans <em>Calculer un devis</em>, tu trouves une section
          <strong> Sous-traitance (P6 Finitions)</strong>. Dans cette section, tu peux ajouter une ou
          plusieurs lignes en sélectionnant un partenaire dans la liste déroulante (alimentée par
          cette page) et en saisissant le <strong>montant forfaitaire</strong> qu&apos;il te facture
          pour ce job spécifique.
        </p>
        <p>
          Le montant que tu saisis là dépend du devis envoyé par ton partenaire pour ce job précis —
          c&apos;est pour ça qu&apos;il n&apos;y a pas de tarif fixe sur la fiche partenaire : chaque
          job est différent (volume, complexité, type d&apos;étiquette).
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Bonnes pratiques :</strong> demande systématiquement un devis à ton partenaire
          avant de saisir un job en sous-traitance dans Calculer un devis. Ça évite les surprises
          en fin de mois et te garantit que ton tarif client couvre vraiment ce que tu vas payer.
        </div>
      </section>

      {/* MODIFIER OU SUPPRIMER */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Modifier ou supprimer un partenaire</h3>
        <p>Sur la liste, dans la colonne <em>Actions</em> :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>Crayon ✏️</strong> = éditer la fiche partenaire. Pré-remplie avec les valeurs actuelles.</li>
          <li><strong>Poubelle 🗑️</strong> = supprimer définitivement. À utiliser avec précaution.</li>
        </ul>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Suppression vs Désactivation :</strong> si le partenaire a déjà été utilisé sur
          des devis sauvegardés, <strong>ne supprime pas</strong>, décoche juste <em>Actif</em>.
          La suppression est à réserver aux fiches créées par erreur ou jamais utilisées.
        </div>
      </section>

      {/* PIÈGES CLASSIQUES */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Les 3 pièges classiques</h3>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 space-y-3">
          <div>
            <strong>1. Confondre Op. finition (interne) et Partenaires ST (externe).</strong>{" "}
            Si tu vernis toi-même sur ta presse, c&apos;est dans <em>Op. finition</em>.
            Si tu envoies à Pelliculage Express pour qu&apos;ils le fassent, c&apos;est ici.
            La règle : « ça quitte mon atelier ? » → Partenaire ST. « Ça reste chez moi ? » → Op. finition.
          </div>
          <div>
            <strong>2. Saisir un prix dans la fiche partenaire (par habitude).</strong>{" "}
            Il n&apos;y a volontairement pas de champ prix sur cette fiche. Le tarif est saisi
            <em> au moment du devis</em> (Calculer un devis &gt; Sous-traitance) parce qu&apos;il
            dépend du job spécifique. Demande un devis à ton partenaire à chaque job sérieux.
          </div>
          <div>
            <strong>3. Ne pas tenir à jour la note qualité.</strong> Un partenaire qui était excellent
            il y a 2 ans peut s&apos;être détérioré. Si tu ne mets pas à jour ta note, tu retomberas
            sur les mêmes mauvaises expériences. Bloque-toi 30 minutes par an pour faire le tour
            de tes partenaires.
          </div>
        </div>
      </section>

      {/* MOT DE LA FIN */}
      <section>
        <p className="text-sm italic text-muted-foreground">
          Ton réseau de partenaires, c&apos;est un atout commercial — bien tenu à jour avec des notes
          qualité honnêtes et des délais réalistes, il te permet de répondre vite et juste à n&apos;importe
          quelle demande client, même celles qui sortent de ton périmètre interne.
        </p>
      </section>

    </div>
  )
}
