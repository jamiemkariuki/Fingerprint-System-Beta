#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Helper Functions ---
print_step() {
    echo -e "\n\033[1;36m$1\033[0m"
}

# --- Main Script ---

print_step "Step 1: Updating package list..."
sudo apt-get update

print_step "Step 2: Installing system dependencies..."
# python3-dev and libffi-dev are for `cffi` which is a dependency of `bcrypt`
sudo apt-get install -y python3-venv python3-pip mysql-server python3-dev libffi-dev

print_step "Step 3: Setting up Python virtual environment..."
if [ -d ".venv" ]; then
    echo "Virtual environment .venv already exists. Skipping creation."
else
    python3 -m venv .venv
fi

print_step "Step 4: Activating virtual environment and installing Python packages..."
source .venv/bin/activate
pip install -r requirements.txt

print_step "Step 5: Setting up MySQL database..."
echo "The script will now set up the database schema."
echo "You may be prompted for your MySQL root password."

# Check if database exists
DB_EXISTS=$(sudo mysql -u root -p -e "SHOW DATABASES LIKE 'FingerprintDB';" | grep "FingerprintDB" > /dev/null; echo "$?")

if [ $DB_EXISTS -eq 0 ]; then
    echo "Database 'FingerprintDB' already exists. Skipping creation."
else
    echo "Creating database and tables from schema.sql..."
    sudo mysql -u root -p < schema.sql
    echo "Database 'FingerprintDB' and tables created."
fi

print_step "Step 6: Creating .env configuration file..."
if [ -f ".env" ]; then
    echo ".env file already exists. Skipping creation."
else
    echo "Creating a new .env file from template..."
cat > .env <<EOF
# Flask Configuration
SECRET_KEY=your-super-secret-key-here
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=fingerprint_user
DB_PASSWORD=your-strong-password-here
DB_NAME=FingerprintDB
DB_POOL_SIZE=5

# Cookie Configuration
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
EOF
    echo ".env file created. Please edit it to set your actual database credentials and a secret key."
fi

print_step "Setup Complete!"
echo -e "\n\033[1;32mYour Raspberry Pi is now set up to run the Fingerprint System.\033[0m"
echo "Next steps:"
echo "1.  Edit the .env file with a strong SECRET_KEY and your MySQL user/password."
echo "    You can create a dedicated MySQL user with this command:"
echo "    sudo mysql -u root -p -e \"CREATE USER 'fingerprint_user'@'localhost' IDENTIFIED BY 'your-strong-password-here';\""
echo "    sudo mysql -u root -p -e \"GRANT ALL PRIVILEGES ON FingerprintDB.* TO 'fingerprint_user'@'localhost';\""
echo "    sudo mysql -u root -p -e \"FLUSH PRIVILEGES;\""
echo "2.  Activate the virtual environment: source .venv/bin/activate"
echo "3.  Run the web application: python wsgi.py"
echo "4.  In a separate terminal, run the fingerprint listener: python fingerprint_listener.py"
