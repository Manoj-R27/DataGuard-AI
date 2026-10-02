import os
import logging
import requests
from dotenv import load_dotenv
from src.data_loader import load_baseline
from src.simulate import simulate_days

logging.basicConfig(level=os.getenv("DATAGUARD_LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("dataguard.scheduler")
load_dotenv()


def run_simulated_day(day_index: int = 1, api_url: str | None = None):
    """Cron-callable job; simulation is explicitly synthetic."""
    api_url = api_url or os.getenv("DATAGUARD_API_URL", "http://localhost:8000")
    days = simulate_days(load_baseline())
    name, frame, _ = days[day_index % len(days)]
    path = f"/tmp/{name}.csv"; frame.to_csv(path, index=False)
    with open(path, "rb") as handle:
        response = requests.post(f"{api_url}/ingest", params={"batch_id": name}, headers={"X-API-Key": os.getenv("DATAGUARD_API_KEY", "")}, files={"file": (f"{name}.csv", handle, "text/csv")}, timeout=30)
    logger.info("Scheduled batch submitted", extra={"batch_id": name, "severity": "unknown"})
    return response.json()

if __name__ == "__main__": logger.info("Scheduled batch complete", extra={"batch_id": "manual", "severity": "unknown"})
