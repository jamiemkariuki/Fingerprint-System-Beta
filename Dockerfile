FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    default-libmysqlclient-dev \
    python3-dev \
    ca-certificates \
    pigpio \
    python3-pigpio \
    python3-rpi.gpio \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Create a virtual environment and install dependencies
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Add entrypoint script for GPIO wiring
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY . .

EXPOSE 5000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "wsgi:application"]