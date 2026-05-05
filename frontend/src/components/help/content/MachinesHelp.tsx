export function MachinesHelp() {
  return (
    <div className="space-y-6 text-sm leading-relaxed">

      {/* ─────────────────────────────────────────────
          INTRO MÉTIER
       ────────────────────────────────────────────── */}
      <section>
        <p className="text-base">
          Cette page, c&apos;est <strong>ton parc machines</strong> — presses flexo et machines de
          finition (roulage, découpe, etc.). Chaque machine que tu configures ici devient sélectionnable
          dans le menu de <em>Calculer un devis</em>, et ses paramètres alimentent le moteur de coût
          (vitesse de roulage, coût horaire, nb couleurs disponibles).
        </p>
        <p>
          Comme pour les Paramètres, tu configures ce parc une fois bien à fond au démarrage avec moi
          en visio, et tu n&apos;y reviens qu&apos;après un investissement (nouvelle machine, mise à
          niveau d&apos;une presse), ou pour ajuster un coût horaire qui a évolué.
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          VUE D'ENSEMBLE LISTE
       ────────────────────────────────────────────── */}
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
          <li><strong>Nom</strong> : ton libellé interne (ex: « Mark Andy P5 », « Daco D250 ligne finition »)</li>
          <li><strong>Statut</strong> : <em>Actif</em> = visible dans Calculer un devis ; sinon masquée mais préservée dans l&apos;historique</li>
          <li><strong>Nb couleurs</strong> : nombre de groupes d&apos;impression (— pour les machines de finition)</li>
          <li><strong>Vitesse (m/min)</strong> : la vitesse moyenne réaliste utilisée par le moteur</li>
          <li><strong>Coût horaire (€)</strong> : ton coût horaire chargé pour cette machine</li>
          <li><strong>Actions</strong> : crayon = éditer, poubelle = supprimer</li>
        </ul>
        <p>
          La case <em>Afficher les machines inactives</em> en haut te permet de retrouver les machines
          désactivées (par exemple une vieille presse vendue mais que tu veux garder en historique).
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          AJOUTER UNE MACHINE
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Ajouter une nouvelle machine</h3>
        <p>Clique <strong>+ Nouvelle machine</strong> en haut à droite. Le formulaire s&apos;ouvre :</p>
        <img
          src="/help/machines/02-formulaire-machine.png"
          alt="Formulaire de création d'une machine"
          className="rounded-md border shadow-sm my-3"
        />
        <p>Voici chaque champ en détail :</p>

        <h4 className="font-semibold mt-4 mb-1">Nom <span className="text-red-500">*</span> (obligatoire)</h4>
        <p className="ml-2">
          Un libellé court et reconnaissable. Mets quelque chose qui te parle au quotidien, pas juste
          le modèle constructeur. Exemples : <em>« Mark Andy P5 - presse principale »</em>,
          <em> « OMET XFlex - 8 couleurs »</em>, <em>« Daco D250 ligne finition »</em>.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Laize max (mm)</h4>
        <p className="ml-2">
          La <strong>laize physique de la presse</strong> (largeur maxi de la bande qu&apos;elle peut
          accepter). À ne pas confondre avec la <em>laize utile</em> que tu saisis dans Calculer un
          devis (= la laize de ta bobine effective, toujours plus petite). Pour une Mark Andy P5
          c&apos;est typiquement 330 mm, pour une OMET 13&quot; c&apos;est 330 mm aussi.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Vitesse max (m/min) — LE point critique</h4>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 my-3">
          <p className="font-semibold mb-2">⚠️ Piège classique — lis bien ce qui suit</p>
          <p className="mb-2">
            Malgré le label « Vitesse max », ce n&apos;est <strong>PAS la vitesse max constructeur</strong>
            (catalogue) qu&apos;il faut mettre. C&apos;est ta <strong>vitesse moyenne effective</strong> de
            roulage — celle que tu tiens vraiment en production sur un job complet.
          </p>
          <p className="mb-2">
            <strong>Pourquoi le constructeur affiche 250-300 m/min ?</strong> Parce qu&apos;il teste
            dans des conditions idéales : sécheurs neufs à 100 %, plaque de découpe parfaite, papier
            avec laize très large, formes de cliché simples, zéro changement de bobine.
          </p>
          <p className="mb-2"><strong>La réalité dans ton atelier</strong> :</p>
          <ul className="list-disc pl-6 space-y-1 mb-2">
            <li><strong>Sécheurs UV usés à 50-60 %</strong> (tu ne changes pas les lampes tout le temps, c&apos;est cher) → tu dois ralentir pour bien sécher</li>
            <li><strong>Formes de plaque souvent difficiles à écheniller</strong> → tu ne peux pas pousser</li>
            <li><strong>Laize papier souvent juste</strong> par rapport à la machine → contraintes de tension qui limitent la vitesse</li>
            <li><strong>Changements de référence non comptés</strong> en cours de job → ça grignote la vitesse moyenne</li>
            <li><strong>Casses papier/film, changements bobine mère/fille, ajustements teinte</strong> → tous ces arrêts comptent dans la vitesse effective</li>
          </ul>
          <p className="mb-2">
            <strong>Ordre de grandeur réaliste</strong> : 70 à 100 m/min pour la plupart des Mark Andy /
            OMET en production normale (oui, beaucoup moins que les fiches constructeur).
          </p>
          <p className="mb-2">
            Si tu mets la vitesse max catalogue (250 au lieu de 80 m/min réelle), tes devis sortent
            <strong> 30 à 50 % trop bas</strong> sur le poste P5 (Roulage) — tu perds de l&apos;argent
            à chaque tirage.
          </p>
        </div>

        <p className="mt-2"><strong>Méthode pratique pour calculer ta vraie vitesse</strong> :</p>
        <ol className="list-decimal pl-6 my-2 space-y-1">
          <li>Prends 3-4 jobs typiques récents que tu fais sur cette machine</li>
          <li>Pour chacun, divise le tirage total (m linéaires) par la durée totale de roulage (heures × 60 min)</li>
          <li>Fais la moyenne des 3-4 résultats</li>
          <li>Tu obtiens ta vraie vitesse moyenne représentative</li>
        </ol>

        <h4 className="font-semibold mt-4 mb-1">Nb couleurs</h4>
        <p className="ml-2">
          Le nombre de groupes d&apos;impression de la machine (typiquement 6, 8 ou 10 sur les
          presses flexo). Pour une machine de finition pure (sans impression, type laminoir ou ligne
          de découpe), laisse <em>vide</em> ou mets 0.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Coût horaire (€)</h4>
        <p className="ml-2">
          Ton coût horaire <strong>chargé</strong> pour cette machine — pas le tarif facturé client.
          C&apos;est ce que la machine te coûte réellement par heure d&apos;utilisation : amortissement +
          électricité + maintenance + part de loyer atelier + main d&apos;œuvre opérateur si tu veux
          l&apos;intégrer ici (sinon le P7 main d&apos;œuvre s&apos;ajoute en plus).
        </p>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3 text-sm">
          <strong>💡 Astuce calcul rapide :</strong> coût annuel total de la machine (amortissement +
          maintenance + énergie) divisé par les heures de production annuelles. Ajoute la part atelier
          (loyer, charges fixes) que tu attribues à cette machine. Ne mélange pas avec P7 (main
          d&apos;œuvre) qui se règle séparément dans Paramètres.
        </div>

        <h4 className="font-semibold mt-4 mb-1">Actif (case à cocher)</h4>
        <p className="ml-2">
          Cochée par défaut. <strong>Décoche-la si tu veux masquer cette machine</strong> dans le menu
          de Calculer un devis sans la supprimer (ex: machine vendue, machine en panne longue, machine
          de remplacement temporaire). L&apos;historique des devis qui l&apos;ont utilisée reste intact.
        </p>

        <h4 className="font-semibold mt-4 mb-1">Commentaire (optionnel)</h4>
        <p className="ml-2">
          Note libre pour toi-même. Utile pour rappeler une particularité : <em>« sécheurs UV à
          remplacer en juin 2026 »</em>, <em>« presse achetée d&apos;occasion en 2018 »</em>, etc.
        </p>

        <p className="mt-3">
          Quand tout est rempli, clique <strong>Créer</strong> en bas à droite. La machine apparaît
          dans la liste et devient sélectionnable dans Calculer un devis (si Actif coché).
        </p>
      </section>

      {/* ─────────────────────────────────────────────
          MODIFIER OU SUPPRIMER
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">Modifier ou supprimer une machine</h3>
        <p>Sur la liste, dans la colonne <em>Actions</em> :</p>
        <ul className="list-disc pl-6 my-2 space-y-1">
          <li>
            <strong>Crayon ✏️</strong> = éditer la machine. Le formulaire de modification est identique
            à celui de création.
          </li>
          <li>
            <strong>Poubelle 🗑️</strong> = supprimer définitivement. <em>À utiliser avec précaution.</em>
          </li>
        </ul>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 my-3 text-sm">
          <strong>⚠️ Suppression vs Désactivation :</strong> avant de cliquer la poubelle, demande-toi si
          la machine a déjà servi sur des devis sauvegardés. Si oui, <strong>ne supprime pas</strong>,
          décoche juste la case <em>Actif</em>. Tu masques la machine sans casser l&apos;historique.
          La suppression est à réserver aux machines créées par erreur ou jamais utilisées.
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          PIÈGES CLASSIQUES
       ────────────────────────────────────────────── */}
      <section>
        <h3 className="text-lg font-semibold mb-2">⚠️ Les 4 pièges classiques</h3>
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 space-y-3">
          <div>
            <strong>1. Saisir la vitesse max constructeur (le piège n°1).</strong> Met ta vitesse
            moyenne effective réelle de roulage (~70-100 m/min en flexo standard), pas les 250 m/min
            de la fiche technique. Sinon devis 30-50 % trop bas.
          </div>
          <div>
            <strong>2. Coût horaire pas chargé.</strong> Ne mets pas juste l&apos;amortissement —
            inclus l&apos;électricité, la maintenance, l&apos;assurance, la part atelier. Si tu mets
            un coût trop bas, tes devis ne couvrent pas tes vrais coûts.
          </div>
          <div>
            <strong>3. Supprimer une machine au lieu de la désactiver.</strong> Si elle a servi sur des
            devis passés, la suppression peut casser l&apos;historique. Décoche <em>Actif</em> à la place.
          </div>
          <div>
            <strong>4. Confondre Laize max machine et laize utile bobine.</strong> Laize max = capacité
            physique de la presse (330 mm typique). Laize utile = ce que tu rentres dans Calculer un
            devis (= laize réelle de ta bobine, toujours plus petite, ex: 220 mm).
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────
          MOT DE LA FIN
       ────────────────────────────────────────────── */}
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
