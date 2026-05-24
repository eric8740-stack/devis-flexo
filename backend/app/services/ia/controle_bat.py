"""Service IA Contrôle BAT — Sprint 15 Lot 2.

Compare la photo du 1er tirage en sortie de presse au BAT validé client
(2 images Claude API multimodal). Retourne un dict structuré +
`cout_api_eur` calculé depuis l'usage tokens.

Pipeline :
  1. Charge le prompt `prompts/controle_bat.txt`
  2. Si `sens_demande` fourni, préfixe le prompt avec « Sens demandé : SEx »
  3. Appelle `analyser_images()` du wrapper avec [BAT, tirage]
  4. Parse le JSON strict
  5. Valide les champs requis + literals (decision_recommandee,
     niveau_confiance_analyse, gravités/types d'écarts)
  6. Calcule le coût API à partir de l'usage tokens
  7. Retourne le payload enrichi de `cout_api_eur`

L'analyse IA est une AIDE à la décision opérateur — la décision finale
revient au chef d'atelier (cf. brief CDC section 03f).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.services.ia.client import (
    IAClientError,
    analyser_images,
    lire_prompt,
    parse_json_strict,
)


# Champs obligatoires dans la réponse Claude — si l'un manque, on lève
# IAClientError plutôt que retourner un payload incomplet au router.
CHAMPS_REQUIS = (
    "score_conformite_global",
    "decision_recommandee",
    "ecarts_detectes",
    "elements_conformes",
    "elements_manquants",
    "niveau_confiance_analyse",
    "limites_analyse",
    "sens_sortie_detecte",
    "alerte_sens_enroulement",
)

DECISIONS_RECOMMANDEES = frozenset(
    {"valider", "ajuster_avant_demarrage", "rejeter"}
)
NIVEAUX_CONFIANCE = frozenset({"haut", "moyen", "faible"})
GRAVITES_ECART = frozenset({"critique", "majeur", "mineur"})
TYPES_ECART = frozenset(
    {"couleur", "position", "texte", "decoupe", "finition", "defaut_impression"}
)

# Modèle cible (cf. brief Lot 2 : « claude-sonnet »). On reste explicite
# plutôt que d'hériter du DEFAULT_MODEL du wrapper : si quelqu'un bascule
# le default sur Opus ou Haiku, ce service garde la cible coût documentée
# (0,03-0,08 €/contrôle).
MODELE_CIBLE = "claude-sonnet-4-6"
# Budget tokens sortie : le JSON de réponse est compact (5-15 écarts max,
# quelques strings courtes) — 1500 laisse de la marge confort.
MAX_TOKENS_SORTIE = 1500

# Pricing Anthropic claude-sonnet-4-6 (USD / 1M tokens) — sources de la
# pricing page publique au moment du Sprint 15. Si Anthropic révise les
# tarifs, ajuster ici (les tests ne checkent pas la valeur exacte du
# coût, juste sa positivité, donc la mise à jour n'invalide rien).
PRIX_USD_INPUT_PAR_M = Decimal("3.0")
PRIX_USD_OUTPUT_PAR_M = Decimal("15.0")
# Conversion USD → EUR. Approximation : permet d'afficher un ordre de
# grandeur en € pour le suivi coût. Pas critique — le facturé Anthropic
# reste en USD et c'est lui qui fait foi côté compta.
TAUX_USD_EUR = Decimal("0.92")


def _calculer_cout_eur(input_tokens: int, output_tokens: int) -> Decimal:
    """Calcule le coût € approximatif de l'appel à partir de l'usage tokens.

    cout_usd = (input * 3 + output * 15) / 1_000_000
    cout_eur = cout_usd * 0.92

    Arrondi à 4 décimales pour rester sous la précision NUMERIC(6,4) du
    modèle ControleBat.cout_api_eur.
    """
    cout_usd = (
        Decimal(input_tokens) * PRIX_USD_INPUT_PAR_M
        + Decimal(output_tokens) * PRIX_USD_OUTPUT_PAR_M
    ) / Decimal(1_000_000)
    cout_eur = cout_usd * TAUX_USD_EUR
    # Quantize à 4 décimales (cohérent avec NUMERIC(6,4)).
    return cout_eur.quantize(Decimal("0.0001"))


def _valider_payload(payload: dict[str, Any]) -> None:
    """Vérifie la structure du payload retourné par Claude.

    Champs requis présents + literals dans les sets autorisés.
    Lève IAClientError avec un message explicite à la 1re anomalie.
    """
    manquants = [c for c in CHAMPS_REQUIS if c not in payload]
    if manquants:
        raise IAClientError(
            f"Réponse Claude incomplète, champs manquants : {manquants}. "
            f"Champs présents : {list(payload.keys())}"
        )

    decision = payload["decision_recommandee"]
    if decision not in DECISIONS_RECOMMANDEES:
        raise IAClientError(
            f"decision_recommandee invalide : {decision!r}. "
            f"Attendu : {sorted(DECISIONS_RECOMMANDEES)}"
        )

    niveau = payload["niveau_confiance_analyse"]
    if niveau not in NIVEAUX_CONFIANCE:
        raise IAClientError(
            f"niveau_confiance_analyse invalide : {niveau!r}. "
            f"Attendu : {sorted(NIVEAUX_CONFIANCE)}"
        )

    # ecarts_detectes : valider type + gravite de chaque écart si la liste
    # n'est pas vide. On accepte une liste vide (= aucun écart détecté).
    ecarts = payload["ecarts_detectes"]
    if not isinstance(ecarts, list):
        raise IAClientError(
            f"ecarts_detectes doit être une liste, reçu : {type(ecarts).__name__}"
        )
    for idx, ecart in enumerate(ecarts):
        if not isinstance(ecart, dict):
            raise IAClientError(
                f"ecarts_detectes[{idx}] doit être un objet, "
                f"reçu : {type(ecart).__name__}"
            )
        t = ecart.get("type")
        g = ecart.get("gravite")
        if t not in TYPES_ECART:
            raise IAClientError(
                f"ecarts_detectes[{idx}].type invalide : {t!r}. "
                f"Attendu : {sorted(TYPES_ECART)}"
            )
        if g not in GRAVITES_ECART:
            raise IAClientError(
                f"ecarts_detectes[{idx}].gravite invalide : {g!r}. "
                f"Attendu : {sorted(GRAVITES_ECART)}"
            )


def comparer_bat_vs_tirage(
    bat_image_bytes: bytes,
    tirage_image_bytes: bytes,
    sens_demande: str | None = None,
    bat_mime_type: str = "image/jpeg",
    tirage_mime_type: str = "image/jpeg",
) -> dict[str, Any]:
    """Compare un BAT et un 1er tirage via Claude API et renvoie l'analyse.

    Args:
      bat_image_bytes : binaire du BAT validé client.
      tirage_image_bytes : binaire de la photo du 1er tirage.
      sens_demande : sens d'enroulement demandé au format SE1..SE8 (ou None).
        Si fourni, est injecté en début de prompt pour aider Claude à
        signaler une éventuelle divergence via `alerte_sens_enroulement`.
      bat_mime_type : mime type du BAT (default image/jpeg, accepte aussi
        image/png, image/webp, image/gif — cf. wrapper).
      tirage_mime_type : idem pour le 1er tirage.

    Returns:
      Dict avec les champs CHAMPS_REQUIS + clé additionnelle `cout_api_eur`
      (Decimal arrondi à 4 décimales).

    Raises:
      IAClientError : entrées invalides, JSON Claude inexploitable, champ
      manquant, literal hors set autorisé.
    """
    prompt = lire_prompt("controle_bat.txt")
    if sens_demande is not None:
        prompt = (
            f"Contexte : Sens demandé : {sens_demande}.\n\n" + prompt
        )

    texte, usage = analyser_images(
        prompt,
        [
            (bat_image_bytes, bat_mime_type),
            (tirage_image_bytes, tirage_mime_type),
        ],
        model=MODELE_CIBLE,
        max_tokens=MAX_TOKENS_SORTIE,
    )

    payload = parse_json_strict(texte)
    _valider_payload(payload)

    payload["cout_api_eur"] = _calculer_cout_eur(
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )
    return payload
