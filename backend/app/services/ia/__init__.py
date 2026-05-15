"""Services IA Sprint 13 Lot S13.E (FlexoCheck).

Module dédié aux interactions Claude API multimodal. Architecture en
deux couches :

  - client.py        : wrapper bas niveau réutilisable (init lazy de
                       l'SDK Anthropic, gestion des erreurs, model name
                       paramétrable). Sera réutilisé pour les futurs
                       modules IA Sprint 14-15 (contrôle BAT, photos
                       palettes, etc.).
  - analyse_photo.py : service spécifique POC S13.E — analyse de photos
                       d'étiquettes pour estimer couleurs + techniques.
  - prompts/*.txt    : prompts texte (faciles à éditer sans toucher le
                       code, et faciles à versionner par PR).
"""
