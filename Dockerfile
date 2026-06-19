FROM python:3.12-slim

# Don't write .pyc files or buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer-cached separately from source)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .


EXPOSE 5000

CMD ["gunicorn", "app:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
