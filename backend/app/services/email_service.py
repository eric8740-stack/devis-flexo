"""Service d'envoi d'emails — Sprint 12 multi-tenant.

Wrapper SendGrid avec fallback log-to-console quand `SENDGRID_API_KEY`
n'est pas définie (dev local + CI). Permet de développer/tester sans
compte SendGrid configuré.

Templates HTML inline simples (pas de Jinja2 pour MVP) :
- Logo texte "Devis Flexo"
- Message + bouton lien
- Footer minimal

URL du frontend lue depuis `APP_BASE_URL` (fallback Vercel prod).
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _send_email(to_email: str, subject: str, html_body: str) -> None:
    """Envoie un email via SendGrid OU log-to-console en mode dev/CI.

    Mode log-to-console (SENDGRID_API_KEY absent) :
    - WARNING avec subject + to + preview HTML pour faciliter le debug
    - Pas d'erreur levée, comme si l'email avait été envoyé

    Mode SendGrid (API key présente) :
    - Envoie via API SendGrid v3
    - Erreur réseau → log + raise (le router renverra 500 ou retry async)
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@devis-flexo.fr")

    if not api_key:
        logger.warning(
            "[email mock] SendGrid not configured — email NOT sent.\n"
            "  to=%s\n  from=%s\n  subject=%s\n  html_preview=%s",
            to_email,
            from_email,
            subject,
            html_body[:200].replace("\n", " "),
        )
        return

    # Import paresseux : la lib sendgrid n'est chargée que si on en a besoin
    # (évite le coût d'import en dev/test).
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=html_body,
    )
    try:
        client = SendGridAPIClient(api_key)
        response = client.send(message)
        logger.info(
            "Email sent via SendGrid: to=%s subject=%s status=%s",
            to_email,
            subject,
            response.status_code,
        )
    except Exception as exc:  # noqa: BLE001 — on log et on re-raise
        logger.error("SendGrid send failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Templates inline minimalistes
# ---------------------------------------------------------------------------


def _wrap_template(title: str, body_html: str) -> str:
    """Wrapper HTML commun (logo + body + footer)."""
    return f"""<!DOCTYPE html>
<html lang="fr"><body style="font-family:sans-serif;max-width:560px;margin:auto;padding:24px;">
  <h1 style="color:#0f172a;font-size:20px;margin:0 0 24px;">Devis Flexo</h1>
  <h2 style="color:#0f172a;font-size:16px;">{title}</h2>
  {body_html}
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:32px 0 16px;">
  <p style="color:#94a3b8;font-size:12px;">
    Vous recevez cet email car votre adresse a été utilisée pour
    créer un compte sur Devis Flexo. Si ce n'est pas vous, ignorez ce message.
  </p>
</body></html>"""


def _button(label: str, url: str) -> str:
    return (
        f'<p><a href="{url}" '
        'style="display:inline-block;background:#0f172a;color:#fff;'
        'padding:12px 20px;border-radius:6px;text-decoration:none;">'
        f"{label}</a></p>"
    )


# ---------------------------------------------------------------------------
# Emails métier
# ---------------------------------------------------------------------------


def send_confirmation_email(to_email: str, nom_contact: str, token: str) -> None:
    """Email envoyé à l'inscription : confirmation d'adresse."""
    base_url = os.getenv("APP_BASE_URL", "https://devis-flexo.vercel.app")
    confirm_url = f"{base_url}/confirm-email?token={token}"
    body = (
        f"<p>Bonjour {nom_contact},</p>"
        "<p>Merci de votre inscription. Cliquez sur le bouton ci-dessous "
        "pour confirmer votre adresse email et activer votre compte.</p>"
        f"{_button('Confirmer mon email', confirm_url)}"
        "<p style='color:#64748b;font-size:14px;'>"
        "Ce lien expire dans 24 heures."
        "</p>"
    )
    html = _wrap_template("Confirmation de votre email", body)
    _send_email(to_email, "Confirmez votre email — Devis Flexo", html)


def send_password_reset_email(
    to_email: str, nom_contact: str, token: str
) -> None:
    """Email de réinitialisation de password."""
    base_url = os.getenv("APP_BASE_URL", "https://devis-flexo.vercel.app")
    reset_url = f"{base_url}/reset-password?token={token}"
    body = (
        f"<p>Bonjour {nom_contact},</p>"
        "<p>Une demande de réinitialisation de votre password a été reçue. "
        "Cliquez sur le bouton ci-dessous pour choisir un nouveau password. "
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce "
        "message — votre password actuel reste valide.</p>"
        f"{_button('Réinitialiser mon password', reset_url)}"
        "<p style='color:#64748b;font-size:14px;'>"
        "Ce lien expire dans 1 heure."
        "</p>"
    )
    html = _wrap_template("Réinitialisation de votre password", body)
    _send_email(to_email, "Réinitialiser votre password — Devis Flexo", html)
