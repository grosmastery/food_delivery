FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home app \
    && mkdir -p /app/media /app/static_files \
    && chown app:app /app/media /app/static_files

COPY . .

USER app

EXPOSE 8009

CMD ["daphne", "-b", "0.0.0.0", "-p", "8009", "food_delivery.asgi:application"]
