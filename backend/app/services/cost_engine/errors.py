class CostEngineError(ValueError):
    """Erreur métier remontée par le moteur de coût v2.

    Levée par les calculateurs ou l'orchestrateur quand une donnée
    requise est manquante ou incohérente (tarif inconnu, complexe sans
    grammage, type d'encre inexistant, etc.).

    Sera convertie en HTTP 422 par le router (Lot 3f).
    """
