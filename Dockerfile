FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y build-essential libpq-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads and logs folders
RUN mkdir -p uploads logs

# CMD is handled by docker-compose usually, but if standalone:
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]