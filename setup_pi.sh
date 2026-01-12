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

print_step "Containerization notice"
echo "For containerized deployment instructions, refer to README.md."
echo "No systemd service will be configured in this script."

# GPIO support for Raspberry Pi
print_step "Step GPIO: Configuring Raspberry Pi GPIO (pigpio, UART, and permissions)"

# Detect Raspberry Pi environment; adapt gracefully if not present
if [ -f /etc/os-release ] && (grep -qi 'raspbian' /etc/os-release || grep -qi 'raspberry' /etc/os-release); then
  echo "Configuring GPIO for Raspberry Pi..."
  print_step "Installing GPIO libraries (pigpio, Python bindings)"
  sudo apt-get update
  sudo apt-get install -y pigpio python3-pigpio python3-rpi.gpio

  print_step "Starting pigpio daemon"
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl enable --now pigpiod || true
  else
    if command -v pigpiod >/dev/null 2>&1; then
      sudo pigpiod
    fi
  fi

  print_step "Adding current user to dialout group for serial access"
  CURRENT_USER=$(whoami)
  sudo usermod -a -G dialout $CURRENT_USER

  print_step "Enabling UART and disabling serial console in boot config"
  if [ -f /boot/config.txt ]; then
    grep -q '^enable_uart=1' /boot/config.txt || echo 'enable_uart=1' | sudo tee -a /boot/config.txt
  fi
  if [ -f /boot/cmdline.txt ]; then
    sudo sed -i 's/ console=serial0,115200//g' /boot/cmdline.txt
    sudo sed -i 's/console=ttyS0,115200//g' /boot/cmdline.txt
  fi

  print_step "GPIO setup complete"
else
  echo "GPIO setup skipped (not running on Raspberry Pi)."
fi
