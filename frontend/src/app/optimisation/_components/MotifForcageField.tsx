"use client";

// Lot Souveraineté — champ « motif de forçage » HARMONISÉ (Règle 7).
//
// Le motif est RECOMMANDÉ, pas obligatoire : le calcul passe même si le champ
// est vide (le backend renvoie au pire un warning NON bloquant). Un motif
// absent ou trop court (< 10 car.) déclenche une PETITE NOTE DISCRÈTE (grise,
// courte) — surtout PAS un encart d'erreur type « Calcul impossible ». Pattern
// aligné sur le bloc bord latéral L1, réutilisé par les forçages intervalle
// laize / dev / épaisseur.

const MOTIF_MIN = 10;

export function MotifForcageField({
  motif,
  onChange,
  testIdPrefix,
}: {
  motif: string;
  onChange: (value: string) => void;
  /** Préfixe data-testid : `${prefix}-motif` (textarea) + `${prefix}-note`. */
  testIdPrefix: string;
}) {
  const motifCourt = motif.trim().length < MOTIF_MIN;
  return (
    <div className="space-y-1">
      <textarea
        className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        rows={2}
        placeholder="Motif (recommandé — Règle 7)"
        value={motif}
        onChange={(e) => onChange(e.target.value)}
        data-testid={`${testIdPrefix}-motif`}
      />
      <p className="text-xs text-muted-foreground">
        Tracé si renseigné — le calcul passe même sans motif.
      </p>
      {motifCourt && (
        <p
          data-testid={`${testIdPrefix}-note`}
          className="text-xs text-muted-foreground"
        >
          ⓘ Forçage sans motif — note recommandée (non bloquant).
        </p>
      )}
    </div>
  );
}
