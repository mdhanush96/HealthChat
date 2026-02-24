#!/usr/bin/env bash
# HealthChat – Quick start script
# Run from the repository root: bash run_backend.sh
set -e

echo "==> Starting HealthChat Django backend on http://127.0.0.1:8000"
cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found. Copy .env.example to .env and configure your database credentials."
fi

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
