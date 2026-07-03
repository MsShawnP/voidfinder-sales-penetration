FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
COPY app/ /app/app/
RUN pip install --no-cache-dir .
COPY assets/ /app/assets/
COPY wsgi.py /app/
EXPOSE 8050
# One worker: each worker holds the full ~1.3M-row scans frame, and two
# of them OOMed the 1024MB VM (SIGKILL loops on first deploy — same
# failure Spin Rate hit). A second worker also made /ready flap, since
# each worker answers with its own load state.
CMD ["gunicorn", "wsgi:server", "--bind", "0.0.0.0:8050", "--workers", "1", "--timeout", "120"]
