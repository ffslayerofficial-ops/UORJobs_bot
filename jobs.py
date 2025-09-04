import os
import requests
import logging

logger = logging.getLogger(__name__)

JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_API_KEY = os.getenv("ADZUNA_API_KEY")

async def fetch_jobs(keyword: str, location: str, pages: int = 1) -> list:
    """Fetch jobs from Jooble (primary) or Adzuna (fallback)."""
    # Try Jooble first
    if JOOBLE_API_KEY:
        try:
            headers = {"Content-Type": "application/json"}
            data = {"keywords": keyword, "location": location}
            response = requests.post(f"https://jooble.org/api/{JOOBLE_API_KEY}", json=data, headers=headers)
            response.raise_for_status()
            jooble_jobs = response.json().get('jobs', [])
            if jooble_jobs:
                logger.info(f"Found {len(jooble_jobs)} jobs on Jooble.")
                return [
                    {
                        "title": job.get("title"),
                        "company": job.get("company"),
                        "location": job.get("location"),
                        "salary": job.get("salary"),
                        "link": job.get("link"),
                    }
                    for job in jooble_jobs[:5]
                ]
        except Exception as e:
            logger.error(f"Jooble API error: {e}")

    # Fallback to Adzuna
    if ADZUNA_APP_ID and ADZUNA_API_KEY:
        try:
            url = (
                f"http://api.adzuna.com/v1/api/jobs/gb/search/{pages}?"
                f"app_id={ADZUNA_APP_ID}&app_key={ADZUNA_API_KEY}&"
                f"results_per_page=5&what={keyword}&where={location}&content-type=application/json"
            )
            response = requests.get(url)
            response.raise_for_status()
            adzuna_jobs = response.json().get('results', [])
            if adzuna_jobs:
                logger.info(f"Found {len(adzuna_jobs)} jobs on Adzuna.")
                return [
                    {
                        "title": job.get("title"),
                        "company": job.get("company", {}).get("display_name", "N/A"),
                        "location": job.get("location", {}).get("display_name", "N/A"),
                        "salary": f"Up to {job.get('salary_max', 'N/A')}" if job.get('salary_max') else "Not specified",
                        "link": job.get("redirect_url"),
                    }
                    for job in adzuna_jobs
                ]
        except Exception as e:
            logger.error(f"Adzuna API error: {e}")

    return []