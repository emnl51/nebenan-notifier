from apscheduler.schedulers.background import BackgroundScheduler
from app import database as db
from app.runner import run_job

_scheduler = BackgroundScheduler()


def _job_wrapper(job_id):
    run_job(job_id)


def sync_jobs():
    """DB'deki aktif joblara göre scheduler'ı günceller."""
    for job_obj in _scheduler.get_jobs():
        _scheduler.remove_job(job_obj.id)

    for job in db.list_jobs():
        if job["active"]:
            _scheduler.add_job(
                _job_wrapper,
                "interval",
                minutes=job["interval_minutes"] or 15,
                args=[job["id"]],
                id=str(job["id"]),
                next_run_time=None,  # ilk çalıştırma sync_jobs çağıran yerden manuel tetiklenebilir
            )


def start():
    sync_jobs()
    _scheduler.start()


def refresh():
    sync_jobs()
