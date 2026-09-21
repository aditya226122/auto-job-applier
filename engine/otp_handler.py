import imaplib
import email
from email.header import decode_header
import re
import time
import datetime
from typing import Optional, Dict, Any
import config

class EmailOTPHandler:
    """Real-time IMAP email listener that intercepts verification OTPs and activation links."""

    def __init__(self):
        self.imap_host = "imap.gmail.com"
        self.imap_port = 993
        self.user = config.SMTP_USER
        self.password = config.SMTP_PASSWORD

    def wait_for_otp_or_link(self, keyword: str = "", timeout_seconds: int = 45) -> Optional[Dict[str, Any]]:
        """
        Polls IMAP inbox every 3 seconds for up to timeout_seconds to intercept
        an incoming verification code or activation URL.
        """
        if not self.user or not self.password:
            print("[OTPHandler] IMAP credentials not configured.")
            return None

        print(f"[OTPHandler] ⏳ Listening for incoming verification email / OTP (keyword: '{keyword}')...")
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            result = self._check_recent_emails(keyword)
            if result:
                print(f"[OTPHandler] 🎯 Intercepted verification message: OTP={result.get('otp')} | Link={result.get('link')}")
                return result
            time.sleep(3.0)

        print(f"[OTPHandler] ⚠ No OTP received within {timeout_seconds}s timeout.")
        return None

    def _check_recent_emails(self, keyword: str = "") -> Optional[Dict[str, Any]]:
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.user, self.password)
            mail.select("inbox")

            # Search recent emails in inbox
            status, messages = mail.search(None, "ALL")
            if status != "OK" or not messages[0]:
                mail.logout()
                return None

            msg_ids = messages[0].split()[-10:]  # Inspect last 10 messages
            for msg_id in reversed(msg_ids):
                res, msg_data = mail.fetch(msg_id, "(RFC822)")
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        
                        subject_header = decode_header(msg.get("Subject", ""))[0]
                        subject = subject_header[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(subject_header[1] or "utf-8", errors="ignore")

                        from_header = decode_header(msg.get("From", ""))[0]
                        from_sender = from_header[0]
                        if isinstance(from_sender, bytes):
                            from_sender = from_sender.decode(from_header[1] or "utf-8", errors="ignore")

                        # Extract text content
                        body_text = ""
                        if msg.is_multipart():
                            for p in msg.walk():
                                if p.get_content_type() in ("text/plain", "text/html"):
                                    payload = p.get_payload(decode=True)
                                    if payload:
                                        body_text += payload.decode(errors="ignore") + " "
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body_text = payload.decode(errors="ignore")

                        full_content = f"{subject} {body_text}"
                        
                        # Match keyword if provided
                        if keyword and keyword.lower() not in full_content.lower() and keyword.lower() not in from_sender.lower():
                            continue

                        # Check for OTP patterns
                        otp_match = re.search(r'(?:otp|code|verification code|security code|pin)\s*(?:is|:|-)?\s*([0-9]{4,8})', full_content, re.IGNORECASE)
                        otp_code = None
                        if otp_match:
                            otp_code = otp_match.group(1)
                        else:
                            generic_digits = re.findall(r'\b[0-9]{6}\b', full_content)
                            if generic_digits:
                                otp_code = generic_digits[0]

                        # Check for activation links
                        link_match = re.search(r'https?://[^\s<>"\'\)]+(?:verify|activate|confirm|token|auth)[^\s<>"\'\)]*', full_content, re.IGNORECASE)
                        activation_link = link_match.group(0) if link_match else None

                        if otp_code or activation_link:
                            mail.logout()
                            return {
                                "otp": otp_code,
                                "link": activation_link,
                                "subject": subject,
                                "from_sender": from_sender
                            }

            mail.logout()
            return None
        except Exception as e:
            return None

otp_handler = EmailOTPHandler()
