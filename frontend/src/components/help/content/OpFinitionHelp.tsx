export function OpFinitionHelp() {
  return (
    <div className="space-y-6 text-sm leading-relaxed">

      {/* INTRO MÉTIER */}
      <section>
        <p className="text-base">
          Cette page, c&apos;est <strong>ton catalogue d&apos;opérations de finition internes</strong>{" "}
          — toutes les opérations que tu réalises sur tes machines pour ajouter de la valeur à
          l&apos;étiquette : vernissage, laminage, dorure à chaud, découpe forme, etc. Chaque opération
          est référencée avec son tarif unitaire et son temps machine.
        </p>
        <p>
          C&apos;est différent de la <em>sous-traitance</em> (Partenaires ST) où tu fais réaliser
          ces opérations par un partenaire externe. Ici on parle de ce que tu fais{" "}
          <strong>sur ton propre matériel</strong>.
        </p>
      </section>

      {/* DISTINCTION IMPORTANTE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Important — 3 endroits qui parlent de finitions</h3>
        <p>Pour ne pas s&apos;y perdre, voici la distinction entre les 3 endroits où le mot
          « finitions » apparaît dans l&apos;app :</p>
        <div className="my-3 overflow-x-auto">
          <table className="text-xs border-collapse border border-gray-300 w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-300 px-2 py-1 text-left">Endroit</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Ce que c&apos;est</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Quand l&apos;utiliser</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">Op. finition (cette page)</td>
                <td className="border border-gray-300 px-2 py-1">Catalogue d&apos;opérations <strong>internes</strong> sur tes machines, avec coût et temps unitaires</td>
                <td className="border border-gray-300 px-2 py-1">Pour référencer ce que tu fais en interne avec leur tarif</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">Paramètres &gt; Poste 6</td>
                <td className="border border-gray-300 px-2 py-1">Prix fixe au m² des opérations de finition standard intégrées au moteur</td>
                <td className="border border-gray-300 px-2 py-1">Tarif global moyen utilisé dans le calcul P6 du devis</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">Calculer un devis &gt; Sous-traitance</td>
                <td className="border border-gray-300 px-2 py-1">Forfait <strong>externe</strong> par partenaire ST (pelliculage, dorure sous-traitée…)</td>
                <td className="border border-gray-300 px-2 py-1">Quand tu envoies une partie du job chez un partenaire</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* VUE D'ENSEMBLE LISTE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Vue d&apos;ensemble — la liste de tes opérations</h3>
        <img
          src="/help/op-finition/01-liste-operations-finition.png"
          alt="Liste des opérations de finition"
          className="rounded-md border shadow-sm my-3"
        />
        <p>La page liste tes opérations avec, pour chacune :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>#</strong> : ordre d&apos;ajout</li>
          <li><strong>Nom</strong> : libellé de l&apos;opération (ex: « Vernis UV brillant », « Laminage transparent BOPP »)</li>
          <li><strong>Unité</strong> : base de facturation — m² (surface), ml (mètre linéaire), ou unite (par étiquette)</li>
          <li><strong>Coût unit. (€)</strong> : tarif HT par unité de facturation</li>
          <li><strong>Temps (min/u)</strong> : durée machine consommée par unité (impact main d&apos;œuvre / occupation machine)</li>
          <li><strong>Statut</strong> : <em>Actif</em> = opération disponible dans le catalogue actif</li>
          <li><strong>Actions</strong> : crayon = éditer, poubelle = supprimer</li>
        </ul>
      </section>

      {/* LES 3 UNITÉS */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Bien choisir l&apos;unité de facturation</h3>
        <p>L&apos;unité dépend du type d&apos;opération que tu réalises :</p>
        <div className="my-3 overflow-x-auto">
          <table className="text-xs border-collapse border border-gray-300 w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-300 px-2 py-1 text-left">Unité</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Pour quel type d&apos;opération</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Exemples typiques</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">m² (m2)</td>
                <td className="border border-gray-300 px-2 py-1">Opérations qui couvrent toute la surface produite</td>
                <td className="border border-gray-300 px-2 py-1">Vernis UV, Laminage, Vernis sélectif, Vernis mat</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">ml (mètre linéaire)</td>
                <td className="border border-gray-300 px-2 py-1">Opérations facturées au mètre de bande défilante</td>
                <td className="border border-gray-300 px-2 py-1">Dorure à chaud, Marquage à froid, Embossage en bande</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1 font-semibold">unite (par étiquette)</td>
                <td className="border border-gray-300 px-2 py-1">Opérations facturées à l&apos;unité d&apos;étiquette produite</td>
                <td className="border border-gray-300 px-2 py-1">Découpe forme, Marquage à chaud localisé</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Choisir la bonne unité</strong> : pose-toi la question « comment je facture
          habituellement cette opération à mon client ? ». Si tu factures la dorure à 1,20 €/ml,
          mets <em>ml</em>. Si tu factures la découpe forme à 0,005 €/étiquette, mets <em>unite</em>.
          C&apos;est la cohérence avec ta facturation qui prime.
        </div>
      </section>

      {/* AJOUTER UNE OPÉRATION */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Ajouter une nouvelle opération</h3>
        <p>Clique <strong>+ Nouvelle opération</strong> en haut à droite. Le formulaire s&apos;ouvre :</p>
        <img
          src="/help/op-finition/02-formulaire-operation-finition.png"
          alt="Formulaire de création d'une opération de finition"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Voici chaque champ en détail :</p>

        <h4 className="font-semibold mt-4 mb-1">Nom <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Le libellé de l&apos;opération. Choisis un nom clair et reconnaissable en interne. Exemples :
          <em> « Vernis UV brillant »</em>, <em> « Laminage transparent BOPP »</em>,
          <em> « Dorure à chaud or »</em>. Évite les abréviations cryptiques (« VUVB ») qui te perdront
          quand tu auras 20+ opérations.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Unité de facturation <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Choisir parmi : <strong>m2</strong>, <strong>ml</strong> ou <strong>unite</strong> (voir
          le tableau juste au-dessus pour bien choisir). Une fois l&apos;opération créée et utilisée
          dans des devis, change l&apos;unité avec précaution — ça impacte les calculs.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Statut</h4>
        <p className="ml-2">
          <em>Actif</em> par défaut. Met à <em>inactif</em> si tu veux retirer cette opération du
          catalogue actif sans la supprimer (ex: opération saisonnière, ou indisponible
          temporairement). L&apos;historique reste intact.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Coût unitaire (€)</h4>
        <p className="ml-2">
          Le coût HT par unité de facturation. Format décimal : <em>0,45 pour 45 cents/m²</em>,
          <em> 1,20 pour 1,20 €/ml</em>, <em>0,005 pour 0,5 cent par étiquette</em>. Mets ton
          <strong>vrai coût de revient</strong> (matière consommable + amortissement outillage spécifique
          + énergie spécifique) — pas le tarif facturé client.
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Méthode pour estimer ton coût de revient</strong> : prends ta consommation
          annuelle (ex: vernis UV) + amortissement outillage spécifique sur la durée de vie + énergie,
          divise par les unités annuelles produites. Tu obtiens un coût unitaire réaliste.
        </div>

        <h4 className="font-semibold mt-4 mb-1">Temps machine (min/unité)</h4>
        <p className="ml-2">
          Le temps machine consommé par unité de facturation. Format décimal :{" "}
          <em>0,1 = 6 secondes/unité</em>, <em>0,15 = 9 secondes/unité</em>,
          <em> 0,3 = 18 secondes/unité</em>. Ce temps sera utilisé pour le calcul de l&apos;occupation
          machine et la main d&apos;œuvre opérateur supplémentaire liée à l&apos;opération.
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Si tu hésites sur le temps</strong> : laisse à 0 dans un premier temps.
          Tu pourras affiner après quelques jobs réels en chronométrant le temps réel passé.
          Mieux vaut 0 (qui n&apos;ajoute rien) qu&apos;un chiffre faux qui fausse tes devis.
        </div>

        <h4 className="font-semibold mt-4 mb-1">Commentaire (optionnel)</h4>
        <p className="ml-2">
          Note libre — utile pour rappeler une particularité : <em>« nécessite outillage spécifique
          réf. XYZ »</em>, <em>« uniquement compatible avec papier couché »</em>, <em>« min de
          commande 500 m² »</em>, etc.
        </p>

        <p className="mt-3">
          Quand tout est rempli, clique <strong>Créer</strong>. L&apos;opération apparaît dans la liste
          et devient référence dans ton catalogue de finitions internes.
        </p>
      </section>

      {/* MODIFIER OU SUPPRIMER */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Modifier ou supprimer une opération</h3>
        <p>Sur la liste, dans la colonne <em>Actions</em> :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>Crayon ✏️</strong> = éditer l&apos;opération. Pré-rempli avec les valeurs actuelles.</li>
          <li><strong>Poubelle 🗑️</strong> = supprimer définitivement. À utiliser avec précaution.</li>
        </ul>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Suppression vs Désactivation :</strong> si l&apos;opération a déjà été référencée
          dans des devis sauvegardés, mieux vaut la passer en <em>inactif</em> que la supprimer.
          Tu masques l&apos;opération sans casser l&apos;historique.
        </div>
      </section>

      {/* PIÈGES CLASSIQUES */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Les 3 pièges classiques</h3>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 space-y-3">
          <div>
            <strong>1. Confondre Op. finition (interne) et Sous-traitance (externe).</strong> Cette
            page = ce que tu fais sur tes propres machines. Si tu envoies à un partenaire (pelliculage
            externe, dorure sous-traitée), c&apos;est dans <em>Calculer un devis &gt; Sous-traitance</em>{" "}
            avec un montant forfaitaire par partenaire.
          </div>
          <div>
            <strong>2. Saisir un coût client au lieu d&apos;un coût de revient.</strong> Le champ
            <em> Coût unitaire</em> doit refléter ce que <strong>te coûte</strong> l&apos;opération —
            pas le prix que tu factures à ton client. La marge est ajoutée plus loin par le moteur
            (au niveau du devis global).
          </div>
          <div>
            <strong>3. Mettre un Temps machine approximatif faux.</strong> Si tu n&apos;as pas mesuré
            précisément, mets 0 plutôt qu&apos;un chiffre inventé. 0 est plus honnête : ça veut dire
            « je n&apos;ajoute pas de temps spécifique ». Un chiffre faux fausse tes devis.
          </div>
        </div>
      </section>

      {/* MOT DE LA FIN */}
      <section>
        <p className="text-sm italic text-muted-foreground">
          Ce catalogue, c&apos;est ta liste des « plus-values » que tu peux apporter à une étiquette.
          Bien tenu à jour avec les vrais coûts, il te permet de chiffrer précisément quand un client
          demande du vernis sélectif, de la dorure ou un laminage particulier — sans t&apos;y prendre
          au feeling.
        </p>
      </section>

    </div>
  )
}
