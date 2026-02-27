FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd -m -u 1000 bridge-1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=bridge-1:bridge-1 src/ ./src

USER bridge-1

EXPOSE 7004

CMD ["uvicorn", "bridge:app", "--host", "0.0.0.0", "--port", "7004", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*", "--log-level", "info"]
