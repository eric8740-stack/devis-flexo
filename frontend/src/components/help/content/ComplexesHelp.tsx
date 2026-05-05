export function ComplexesHelp() {
  return (
    <div className="space-y-6 text-sm leading-relaxed">

      {/* INTRO MÉTIER */}
      <section>
        <p className="text-base">
          Cette page, c&apos;est <strong>ton catalogue matières</strong> — tous les complexes adhésifs
          (papiers, films, thermiques) que tu utilises pour fabriquer tes étiquettes. Chaque complexe
          configuré ici devient sélectionnable dans le menu <em>Calculer un devis</em>, et son
          <strong> prix au m²</strong> alimente directement le calcul du poste P1 (Matière).
        </p>
        <p>
          C&apos;est typiquement la 1ʳᵉ liste à enrichir au démarrage, parce que sans complexe configuré,
          impossible de faire un devis. On la met en place ensemble en visio.
        </p>
      </section>

      {/* VUE D'ENSEMBLE LISTE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Vue d&apos;ensemble — la liste de tes complexes</h3>
        <img
          src="/help/complexes/01-liste-complexes.png"
          alt="Liste des complexes adhésifs"
          className="rounded-md border shadow-sm my-3"
        />
        <p>La page liste tes complexes avec, pour chacun :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>#</strong> : ordre d&apos;ajout</li>
          <li><strong>Référence</strong> : ton code interne, généralement structuré (ex: <code>BOPP_BLANC_50</code> = matière_finition_grammage/épaisseur)</li>
          <li><strong>Famille</strong> : catégorie technique du complexe (voir détail ci-dessous)</li>
          <li><strong>Grammage</strong> : poids matière en g/m² — <em>vide pour les films</em></li>
          <li><strong>Prix €/m²</strong> : ton tarif d&apos;achat (HT) au m²</li>
          <li><strong>Fournisseur (ID)</strong> : lien vers ton fournisseur principal de cette matière</li>
          <li><strong>Statut</strong> : <em>Actif</em> = sélectionnable dans Calculer un devis</li>
          <li><strong>Actions</strong> : crayon = éditer, poubelle = supprimer</li>
        </ul>
        <p>
          La case <em>Afficher les complexes inactifs</em> en haut te permet de retrouver les matières
          que tu n&apos;utilises plus mais que tu veux garder en historique.
        </p>
      </section>

      {/* LES 6 FAMILLES */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Les 6 familles disponibles</h3>
        <p>L&apos;app regroupe tes matières en 6 familles techniques :</p>
        <div className="my-3 overflow-x-auto">
          <table className="text-xs border-collapse border border-gray-300 w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-300 px-2 py-1 text-left">Famille</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Type</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Grammage ?</th>
                <th className="border border-gray-300 px-2 py-1 text-left">Usages typiques</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 px-2 py-1"><code>papier_couche</code></td>
                <td className="border border-gray-300 px-2 py-1">Papier</td>
                <td className="border border-gray-300 px-2 py-1">✅ Oui (60-100 g/m²)</td>
                <td className="border border-gray-300 px-2 py-1">Étiquettes alimentaires, cosmétiques</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1"><code>thermique</code></td>
                <td className="border border-gray-300 px-2 py-1">Papier thermique</td>
                <td className="border border-gray-300 px-2 py-1">✅ Oui (60-90 g/m²)</td>
                <td className="border border-gray-300 px-2 py-1">Logistique, code-barres, balances</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1"><code>bopp</code></td>
                <td className="border border-gray-300 px-2 py-1">Film polypropylène biorienté</td>
                <td className="border border-gray-300 px-2 py-1">⚠️ À saisir manuellement (voir piège)</td>
                <td className="border border-gray-300 px-2 py-1">Étiquettes humides, agroalim, beauté</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1"><code>pp</code></td>
                <td className="border border-gray-300 px-2 py-1">Film polypropylène</td>
                <td className="border border-gray-300 px-2 py-1">⚠️ À saisir manuellement</td>
                <td className="border border-gray-300 px-2 py-1">Étiquettes durables, transparentes</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1"><code>pe</code></td>
                <td className="border border-gray-300 px-2 py-1">Film polyéthylène</td>
                <td className="border border-gray-300 px-2 py-1">⚠️ À saisir manuellement</td>
                <td className="border border-gray-300 px-2 py-1">Bidons, bouteilles, contenus souples</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-2 py-1"><code>pvc_vinyle</code></td>
                <td className="border border-gray-300 px-2 py-1">Film PVC / vinyle</td>
                <td className="border border-gray-300 px-2 py-1">⚠️ À saisir manuellement</td>
                <td className="border border-gray-300 px-2 py-1">Industrie, marquage longue durée</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* AJOUTER UN COMPLEXE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Ajouter un nouveau complexe</h3>
        <p>Clique <strong>+ Nouveau complexe</strong> en haut à droite. Le formulaire s&apos;ouvre :</p>
        <img
          src="/help/complexes/02-formulaire-complexe.png"
          alt="Formulaire de création d'un complexe"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Voici chaque champ en détail :</p>

        <h4 className="font-semibold mt-4 mb-1">Référence <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Ton code interne pour identifier ce complexe. Le mieux est d&apos;adopter une nomenclature
          structurée — exemples du seed : <code>BOPP_BLANC_50</code>, <code>VELIN_STANDARD_80</code>,
          <code> THERMIQUE_TOPCOAT_90</code>. Format conseillé : <em>MATIÈRE_FINITION_GRAMMAGE</em>.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Famille <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Choisir parmi les 6 familles du dropdown. La famille sert à organiser ton catalogue
          (filtres futurs, statistiques par type), mais <strong>n&apos;impacte pas le calcul</strong>
          du devis directement — c&apos;est le prix au m² et le grammage qui pilotent P1.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Face / matière (optionnel)</h4>
        <p className="ml-2">
          Description plus détaillée de la matière — ex: <em>« Papier vélin standard 80g blanc »</em>,
          <em> « BOPP blanc adhésif permanent acrylique »</em>. Utile pour toi pour t&apos;y retrouver
          quand tu as 50+ complexes.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Grammage (g/m²) — LE point critique 🔴</h4>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 my-3">
          <p className="font-semibold mb-2">⚠️ Piège n°1 — lis bien ce qui suit</p>
          <p className="mb-2">
            Le champ Grammage est <strong>marqué optionnel dans le formulaire</strong>, mais{" "}
            <strong>obligatoire pour le calcul du devis</strong> dès que tu utilises ce complexe.
          </p>
          <p className="mb-2">
            <strong>Pourquoi ?</strong> Le moteur P1 (Matière) calcule le prix au kg via la formule
            <code> prix_m2 × 1000 / grammage</code>. Sans grammage, division par zéro impossible →
            l&apos;app affiche une <strong>erreur 422</strong> au moment du calcul.
          </p>
          <p className="mb-2"><strong>Conséquence visible</strong> : tous les complexes BOPP, PP, PE,
          PVC du seed initial ont leur grammage à <em>—</em> (vide). Si tu lances un devis avec un de ces
          complexes <em>sans avoir renseigné de grammage avant</em>, tu auras l&apos;erreur 422.</p>
          <p className="mb-2"><strong>Solution pour les films</strong> : convertir l&apos;épaisseur
          (microns) en grammage approximatif :</p>
          <ul className="list-disc pl-6 space-y-1 mb-2">
            <li>BOPP 50 µm → grammage ≈ <strong>45 g/m²</strong> (densité 0,91 g/cm³)</li>
            <li>BOPP 70 µm → grammage ≈ <strong>64 g/m²</strong></li>
            <li>PP 60 µm → grammage ≈ <strong>54 g/m²</strong></li>
            <li>PE 70 µm → grammage ≈ <strong>64 g/m²</strong> (densité 0,92)</li>
            <li>PVC 80 µm → grammage ≈ <strong>112 g/m²</strong> (densité 1,40, le plus dense)</li>
          </ul>
          <p className="mb-2">
            <strong>Solution pour les papiers et thermiques</strong> : c&apos;est facile, le grammage
            est marqué sur la fiche technique du papier (ex: 80 g/m², 90 g/m²).
          </p>
        </div>

        <h4 className="font-semibold mt-4 mb-1">Type d&apos;adhésif (optionnel)</h4>
        <p className="ml-2">
          Le type de colle au dos du complexe : <em>« permanent acrylique »</em>,
          <em> « repositionnable »</em>, <em>« congélation »</em>, etc. Champ libre, sert à toi pour
          t&apos;y retrouver. N&apos;impacte pas le calcul.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Prix au m² (€) <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Ton tarif d&apos;achat HT au m² (le prix que tu paies à ton fournisseur). C&apos;est{" "}
          <strong>le paramètre principal qui alimente P1</strong> dans le calcul du devis. Format
          décimal — ex: 0,80 pour 80 cents le m², 1,75 pour 1,75 € le m². Plage typique flexo :
          0,50 à 5,00 €/m².
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Astuce :</strong> demande à ton fournisseur le prix HT au m² spécifiquement
          (et non au mètre linéaire qui dépend de la laize). Ça simplifie le suivi et évite les conversions.
        </div>

        <h4 className="font-semibold mt-4 mb-1">ID Fournisseur (FK) (optionnel)</h4>
        <p className="ml-2">
          Lien vers le fournisseur principal de ce complexe (l&apos;ID que tu trouves dans la page
          <em> Fournisseurs</em>). Utile pour traçabilité, et si tu veux automatiser des relances de stock
          plus tard.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Actif (case à cocher)</h4>
        <p className="ml-2">
          Cochée par défaut. <strong>Décoche-la</strong> si tu veux masquer cette matière sans la
          supprimer (ex: matière retirée du catalogue fournisseur, plus dispo en stock).
          L&apos;historique des devis qui l&apos;ont utilisée reste intact.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Commentaire (optionnel)</h4>
        <p className="ml-2">
          Note libre. Utile pour : <em>« stock = 5 bobines »</em>,
          <em> « commande mini 500 m² »</em>, <em>« remplaçant temporaire de BOPP_BLANC_50 »</em>, etc.
        </p>

        <p className="mt-3">
          Quand tout est rempli, clique <strong>Créer</strong> en bas. Le complexe apparaît dans la liste
          et devient sélectionnable dans Calculer un devis (si Actif coché).
        </p>
      </section>

      {/* MODIFIER OU SUPPRIMER */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Modifier ou supprimer un complexe</h3>
        <p>Sur la liste, dans la colonne <em>Actions</em> :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>Crayon ✏️</strong> = éditer le complexe. Pré-rempli avec les valeurs actuelles.</li>
          <li><strong>Poubelle 🗑️</strong> = supprimer définitivement. À utiliser avec précaution.</li>
        </ul>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Suppression vs Désactivation :</strong> si le complexe a déjà servi sur des
          devis sauvegardés, <strong>ne supprime pas</strong>, décoche juste <em>Actif</em>.
          La suppression est à réserver aux complexes créés par erreur ou jamais utilisés.
        </div>
      </section>

      {/* PIÈGES CLASSIQUES */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Les 4 pièges classiques</h3>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 space-y-3">
          <div>
            <strong>1. Grammage vide sur un film (BOPP/PP/PE/PVC).</strong> Le piège n°1.
            Convertis l&apos;épaisseur en microns en grammage approximatif (BOPP 50 µm ≈ 45 g/m²).
            Sinon erreur 422 au calcul du devis.
          </div>
          <div>
            <strong>2. Prix au m² approximé.</strong> Le P1 représente souvent 30-50 % du coût total
            d&apos;un devis. Un écart de 10 % sur ton prix au m² impacte directement ta marge.
            Vérifie tes derniers bons de livraison fournisseur pour avoir les vrais prix.
          </div>
          <div>
            <strong>3. Référence pas standardisée.</strong> Si tu mélanges les nomenclatures
            (<code>BOPP_BLANC_50</code> vs <code>bopp blanc 50µ</code> vs <code>BOPP-W-50</code>),
            tu te perds vite avec 30+ complexes. Choisis une convention et tiens-la.
          </div>
          <div>
            <strong>4. Supprimer un complexe au lieu de le désactiver.</strong> Si tu décides de ne
            plus utiliser un BOPP, décoche <em>Actif</em>. Tu masques la matière sans casser
            l&apos;historique des devis qui l&apos;ont utilisée.
          </div>
        </div>
      </section>

      {/* MOT DE LA FIN */}
      <section>
        <p className="text-sm italic text-muted-foreground">
          Ce catalogue, c&apos;est ton patrimoine matières — bien tenu à jour, il te fait gagner un
          temps fou sur tes devis et te garantit que les prix reflètent vraiment tes coûts d&apos;achat.
          On le construit ensemble au démarrage, et tu l&apos;ajustes au fil des évolutions
          tarifaires de tes fournisseurs.
        </p>
      </section>

    </div>
  )
}
