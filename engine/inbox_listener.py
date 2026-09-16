import imaplib
import email
from email.header import decode_header
import datetime
from typing import List, Dict, Any
import config
from services.db import db

class CompanyEmailVerifier:
    def __init__(self):
        self.imap_host = "imap.gmail.com"
        self.imap_port = 993
        self.user = config.SMTP_USER
        self.password = config.SMTP_PASSWORD
        self.candidate_email = config.RECIPIENT_EMAIL

    def check_incoming_company_confirmations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Connects to the email inbox and scans for incoming recruitment / ATS confirmation emails
        from employers and job boards (e.g. Workday, Greenhouse, Lever, TCS, Infosys, Wipro, LinkedIn, Naukri).
        """
        if not self.user or not self.password:
            print("[InboxVerifier] IMAP credentials not configured.")
            return []

        confirmations = []
        try:
            # Connect via IMAP SSL
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.user, self.password)
            mail.select("inbox")

            # Search for emails related to application confirmations
            keywords = ['"Application"', '"Received"', '"Applied"', '"Confirmation"', '"Careers"', '"Candidate"']
            search_query = f'(OR (OR SUBJECT "Application" SUBJECT "Careers") (OR SUBJECT "Received" SUBJECT "Applied"))'
            
            status, messages = mail.search(None, search_query)
            if status != "OK" or not messages[0]:
                mail.logout()
                return []

            msg_ids = messages[0].split()[-limit:]
            for msg_id in reversed(msg_ids):
                res, msg_data = mail.fetch(msg_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject, encoding = decode_header(msg.get("Subject", ""))[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8", errors="ignore")

                        from_sender, encoding = decode_header(msg.get("From", ""))[0]
                        if isinstance(from_sender, bytes):
                            from_sender = from_sender.decode(encoding or "utf-8", errors="ignore")

                        date_str = msg.get("Date", "")
                        
                        # Body snippet
                        body_snippet = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body_snippet = part.get_payload(decode=True).decode(errors="ignore")[:300]
                                    break
                        else:
                            body_snippet = msg.get_payload(decode=True).decode(errors="ignore")[:300]

                        confirmations.append({
                            "subject": subject,
                            "from_sender": from_sender,
                            "date": date_str,
                            "snippet": body_snippet
                        })

            mail.logout()
            return confirmations
        except Exception as e:
            print(f"[InboxVerifier Error] Could not check inbox: {e}")
            return []

inbox_verifier = CompanyEmailVerifier()
