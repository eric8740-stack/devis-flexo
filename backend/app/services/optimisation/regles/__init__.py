"""Règles métier du moteur d'optimisation Sprint 13 Lot S13.D.

Un fichier par règle (CdC § Tâche D) :

  - effet_banane.py        : filtre dur (cylindre exclu si largeur plaque
                             trop grande pour son développé)
  - echenillage.py         : scoring + coefs vitesse/gâche selon intervalle dev
  - compensation_laize_dev : bonus si on élargit l'intervalle laize quand
                             l'intervalle dev est forcément grand
  - confort_roulage        : coefs rayon + quinconce
  - capacite_couleurs      : filtre dur (machine assez de groupes couleurs
                             pour les couleurs d'impression + options)
  - contrainte_client      : plancher intervalle dev imposé par la machine
                             de pose du client final
"""
