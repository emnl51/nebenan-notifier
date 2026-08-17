FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/data/app.db
ENV STORAGE_STATE_PATH=/app/data/storage_state.json

EXPOSE 5000

CMD ["python", "app/main.py"]
