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
