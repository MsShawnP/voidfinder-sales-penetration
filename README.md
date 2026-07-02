# Void Finder

Void Finder answers one question: where are we authorized but not
selling, and what is each gap costing us? It scans the Cinderhaven
authorization matrix against POS data, flags stores where an
authorized item isn't scanning, classifies each void (never-scanned
vs went-dark), dollarizes the opportunity from median comparable-store
velocity, and produces a ranked, broker-ready work list. Tool #5 of
the Cinderhaven sales-penetration series.

**Stack:** Python 3.11, Dash 3.x, Plotly 6.0, pandas, psycopg2 →
cinderhaven-db (Postgres), dash-ag-grid, Gunicorn + Docker + Fly.io.

**Run:** Not yet buildable — project scaffolded, build pending. See
PLAN.md and voidfinder-fable-brief.md.
