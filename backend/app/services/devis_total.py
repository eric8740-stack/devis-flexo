"""Total HT du devis = base cost_engine + contribution rebobinage (bug #6 6.2e-final).

Le coût rebobinage entre désormais dans `devis.ht_total_eur`. Sa contribution
vient de la ligne **multi-lots** (`rebobinage_multilots`, épaisseur réelle +
paroi par lot) QUAND elle existe, sinon de la ligne **mono-lot** legacy
(`rebobinage`), sinon 0.

INVARIANT SACRÉ : `payload_output["prix_vente_ht_eur"]` reste la valeur PURE du
cost_engine (7 postes) — JAMAIS augmentée du rebobinage. Le benchmark V1a
(1 449,09 €) et le tripwire P0b (704,07 €) asserent ce champ base sur des
scénarios SANS rebobinage → contribution 0 → `ht_total = base`, donc inchangés.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def contribution_rebobinage_eur(payload_output: dict | None) -> Decimal:
    """Coût rebobinage qui ENTRE dans `ht_total`.

    Priorité : `rebobinage_multilots` (par lot, épaisseur réelle + paroi) >
    `rebobinage` (mono-lot legacy) > 0. Une ligne ne compte que si elle est
    marquée `applique`.
    """
    if not payload_output:
        return Decimal("0")
    multilots = payload_output.get("rebobinage_multilots")
    if isinstance(multilots, dict) and multilots.get("applique"):
        return Decimal(str(multilots.get("cout_total_rebobinage_eur", "0")))
    mono = payload_output.get("rebobinage")
    if isinstance(mono, dict) and mono.get("applique"):
        return Decimal(str(mono.get("cout_total_rebobinage_eur", "0")))
    return Decimal("0")


def ht_total_avec_rebobinage(
    base_ht_eur: Decimal | None, payload_output: dict | None
) -> Decimal | None:
    """`ht_total` = base cost_engine + contribution rebobinage.

    `base_ht_eur` None (chiffrage incomplet) → None : on n'invente pas de
    total. Sinon on additionne la contribution (0 si aucune ligne rebobinage).
    """
    if base_ht_eur is None:
        return None
    total = Decimal(str(base_ht_eur)) + contribution_rebobinage_eur(payload_output)
    # ht_total_eur est un montant (Numeric(10,2)) : on quantize à 2 décimales
    # (le coût rebobinage est porté à 4 décimales par le moteur). Déterministe
    # vs l'arrondi implicite de la colonne DB.
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
