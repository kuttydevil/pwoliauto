#!/bin/bash

# NetHunter / Termux Auto-Start Script for NetHunter Core
# This script initializes the environment, installs dependencies, and starts the dashboard.

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}   NETHUNTER CORE - AUTO INITIALIZER     ${NC}"
echo -e "${BLUE}=========================================${NC}"

# 1. Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}[!] Node.js not found. Installing...${NC}"
    pkg install nodejs -y
fi

# 2. Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[!] Python3 not found. Installing...${NC}"
    pkg install python -y
fi

# 3. Check for Chromium (needed for the bot)
if ! command -v chromium &> /dev/null; then
    echo -e "${RED}[!] Chromium not found. Installing...${NC}"
    pkg install chromium -y
fi

# 4. Check for Cloudflared (for remote access)
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}[!] Cloudflared not found. Installing for remote access...${NC}"
    pkg install cloudflared -y
fi

# 5. Install Node dependencies
echo -e "${GREEN}[*] Installing Node.js dependencies...${NC}"
npm install

# 6. Create necessary directories
echo -e "${GREEN}[*] Preparing workspace...${NC}"
mkdir -p bot_repo
mkdir -p bot_repo/core
mkdir -p bot_repo/scraper
mkdir -p bot_repo/services
mkdir -p bot_repo/utils
mkdir -p bot_repo/accounts_data
mkdir -p bot_repo/promotion_images

# 7. Start Remote Tunnel in background
echo -e "${BLUE}[*] Initializing Secure Remote Tunnel...${NC}"
cloudflared tunnel --url http://localhost:3000 > .tunnel.log 2>&1 &
sleep 5
TUNNEL_URL=$(grep -o 'https://[-a-z0-9.]*trycloudflare.com' .tunnel.log | head -n 1)

# 8. Start the Dashboard
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}[+] Initialization Complete!${NC}"
echo -e "${GREEN}[+] Local: http://localhost:3000${NC}"
if [ ! -z "$TUNNEL_URL" ]; then
    echo -e "${GREEN}[+] Remote: $TUNNEL_URL${NC}"
    echo "$TUNNEL_URL" > .remote_url
else
    echo -e "${RED}[!] Remote Tunnel failed to start. Check .tunnel.log${NC}"
fi
echo -e "${BLUE}=========================================${NC}"

# Run the server
npm run dev
