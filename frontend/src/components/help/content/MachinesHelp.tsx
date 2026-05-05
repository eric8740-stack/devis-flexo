export function MachinesHelp() {
  return (
    <div className="space-y-6 text-sm leading-relaxed">

      {/* INTRO MÉTIER */}
      <section>
        <p className="text-base">
          Cette page, c&apos;est <strong>ton parc machines</strong> — presses flexo et machines de
          finition (roulage, découpe, etc.). Chaque machine que tu configures ici devient sélectionnable
          dans le menu de <em>Calculer un devis</em>, et ses paramètres alimentent le moteur de coût
          (vitesse moyenne réaliste, durée de calage, coût horaire, nb couleurs).
        </p>
        <p>
          Tu configures ce parc une fois bien à fond au démarrage avec moi en visio, et tu n&apos;y
          reviens qu&apos;après un investissement (nouvelle machine), une mise à niveau, ou pour ajuster
          un coût horaire qui a évolué.
        </p>
      </section>

      {/* VUE D'ENSEMBLE LISTE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Vue d&apos;ensemble — la liste de tes machines</h3>
        <img
          src="/help/machines/01-liste-machines.png"
          alt="Liste des machines"
          className="rounded-md border shadow-sm my-3"
        />
        <p>La page liste tes machines avec, pour chacune :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>#</strong> : ordre d&apos;ajout</li>
          <li><strong>Nom</strong> : ton libellé interne</li>
          <li><strong>Statut</strong> : <em>Actif</em> = visible dans Calculer un devis</li>
          <li><strong>Nb couleurs</strong> : nombre de groupes d&apos;impression</li>
          <li><strong>Vitesse (m/min)</strong> : la <strong>vitesse moyenne réaliste</strong> utilisée par le moteur (pas la vitesse catalogue)</li>
          <li><strong>Coût horaire (€)</strong> : ton coût horaire chargé pour cette machine</li>
          <li><strong>Actions</strong> : crayon = éditer, poubelle = supprimer</li>
        </ul>
      </section>

      {/* AJOUTER UNE MACHINE */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Ajouter une nouvelle machine</h3>
        <p>Clique <strong>+ Nouvelle machine</strong> en haut à droite. Le formulaire s&apos;ouvre :</p>
        <img
          src="/help/machines/02-formulaire-machine.png"
          alt="Formulaire de création d'une machine"
          className="rounded-md border shadow-sm my-3"
        />
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Note sur la capture :</strong> la version actuellement en prod a évolué — le formulaire
          inclut désormais aussi des champs <em>Vitesse moyenne réaliste</em>, <em>Durée calage</em> et
          <em> Laize max</em> qui sont décrits ci-dessous. Capture mise à jour bientôt.
        </div>
        <p>Voici chaque champ en détail :</p>

        <h4 className="font-semibold mt-4 mb-1">Nom <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Un libellé court et reconnaissable. Mets quelque chose qui te parle au quotidien.
          Exemples : <em>« Mark Andy P5 - presse principale »</em>, <em> « OMET XFlex - 8 couleurs »</em>.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Laize max (mm) <span className="text-red-500">*</span></h4>
        <p className="ml-2">
          La <strong>laize physique de la presse</strong> (largeur maxi de bande qu&apos;elle accepte).
          À ne pas confondre avec la <em>laize utile</em> (= laize de ta bobine, toujours plus petite).
          Pour une Mark Andy P5 : 330 mm typiquement. Pour une OMET 13&quot; : 330 mm aussi.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Vitesse catalogue (m/min, indicative)</h4>
        <p className="ml-2">
          La vitesse maximale annoncée par le constructeur sur sa fiche technique. Information utile
          pour ta documentation interne, mais <strong>n&apos;impacte pas le calcul</strong> du devis.
          C&apos;est le champ <em>Vitesse moyenne réaliste</em> juste en-dessous qui pilote le moteur.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Vitesse moyenne réaliste (m/min) <span className="text-red-500">*</span> — LE point critique</h4>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 my-3">
          <p className="font-semibold mb-2">⚠️ Le champ qui change tout — lis bien</p>
          <p className="mb-2">
            C&apos;est ta <strong>vitesse moyenne effective</strong> de roulage — celle que tu tiens
            vraiment en production sur un job complet, en intégrant tous les arrêts.
          </p>
          <p className="mb-2">
            <strong>Pourquoi le constructeur affiche 250-300 m/min ?</strong> Parce qu&apos;il teste
            dans des conditions idéales : sécheurs neufs à 100 %, plaque de découpe parfaite, papier
            avec laize très large, formes de cliché simples, zéro changement de bobine.
          </p>
          <p className="mb-2"><strong>La réalité dans ton atelier</strong> :</p>
          <ul className="list-disc pl-6 space-y-1 mb-2">
            <li><strong>Sécheurs UV usés à 50-60 %</strong> (tu ne changes pas les lampes tout le temps) → tu dois ralentir</li>
            <li><strong>Formes de plaque souvent difficiles à écheniller</strong> → tu ne peux pas pousser</li>
            <li><strong>Laize papier souvent juste</strong> par rapport à la machine → contraintes de tension</li>
            <li><strong>Changements de référence non comptés</strong> en cours de job → ça grignote la moyenne</li>
            <li><strong>Casses papier/film, changements bobine mère/fille, ajustements teinte</strong> → tous comptent</li>
          </ul>
          <p className="mb-2">
            <strong>Ordre de grandeur réaliste</strong> : 70 à 100 m/min pour la plupart des Mark Andy /
            OMET en production normale (oui, beaucoup moins que les fiches constructeur).
          </p>
          <p className="mb-2">
            Si tu mets 250 au lieu de 80 m/min, tes devis sortent <strong>30 à 50 % trop bas</strong>
            sur P5 (Roulage) et P7 (MO opérateur) — tu perds de l&apos;argent à chaque tirage.
          </p>
        </div>

        <p className="mt-2"><strong>Méthode pratique pour calculer ta vraie vitesse</strong> :</p>
        <ol className="list-decimal pl-6 my-2 space-y-1">
          <li>Prends 3-4 jobs typiques récents que tu fais sur cette machine</li>
          <li>Pour chacun, divise le tirage total (m linéaires) par la durée totale de roulage (heures × 60 min)</li>
          <li>Fais la moyenne des 3-4 résultats</li>
          <li>Tu obtiens ta vraie vitesse moyenne représentative</li>
        </ol>

        <h4 className="font-semibold mt-4 mb-1">Durée calage (h) <span className="text-red-500">*</span></h4>
        <p className="ml-2">
          La durée typique de la mise en route + calage avant que tu commences à produire en série.
          Format décimal : <em>1.00 = 1h, 0.50 = 30 min, 1.50 = 1h30</em>. C&apos;est utilisé pour
          calculer le coût main d&apos;œuvre opérateur (P7) lié au calage.
        </p>
        <p className="ml-2 mt-1">
          Valeur typique flexo : entre 0.50 (job répétitif simple) et 2.00 (premier passage ou
          changement complet de configuration).
        </p>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Limitation actuelle à connaître :</strong> la durée de calage saisie ici est un{" "}
          <strong>forfait fixe par machine</strong>, indépendant du nombre de couleurs du job en cours.
          Concrètement : que tu fasses un job 1 couleur ou un job 8 couleurs UV multi-étapes, l&apos;app
          facture la même durée de calage (celle saisie ici).
          <p className="mt-2">
            <strong>Conseil pratique</strong> : saisis une <em>durée moyenne représentative</em> de tes
            jobs typiques sur cette machine. Exemples :
          </p>
          <ul className="list-disc pl-6 mt-1 space-y-0.5">
            <li>Tu fais surtout des jobs 1-2 couleurs simples → mets <strong>0.50</strong> (30 min)</li>
            <li>Tu fais surtout des jobs 4-6 couleurs CMJN → mets <strong>1.00</strong> (1h)</li>
            <li>Tu fais surtout des jobs 8 couleurs UV multi-étapes → mets <strong>1.50</strong> (1h30)</li>
          </ul>
          <p className="mt-2">
            <em>À venir en Phase 2</em> : durée calage variable selon le nombre de couleurs du job
            (rejoindra la refonte du moteur temps de production).
          </p>
        </div>

        <h4 className="font-semibold mt-4 mb-1">Nb couleurs</h4>
        <p className="ml-2">
          Le nombre de groupes d&apos;impression de la machine (typiquement 6, 8 ou 10 sur les presses flexo).
          Pour une machine de finition pure (laminoir ou ligne de découpe), laisse vide ou mets 0.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Coût horaire (€)</h4>
        <p className="ml-2">
          Ton coût horaire <strong>chargé</strong> pour cette machine — pas le tarif facturé client.
          C&apos;est ce que la machine te coûte réellement par heure : amortissement + électricité +
          maintenance + part atelier.
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Astuce calcul rapide :</strong> coût annuel total (amortissement + maintenance +
          énergie) ÷ heures de production annuelles, + part atelier attribuée à cette machine. Ne mélange
          pas avec P7 (main d&apos;œuvre) qui se règle séparément dans <em>Paramètres</em>.
        </div>

        <h4 className="font-semibold mt-4 mb-1">Actif (case à cocher)</h4>
        <p className="ml-2">
          Cochée par défaut. <strong>Décoche-la pour masquer cette machine</strong> sans la supprimer
          (machine vendue, en panne longue, etc.). L&apos;historique des devis qui l&apos;ont utilisée
          reste intact.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Commentaire (optionnel)</h4>
        <p className="ml-2">
          Note libre. Utile pour rappeler une particularité : <em>« sécheurs UV à remplacer mi-2026 »</em>,
          <em> « presse achetée d&apos;occasion en 2018 »</em>, etc.
        </p>

        <p className="mt-3">
          Quand tout est rempli, clique <strong>Créer</strong> en bas. La machine apparaît dans la liste
          et devient sélectionnable dans Calculer un devis (si Actif coché).
        </p>
      </section>

      {/* MODIFIER OU SUPPRIMER */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Modifier ou supprimer une machine</h3>
        <p>Sur la liste, dans la colonne <em>Actions</em> :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li><strong>Crayon ✏️</strong> = éditer la machine. Le formulaire est identique à la création, pré-rempli avec tes valeurs.</li>
          <li><strong>Poubelle 🗑️</strong> = supprimer définitivement. À utiliser avec précaution.</li>
        </ul>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Suppression vs Désactivation :</strong> avant de cliquer la poubelle, demande-toi
          si la machine a déjà servi sur des devis sauvegardés. Si oui, <strong>ne supprime pas</strong>,
          décoche juste la case <em>Actif</em>. Tu masques la machine sans casser l&apos;historique.
        </div>
      </section>

      {/* PIÈGES CLASSIQUES */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Les 4 pièges classiques</h3>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 space-y-3">
          <div>
            <strong>1. Confondre Vitesse catalogue et Vitesse moyenne réaliste.</strong>{" "}
            La vitesse catalogue (250-300 m/min) est juste indicative et n&apos;impacte pas le calcul.
            C&apos;est la <em>Vitesse moyenne réaliste</em> (~70-100 m/min en flexo standard) qui pilote
            P5 et P7. Si tu mets la valeur catalogue dans le mauvais champ, tu sors des devis 30-50 %
            trop bas.
          </div>
          <div>
            <strong>2. Coût horaire pas chargé.</strong> Ne mets pas juste l&apos;amortissement —
            inclus l&apos;électricité, la maintenance, l&apos;assurance, la part atelier.
          </div>
          <div>
            <strong>3. Supprimer une machine au lieu de la désactiver.</strong> Si elle a servi sur
            des devis passés, la suppression peut casser l&apos;historique. Décoche <em>Actif</em>.
          </div>
          <div>
            <strong>4. Confondre Laize max machine et laize utile bobine.</strong> Laize max =
            capacité physique de la presse (330 mm typique). Laize utile = ce que tu rentres dans
            Calculer un devis (= laize réelle de ta bobine, ex: 220 mm).
          </div>
        </div>
      </section>

      {/* MOT DE LA FIN */}
      <section>
        <p className="text-sm italic text-muted-foreground">
          Ce qui change tout sur cette page, c&apos;est de saisir des <strong>vitesses et coûts
          réalistes</strong>, pas idéalisés. C&apos;est la base pour avoir des devis qui reflètent
          ta vraie production — et donc une vraie marge à la fin du mois.
        </p>
      </section>

    </div>
  )
}
