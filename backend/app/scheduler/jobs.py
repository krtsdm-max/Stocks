import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.services.recommendation_engine import run_all_recommendations, update_track_record

logger = logging.getLogger(__name__)

EST = pytz.timezone("America/New_York")

_scheduler: BackgroundScheduler = None


def _is_market_open() -> bool:
    now_est = datetime.now(tz=EST)
    if now_est.weekday() >= 5:  # Saturday/Sunday
        return False
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now_est <= market_close


def hourly_recommendation_job():
    if not _is_market_open():
        logger.info("Market is closed — skipping hourly recommendation job.")
        return
    logger.info("Running hourly recommendation job...")
    db = SessionLocal()
    try:
        result = run_all_recommendations(db)
        logger.info(f"Recommendations updated: {result}")
    except Exception as e:
        logger.error(f"Hourly job error: {e}")
    finally:
        db.close()


def daily_track_record_job():
    logger.info("Running daily track-record update job...")
    db = SessionLocal()
    try:
        update_track_record(db)
        logger.info("Track record updated.")
    except Exception as e:
        logger.error(f"Daily job error: {e}")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=EST)

    # Hourly during market hours (09:30–16:00 EST, Mon–Fri)
    _scheduler.add_job(
        hourly_recommendation_job,
        CronTrigger(
            day_of_week="mon-fri",
            hour="9-16",
            minute="30",
            timezone=EST,
        ),
        id="hourly_recommendations",
        replace_existing=True,
    )

    # Daily after market close
    _scheduler.add_job(
        daily_track_record_job,
        CronTrigger(
            day_of_week="mon-fri",
            hour=16,
            minute=15,
            timezone=EST,
        ),
        id="daily_track_record",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("APScheduler started.")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
