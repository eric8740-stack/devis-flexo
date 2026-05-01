"""Garde-fou weasyprint runtime (Hotfix-PDF-B 01/05/2026).

Avant ce hotfix, les 4 tests de tests/test_pdf_service.py étaient skippés
silencieusement par `pytestmark = skipif(not _WEASYPRINT_OK)` quand la
probe runtime weasyprint échouait — y compris en CI Linux Ubuntu (où les
libs natives GTK sont POURTANT installées via apt-get du workflow). Ce
skip silencieux a masqué le bug TypeError float/Decimal Sprint 4 (CI run
25208253433 = SUCCESS avec les 4 tests PDF skipped, mais PDF cassé en
prod Railway).

Ce fichier contient UN SEUL test garde-fou, SANS pytestmark, qui :
  - skip légitimement sur Windows local (libs GTK rarement présentes)
  - FAIL bruyamment sur Linux ou en CI si la probe échoue → alerte
    immédiate avec stack précise pour identifier la lib manquante

Si ce test fail en CI, compléter la liste apt-get dans :
  - backend/Dockerfile (env prod Railway)
  - .github/workflows/backend.yml (env CI Ubuntu)
"""
import os
import platform

import pytest


def _probe_weasyprint() -> tuple[bool, str]:
    """Probe runtime fraîche : tente write_pdf() sur un HTML trivial."""
    try:
        from weasyprint import HTML

        HTML(string="<html><body>probe</body></html>").write_pdf()
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, repr(exc)


def test_weasyprint_runtime_available_on_linux_or_ci():
    """weasyprint DOIT fonctionner sur CI Linux et en prod Railway.

    Skippé seulement en local Windows (sans GTK installé = comportement
    attendu pour les développeurs sous Windows qui n'ont pas besoin de
    générer de PDF localement).

    Si fail : une lib transitive manque dans Dockerfile + CI workflow.
    Compléter la liste apt-get puis relancer.
    """
    is_windows = platform.system() == "Windows"
    is_ci = os.environ.get("CI", "").lower() == "true"

    if is_windows and not is_ci:
        pytest.skip("Windows local sans GTK = skip légitime (pas en CI)")

    ok, err = _probe_weasyprint()
    assert ok, (
        f"weasyprint runtime KO sur {platform.system()} (CI={is_ci}). "
        f"Erreur : {err}. "
        f"Cause probable : lib transitive manquante. "
        f"Compléter la liste apt-get dans backend/Dockerfile + "
        f".github/workflows/backend.yml puis relancer la CI."
    )
