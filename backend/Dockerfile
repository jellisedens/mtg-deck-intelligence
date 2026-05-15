FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Use --reload only in dev (controlled by ENVIRONMENT var)
CMD ["sh", "-c", "if [ \"$APP_ENV\" = 'development' ]; then uvicorn main:app --host 0.0.0.0 --port 8000 --reload; else uvicorn main:app --host 0.0.0.0 --port 8000; fi"]