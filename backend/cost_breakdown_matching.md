# Cost breakdown matching — V7a (S7 Lot 7g)

Cas V1a (médian) en **mode matching** : top 3 cylindres magnétiques
compatibles avec le format 60×40, plaque 180 mm sur Mark Andy P5
(laize 330, banane Z_mini=96).

## Garde-fou métier

**HT identique pour les 3 candidats = HT V1a manuel = 1449.09 €.**
Les postes ne dépendent pas du choix de cylindre dans le moteur
actuel — seul le `prix_au_mille` peut varier (selon
`nb_etiq_par_metre`). Toute régression sur cet invariant doit être
investiguée (introduction d'une dépendance cylindre dans un poste ?).

## Top 3 candidats (tri intervalle croissant)

| Rang | Z | nb_etiq/tour | Circonf. mm | Pas mm | Intervalle mm | Étiq/m | HT € | Prix/1000 € |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 134 | 10 | 425.450 | 42.5450 | 2.5450 | 23 | 1449.09 | 7.00 |
| 2 | 121 | 9 | 384.175 | 42.6861 | 2.6861 | 23 | 1449.09 | 7.00 |
| 3 | 108 | 8 | 342.900 | 42.8625 | 2.8625 | 23 | 1449.09 | 7.00 |

## Postes (communs aux 3 candidats)

- **Coût de revient** : 1228.04 €
- **Marge appliquée** : 18.00 %
- **Prix vente HT** : 1449.09 €

| # | Libellé | Montant € |
|---|---|---:|
| P1 | Matière | 241.50 |
| P2 | Encres | 111.54 |
| P3 | Outillage / Clichés | 225.00 |
| P4 | Mise en route / Calage | 225.00 |
| P5 | Roulage | 187.50 |
| P6 | Finitions | 132.50 |
| P7 | Main d'œuvre opérateur | 105.00 |