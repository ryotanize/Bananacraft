#!/bin/bash
set -e

echo "🍌 Bananacraft GCE Setup Script"

# 1. Update System
echo "Updating system..."
sudo apt-get update
sudo apt-get install -y git python3-pip python3-venv openjdk-17-jre-headless screen curl

# Install Node.js 22
echo "Installing Node.js 22..."
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# 2. Setup Python Environment
echo "Setting up Python..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Setup Node.js Environment (AI Carpenter & Tools)
echo "Setting up AI Carpenter..."
cd AI_Carpenter_Bot
npm install
cd ..

# 4. Setup Directories
mkdir -p projects

echo "✅ Setup Complete!"
echo "Please configure .env file and place 'server.jar' in a separate directory if needed."
