#!/usr/bin/env bash
# HealthChat – Streamlit frontend start script
# Run from the repository root: bash run_frontend.sh
set -e

echo "==> Starting HealthChat Streamlit frontend on http://localhost:8501"
cd "$(dirname "$0")"

streamlit run frontend/app.py --server.port 8501 --server.address localhost
