from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

URL = "https://www.onited.com/werken-bij/#onze-vacatures"
SLACK_WEBHOOK    = os.getenv("SLACK_WEBHOOK_URL")
GMAIL_ADDRESS    = os.getenv("GMAIL_ADDRESS")
GMAIL_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "")  # comma-separated list
DATA_FILE = "jobs.json"


def get_jobs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(5000)
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, "html.parser")
    jobs = {}
    for job in soup.select(".cats-job"):
        link = job.select_one(".cats-job-title a")
        if not link:
            continue
        jobs[link.get("href")] = link.get_text(strip=True)
    return jobs


def load_previous_jobs():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_jobs(jobs):
    with open(DATA_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def send_slack_message(message):
    if not SLACK_WEBHOOK:
        return
    requests.post(SLACK_WEBHOOK, json={"text": message})


def send_email(added, removed, current_jobs, previous_jobs):
    if not GMAIL_ADDRESS or not GMAIL_PASSWORD or not EMAIL_RECIPIENTS:
        return

    recipients = [r.strip() for r in EMAIL_RECIPIENTS.split(",") if r.strip()]
    if not recipients:
        return

    # Build plain text body
    body_text = "Onited Vacancy Changes Detected\n"
    body_text += "=" * 40 + "\n\n"
    if added:
        body_text += "NEW POSITIONS:\n"
        for href in added:
            body_text += f"  + {current_jobs[href]}\n    {href}\n\n"
    if removed:
        body_text += "REMOVED POSITIONS:\n"
        for href in removed:
            body_text += f"  - {previous_jobs[href]}\n\n"
    body_text += f"\nView all vacatures: {URL}"

    # Build HTML body
    new_rows = ""
    for href in added:
        new_rows += f"""
        <tr>
          <td style="padding:8px 12px;">
            <span style="color:#16a34a; font-weight:600;">&#43; New</span>
          </td>
          <td style="padding:8px 12px;">
            <a href="{href}" style="color:#1d4ed8;">{current_jobs[href]}</a>
          </td>
        </tr>"""

    removed_rows = ""
    for href in removed:
        removed_rows += f"""
        <tr>
          <td style="padding:8px 12px;">
            <span style="color:#dc2626; font-weight:600;">&#8722; Removed</span>
          </td>
          <td style="padding:8px 12px; color:#6b7280; text-decoration:line-through;">
            {previous_jobs[href]}
          </td>
        </tr>"""

    body_html = f"""
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto;">
      <div style="background:#ff6b35; padding:20px 24px; border-radius:8px 8px 0 0;">
        <h2 style="color:#ffffff; margin:0; font-size:18px;">
          🚨 Onited Vacancy Changes Detected
        </h2>
      </div>
      <div style="border:1px solid #e5e7eb; border-top:none; border-radius:0 0 8px 8px; padding:20px 24px;">
        <table style="width:100%; border-collapse:collapse;">
          <thead>
            <tr style="background:#f9fafb;">
              <th style="padding:8px 12px; text-align:left; font-size:13px; color:#6b7280;">Status</th>
              <th style="padding:8px 12px; text-align:left; font-size:13px; color:#6b7280;">Position</th>
            </tr>
          </thead>
          <tbody>
            {new_rows}
            {removed_rows}
          </tbody>
        </table>
        <div style="margin-top:20px; padding-top:16px; border-top:1px solid #e5e7eb;">
          <a href="{URL}" style="background:#ff6b35; color:#ffffff; padding:10px 20px;
             border-radius:6px; text-decoration:none; font-size:14px;">
            View all vacatures →
          </a>
        </div>
        <p style="margin-top:16px; font-size:12px; color:#9ca3af;">
          Monitored by Shahroz — shahrozshahid.com
        </p>
      </div>
    </div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚨 Onited: {len(added)} new, {len(removed)} removed"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())


def main():
    current_jobs  = get_jobs()
    previous_jobs = load_previous_jobs()

    added   = set(current_jobs.keys()) - set(previous_jobs.keys())
    removed = set(previous_jobs.keys()) - set(current_jobs.keys())

    if added or removed:
        # Slack
        message = "🚨 *Onited Vacancy Changes Detected*\n\n"
        if added:
            message += "*NEW JOBS:*\n"
            for href in added:
                message += f"• {current_jobs[href]}\n{href}\n\n"
        if removed:
            message += "*REMOVED JOBS:*\n"
            for href in removed:
                message += f"• {previous_jobs[href]}\n{href}\n\n"
        send_slack_message(message)

        # Email
        send_email(added, removed, current_jobs, previous_jobs)

    save_jobs(current_jobs)


if __name__ == "__main__":
    main()
