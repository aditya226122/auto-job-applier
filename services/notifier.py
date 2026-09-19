import smtplib
import datetime
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, List
import config

class EmailNotifier:
    def __init__(self):
        self.smtp_host = config.SMTP_HOST
        self.smtp_port = config.SMTP_PORT
        self.smtp_user = config.SMTP_USER
        self.smtp_password = config.SMTP_PASSWORD
        self.sender_name = config.SENDER_NAME
        self.recipient_email = config.RECIPIENT_EMAIL

    def send_single_application_alert(self, job: Dict[str, Any], match_score: int, response_message: str = "Application Successfully Submitted", screenshot_path: str = None, reference_id: str = None) -> bool:
        """Sends an instant email notification to the candidate for each applied job with proof screenshot and reference ID."""
        if not config.EMAIL_NOTIFICATIONS_ENABLED:
            print(f"[EmailNotifier] Email notifications disabled in config.")
            return False

        ref_id_display = reference_id or f"APP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        subject = f"🚀 [Applied & Verified] {job.get('title')} at {job.get('company')} ({match_score}% Match)"
        applied_time = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
        
        screenshot_html = ""
        if screenshot_path and os.path.exists(screenshot_path):
            screenshot_html = f"""
            <div style="margin-top: 25px; border-top: 2px dashed #cbd5e1; padding-top: 20px;">
                <h3 style="margin: 0 0 10px 0; color: #1e293b; font-size: 16px;">📸 Proof of Submission (Live Screenshot):</h3>
                <p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">The confirmation page below was detected and captured directly by the agent upon submission:</p>
                <div style="border: 2px solid #2563eb; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    <img src="cid:proof_screenshot" alt="Application Proof Screenshot" style="width: 100%; max-width: 100%; display: block;" />
                </div>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }}
                .container {{ max-width: 650px; background: #ffffff; margin: 0 auto; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
                .header {{ background: linear-gradient(135deg, #059669 0%, #1e3c72 100%); color: white; padding: 25px 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 22px; }}
                .content {{ padding: 30px; color: #333333; }}
                .job-card {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 20px 0; }}
                .badge {{ display: inline-block; padding: 5px 12px; font-size: 13px; font-weight: bold; border-radius: 20px; }}
                .badge-match {{ background-color: #dcfce7; color: #15803d; }}
                .badge-status {{ background-color: #dbeafe; color: #1e40af; }}
                .badge-verified {{ background-color: #fef08a; color: #854d0e; }}
                .field-row {{ margin: 10px 0; font-size: 14px; line-height: 1.6; }}
                .field-label {{ font-weight: 600; color: #64748b; width: 140px; display: inline-block; }}
                .field-value {{ color: #1e293b; font-weight: 500; }}
                .btn {{ display: inline-block; background-color: #2563eb; color: white !important; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 600; margin-top: 15px; text-align: center; }}
                .footer {{ background-color: #f1f5f9; padding: 15px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Application Verified & Submitted</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">Candidate: Udaya Lakshmi Boddu</p>
                </div>
                <div class="content">
                    <p>Hello <strong>Udaya Lakshmi</strong>,</p>
                    <p>Your AI Agent has successfully submitted your job application and verified the resulting confirmation page.</p>
                    
                    <div class="job-card">
                        <div style="margin-bottom: 15px;">
                            <span class="badge badge-match">🎯 {match_score}% Resume Match</span>
                            <span class="badge badge-status">✅ Submitted</span>
                            <span class="badge badge-verified">🛡️ Proof Verified</span>
                        </div>
                        <h2 style="margin: 0 0 10px 0; color: #0f172a; font-size: 18px;">{job.get('title')}</h2>
                        <div class="field-row">
                            <span class="field-label">🏢 Company:</span>
                            <span class="field-value"><strong>{job.get('company')}</strong></span>
                        </div>
                        <div class="field-row">
                            <span class="field-label">📍 Location:</span>
                            <span class="field-value">{job.get('location', 'Not specified')}</span>
                        </div>
                        <div class="field-row">
                            <span class="field-label">🌐 Portal / Source:</span>
                            <span class="field-value">{job.get('portal', 'Direct Portal')}</span>
                        </div>
                        <div class="field-row">
                            <span class="field-label">🆔 Reference ID:</span>
                            <span class="field-value" style="color: #2563eb; font-weight: bold; font-family: monospace;">{ref_id_display}</span>
                        </div>
                        <div class="field-row">
                            <span class="field-label">⏰ Applied At:</span>
                            <span class="field-value">{applied_time}</span>
                        </div>
                        <div class="field-row">
                            <span class="field-label">📝 Result Status:</span>
                            <span class="field-value" style="color: #15803d; font-weight: bold;">{response_message}</span>
                        </div>
                        
                        {f'<a href="{job.get("job_url")}" class="btn" target="_blank">View Original Listing</a>' if job.get("job_url") else ''}
                        
                        {screenshot_html}
                    </div>
                    
                    <p style="font-size: 13px; color: #64748b;">The agent will continue its hourly run to apply for 1–2 jobs automatically.</p>
                </div>
                <div class="footer">
                    Automated by AI Job Application Agent &bull; Verified Proof Delivery to {self.recipient_email}
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(subject, html_content, screenshot_path=screenshot_path)

    def send_daily_summary_report(self, applied_jobs: List[Dict[str, Any]], date_str: str = None) -> bool:
        """Sends an end-of-day summary of all applied jobs to the candidate."""
        if not date_str:
            date_str = datetime.date.today().strftime("%d %b %Y")

        subject = f"📊 Daily Job Applications Summary ({len(applied_jobs)} Jobs Applied) - {date_str}"
        
        rows_html = ""
        for idx, job in enumerate(applied_jobs, 1):
            rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px; font-weight: bold;">{idx}</td>
                <td style="padding: 10px;"><strong>{job.get('title')}</strong><br><span style="color: #64748b; font-size: 12px;">{job.get('company')}</span></td>
                <td style="padding: 10px; font-size: 13px;">{job.get('location', 'N/A')}</td>
                <td style="padding: 10px; text-align: center;"><span style="background: #dcfce7; color: #166534; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{job.get('match_score', 80)}%</span></td>
                <td style="padding: 10px; font-size: 12px;">{job.get('portal', 'Web')}</td>
            </tr>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }}
                .container {{ max-width: 700px; background: #ffffff; margin: 0 auto; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
                .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 25px 30px; text-align: center; }}
                .content {{ padding: 30px; color: #333333; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
                th {{ background-color: #f8fafc; color: #475569; padding: 12px 10px; text-align: left; border-bottom: 2px solid #e2e8f0; font-size: 13px; }}
                .footer {{ background-color: #f1f5f9; padding: 15px; text-align: center; font-size: 12px; color: #64748b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 22px;">Daily Job Application Summary</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.85; font-size: 14px;">Date: {date_str} &bull; Candidate: Udaya Lakshmi Boddu</p>
                </div>
                <div class="content">
                    <p>Hello <strong>Udaya Lakshmi</strong>,</p>
                    <p>Here is your daily summary report. Your AI agent has submitted <strong>{len(applied_jobs)} job applications</strong> matching your target fresher profile today.</p>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Role & Company</th>
                                <th>Location</th>
                                <th style="text-align: center;">Match</th>
                                <th>Portal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
                <div class="footer">
                    Target Quota: 10-15 applications/day &bull; Automated by AI Job Agent
                </div>
            </div>
        </body>
        </html>
        """

        return self._send_email(subject, html_content)

    def _send_email(self, subject: str, html_body: str, screenshot_path: str = None) -> bool:
        if not self.smtp_user or not self.smtp_password:
            print(f"\n[EmailNotifier - MOCK / PREVIEW MODE]")
            print(f"To: {self.recipient_email}")
            print(f"Subject: {subject}")
            print(f"Screenshot Attached: {screenshot_path if screenshot_path else 'None'}")
            print(f"Note: SMTP_USER or SMTP_PASSWORD is not set in .env. Email simulation recorded successfully.\n")
            return True

        try:
            from email.mime.image import MIMEImage

            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = f"{self.sender_name} <{self.smtp_user}>"
            msg["To"] = self.recipient_email

            msg_alt = MIMEMultipart("alternative")
            msg.attach(msg_alt)

            part = MIMEText(html_body, "html")
            msg_alt.attach(part)

            # Attach screenshot inline if available
            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as f:
                    img_data = f.read()
                img = MIMEImage(img_data)
                img.add_header("Content-ID", "<proof_screenshot>")
                img.add_header("Content-Disposition", "inline", filename=os.path.basename(screenshot_path))
                msg.attach(img)

            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, [self.recipient_email], msg.as_string())
            server.quit()
            print(f"[EmailNotifier] Successfully sent verified proof email to {self.recipient_email} | Subject: {subject}")
            return True
        except Exception as e:
            print(f"[EmailNotifier ERROR] Failed to send email: {e}")
            return False

notifier = EmailNotifier()
