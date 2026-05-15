"""Moteur d'optimisation Sprint 13 Lot S13.D.

Architecture :
  - types.py        : dataclasses pures (Format, Cylindre, Machine, Pose, ...)
                      indépendantes des modèles SQLAlchemy → séparation
                      domaine ↔ persistence.
  - regles/         : un fichier par règle métier (6 règles + 1 souveraineté).
  - moteur.py       : orchestrateur optimiser_pose() (S13.D.7).

Convention "pas de triche" (CdC § 658) : si moins de 3 candidats viables
après filtres durs, on RENVOIE moins de 3 — on ne dégrade jamais les
contraintes pour faire du remplissage.
"""
