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
sudo apt-get install -y python3-venv python3-pip mariadb-server python3-dev libffi-dev

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
echo "Please enter your MySQL root password to continue."
read -s MYSQL_ROOT_PASSWORD

# Check if database exists
DB_EXISTS=$(sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "SHOW DATABASES LIKE 'FingerprintDB';" | grep -c FingerprintDB || true)

if [ $DB_EXISTS -eq 0 ]; then
    echo "Creating database and tables from schema.sql..."
    sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" < schema.sql
    echo "Database 'FingerprintDB' and tables created."
else
    echo "Database 'FingerprintDB' already exists. Skipping creation."
fi

print_step "Step 6: Creating dedicated MySQL user..."

# Create a dedicated DB user
echo "Please create a password for the new database user (fingerprint_user)."
read -s DB_PASSWORD

# Check if user exists
USER_EXISTS=$(sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "SELECT User FROM mysql.user WHERE User = 'fingerprint_user' AND Host = 'localhost';" | grep -c fingerprint_user || true)

if [ $USER_EXISTS -eq 0 ]; then
    sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER 'fingerprint_user'@'localhost' IDENTIFIED BY '$DB_PASSWORD';"
    sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON FingerprintDB.* TO 'fingerprint_user'@'localhost';"
    sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "FLUSH PRIVILEGES;"
    echo "User 'fingerprint_user' created and granted privileges."
else
    echo "User 'fingerprint_user' already exists. Skipping creation."
fi

print_step "Step 7: Creating .env configuration file..."

# Collect SMTP credentials
echo "Please enter your SMTP username (email address):"
read SMTP_USERNAME
echo "Please enter your SMTP password:"
read -s SMTP_PASSWORD

SECRET_KEY=$(python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
)

cat > .env <<EOF
# Flask Configuration
SECRET_KEY=$SECRET_KEY
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=fingerprint_user
DB_PASSWORD=$DB_PASSWORD
DB_NAME=FingerprintDB
DB_POOL_SIZE=5

# Cookie Configuration
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax

# Email Configuration
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=$SMTP_USERNAME
SMTP_PASSWORD=$SMTP_PASSWORD
EOF

echo ".env file created with new credentials."

print_step "Step 8: Setting up cron job for daily reports..."
PROJECT_DIR=$(pwd)
CRON_CMD="0 11 * * * cd $PROJECT_DIR && $PROJECT_DIR/.venv/bin/python $PROJECT_DIR/daily_report_sender.py >> $PROJECT_DIR/cron.log 2>&1"
(crontab -l 2>/dev/null | grep -v -F "$PROJECT_DIR/daily_report_sender.py" ; echo "$CRON_CMD") | crontab -

echo "Cron job added to run daily at 11 AM."

print_step "Step 9: Configuring git safe directory..."
CURRENT_USER=$(whoami)
PROJECT_DIR=$(pwd)

sudo -u $CURRENT_USER git config --global --add safe.directory $PROJECT_DIR

echo "Git safe directory configured."

print_step "Step 10: Setting up systemd service (single service) for the web app..."
SERVICE_NAME="fingerprint-web.service"
cat > fingerprint-web.service <<EOF
[Unit]
Description=Fingerprint Web App
After=network.target mysql.service

[Service]
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python wsgi.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo mv fingerprint-web.service /etc/systemd/system/fingerprint-web.service

print_step "Step 11: Enabling and starting the service..."

sudo systemctl daemon-reload
sudo systemctl enable fingerprint-web.service
sudo systemctl start fingerprint-web.service

print_step "Setup Complete!"
echo -e "\n\033[1;32mYour Raspberry Pi is now set up to run the Fingerprint System as a service.\033[0m"
echo "You can check the status of the service with:"
echo "sudo systemctl status fingerprint-web.service"
