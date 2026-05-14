"""
Email service using SendGrid.
Handles verification emails and other transactional messages.
"""

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@example.com")
APP_URL = os.getenv("APP_URL", "http://localhost:3000")


def send_verification_email(to_email: str, token: str) -> bool:
    """Send an email verification link to a new user."""
    if not SENDGRID_API_KEY:
        print(f"[EMAIL] SendGrid not configured. Verification token for {to_email}: {token}")
        return False

    verify_url = f"{APP_URL}/auth/verify?token={token}"

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject="Verify your MTG Deck Intelligence account",
        html_content=f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Welcome to MTG Deck Intelligence!</h2>
            <p>Click the button below to verify your email address:</p>
            <p style="margin: 30px 0;">
                <a href="{verify_url}"
                   style="background: #4F46E5; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Verify Email
                </a>
            </p>
            <p style="color: #666; font-size: 14px;">
                Or copy this link: {verify_url}
            </p>
            <p style="color: #999; font-size: 12px;">
                If you didn't create this account, you can ignore this email.
            </p>
        </div>
        """,
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"[EMAIL] Sent verification to {to_email}, status: {response.status_code}")
        return response.status_code in (200, 201, 202)
    except Exception as e:
        print(f"[EMAIL] Failed to send to {to_email}: {e}")
        return False