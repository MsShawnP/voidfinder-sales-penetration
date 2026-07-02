"""Thin entry point — named wsgi.py to avoid import collision with app/ package.

Health-check contract (the Spin Rate lesson, do not regress):

  /health  — liveness only. Returns 200 whenever the process is up.
             It NEVER touches the database. Hard-gating /health on
             the DB is the exact bug that took Spin Rate to an
             external 503: Fly restarts or de-routes the machine on
             a DB blip, and visitors get a platform error page
             instead of the branded shell.
  /ready   — readiness. Reports database connectivity for humans,
             deploy scripts, and monitors. Fly is NOT pointed at it.
"""

from dotenv import load_dotenv
from flask import jsonify

load_dotenv()

from app.app import server  # noqa: E402
from app.layout import register_layout  # noqa: E402

register_layout()


@server.route("/health")
def health():
    """Liveness: the process is serving. No database involvement."""
    return jsonify(status="ok"), 200


@server.route("/ready")
def ready():
    """Readiness: is the database answering and data loaded?"""
    from app.db import db_ready
    from app.data import data_available

    db_ok = db_ready()
    data_ok = data_available() if db_ok else False
    status = "ready" if (db_ok and data_ok) else "degraded"
    return jsonify(status=status, database=db_ok, data_loaded=data_ok), (
        200 if status == "ready" else 503
    )


if __name__ == "__main__":
    import os

    from app.app import app

    app.run(
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        use_reloader=False,
        port=int(os.environ.get("PORT", 8050)),
    )
