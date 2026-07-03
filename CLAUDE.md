# devis-flexo

Ce dépôt, **devis-flexo**, est une application de devis pour les TPE de flexographie d'étiquettes : un backend FastAPI (Python) et un frontend Next.js qui exposent un modèle de coût industriel à 7 postes appliqué au métier de la flexo.

## Arborescence (dossiers suivis par git)

```text
devis-flexo/
├── .github/
│   └── workflows/
├── docs/
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── crud/
│   │   ├── data/
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── cost_engine/
│   │   │   ├── ia/
│   │   │   │   └── prompts/
│   │   │   ├── optimisation/
│   │   │   │   └── regles/
│   │   │   └── rebobinage/
│   │   └── templates/
│   ├── scripts/
│   ├── seeds/
│   └── tests/
│       └── optimisation/
└── frontend/
    ├── public/
    │   ├── assets/
    │   │   └── bobines/
    │   └── help/
    │       ├── calculer-devis/
    │       ├── complexes/
    │       ├── machines/
    │       ├── op-finition/
    │       ├── parametres/
    │       ├── partenaires-st/
    │       └── produits-clients/
    └── src/
        ├── app/
        │   ├── admin/
        │   ├── atelier/
        │   │   └── controle-bat/
        │   │       ├── [id]/
        │   │       └── _components/
        │   ├── catalogue/
        │   │   ├── [id]/
        │   │   └── nouveau/
        │   ├── charges-mensuelles/
        │   │   ├── [id]/
        │   │   └── nouveau/
        │   ├── clients/
        │   │   ├── [id]/
        │   │   └── nouveau/
        │   ├── complexes/
        │   │   ├── [id]/
        │   │   └── nouveau/
        │   ├── confirm-email/
        │   ├── devis/
        │   │   ├── [id]/
        │   │   │   ├── _components/
        │   │   │   └── edit/
        │   │   ├── nouveau/
        │   │   └── nouvelle/
        │   ├── fonts/
        │   ├── forgot-password/
        │   ├── fournisseurs/
        │   │   ├── [id]/
        │   │   └── nouveau/
        │   ├── ia/
        │   │   ├── analyser-photo/
        │   │   └── analyses/
        │   │       └── [id]/
        │   ├── login/
        │   ├── machines/
        │   │   ├── [id]/
        │   │   └── nouveau/
        │   ├── onboarding/
        │   ├── operations-finition/
        │   │   ├── [id]/
        │   │   └── nouveau/
        │   ├── optimisation/
        │   │   └── _components/
        │   │       └── brief-client/
        │   ├── parametres/
        │   │   ├── entreprise/
        │   │   ├── mon-parc/
        │   │   │   └── _components/
        │   │   ├── options-fabrication/
        │   │   ├── outils/
        │   │   └── tarifs/
        │   ├── partenaires-st/
        │   │   ├── [id]/
        │   │   └── nouveau/
        │   ├── register/
        │   ├── reset-password/
        │   ├── stock/
        │   └── strategique/
        │       └── _components/
        ├── components/
        │   ├── admin/
        │   ├── devis/
        │   ├── feedback/
        │   ├── help/
        │   │   └── content/
        │   ├── ia/
        │   └── ui/
        ├── contexts/
        ├── hooks/
        ├── lib/
        │   └── api/
        └── types/
```

Bien évidemment, cette arborescence est mise à jour au fur et à mesure que de nouveaux dossiers et fichiers sont ajoutés et commités.

## Capsule contexte — pour les sessions sans la config globale

Mainteneur : **Eric Paysant** (ERP Conseil). Profil et règles complets dans le dépôt
privé `eric8740-stack/claude-config` (chargé d'office dans les sessions locales sur
les PC d'Eric ; cette capsule est le minimum vital pour les autres sessions).

- Préférences : réponses directes ; trancher les détails techniques sans multiplier
  les questions ; conventional commits ; on teste APRÈS push (jamais de merge sur
  build Vercel rouge).
- Fin de session : tout committer et **pousser** — deux PC se synchronisent par
  `git pull`, et l'un part en rendez-vous client.
- Gros chantier : proposer un découpage en 2 sessions Claude Code parallèles.
- Valeur sacrée du moteur : **V1a = 1 449,09 € HT exact** — ne jamais casser.
- ⚠️ Dépôt **PUBLIC** : jamais de données client réelles, de coordonnées personnelles
  ni de secrets dans le code, les docs ou les commits.
