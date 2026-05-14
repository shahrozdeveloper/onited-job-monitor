import requests
from bs4 import BeautifulSoup
import json
import os

URL = "https://www.onited.com/werken-bij/#onze-vacatures"

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

DATA_FILE = "jobs.json"


def get_jobs():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    jobs = {}

    job_elements = soup.select(".cats-job")

    for job in job_elements:
        link = job.select_one(".cats-job-title a")

        if not link:
            continue

        title = link.get_text(strip=True)
        href = link.get("href")

        jobs[href] = title

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
    requests.post(
        SLACK_WEBHOOK,
        json={"text": message}
    )


def main():
    current_jobs = get_jobs()
    previous_jobs = load_previous_jobs()

    current_set = set(current_jobs.keys())
    previous_set = set(previous_jobs.keys())

    added = current_set - previous_set
    removed = previous_set - current_set

    if added or removed:

        message = "🚨 *Onited Vacancy Changes Detected*\n\n"

        if added:
            message += "*NEW JOBS:*\n"
            for job in added:
                message += f"• {current_jobs[job]}\n{job}\n\n"

        if removed:
            message += "*REMOVED JOBS:*\n"
            for job in removed:
                message += f"• {previous_jobs[job]}\n{job}\n\n"

        send_slack_message(message)

    save_jobs(current_jobs)


if __name__ == "__main__":
    main()
