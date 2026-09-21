import imaplib
import email
from email.header import decode_header
import re
import time
from typing import Optional
import config

class OTPHandler:
    def __init__(self):
        self.imap_host = 'imap.gmail.com'
        self.imap_port = 993
        self.user = (config.CANDIDATE_EMAIL_PASSWORD and config.RECIPIENT_EMAIL) or config.SMTP_USER
        self.password = config.CANDIDATE_EMAIL_PASSWORD or config.SMTP_PASSWORD

    def wait_for_otp(self, sender_hint: str = '', timeout_seconds: int = 60, poll_interval: float = 3.0) -> Optional[str]:
        if not self.user or not self.password:
            print('[OTPHandler] Gmail credentials not configured.')
            return None

        print(f'[OTPHandler] Waiting up to {timeout_seconds}s for OTP from {sender_hint} to {self.user}...')
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
                mail.login(self.user, self.password)
                mail.select('inbox')

                status, messages = mail.search(None, 'UNSEEN')
                if status == 'OK' and messages[0]:
                    msg_ids = messages[0].split()
                    for msg_id in reversed(msg_ids[-5:]):
                        res, msg_data = mail.fetch(msg_id, '(RFC822)')
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                
                                subject, encoding = decode_header(msg.get('Subject', ''))[0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode(encoding or 'utf-8', errors='ignore')

                                from_sender, encoding = decode_header(msg.get('From', ''))[0]
                                if isinstance(from_sender, bytes):
                                    from_sender = from_sender.decode(encoding or 'utf-8', errors='ignore')

                                body_text = ''
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() in ('text/plain', 'text/html'):
                                            payload = part.get_payload(decode=True)
                                            if payload:
                                                body_text += payload.decode(errors='ignore') + ' '
                                else:
                                    payload = msg.get_payload(decode=True)
                                    if payload:
                                        body_text = payload.decode(errors='ignore')

                                otp_match = re.search(r'\b([0-9]{4,6})\b', body_text)
                                if otp_match:
                                    otp = otp_match.group(1)
                                    print(f'[OTPHandler] Intercepted OTP: {otp} from {from_sender}')
                                    mail.logout()
                                    return otp

                mail.logout()
            except Exception as e:
                print(f'[OTPHandler Exception] {e}')

            time.sleep(poll_interval)

        return None

otp_handler = OTPHandler()
