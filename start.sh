#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Helper Functions ---
print_step() {
    echo -e "\n\033[1;36m$1\033[0m"
}

# --- Main Script ---

print_step "Step 1: Fetching and pulling latest changes from git..."
git fetch --all
git pull

print_step "Step 2: Activating virtual environment..."
source .venv/bin/activate

print_step "Step 3: Starting the application..."

nohup python wsgi.py > flask_app.log 2>&1 &
nohup python fingerprint_listener.py > fingerprint_listener.log 2>&1 &

echo -e "\n\033[1;32mThe web application and fingerprint listener have been started in the background.\033[0m"
echo "You can view their logs in flask_app.log and fingerprint_listener.log"
