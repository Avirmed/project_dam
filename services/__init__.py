"""Background services run by the in-process worker (services.scheduler).

Each job is a plain function executed inside the Flask app context on its own
cadence; jobs must be idempotent and short. Register them in scheduler.JOBS.
"""
