FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
COPY app/ /app/app/
RUN pip install --no-cache-dir .
COPY assets/ /app/assets/
COPY wsgi.py /app/
EXPOSE 8050
CMD ["gunicorn", "wsgi:server", "--bind", "0.0.0.0:8050", "--workers", "2", "--timeout", "120"]
