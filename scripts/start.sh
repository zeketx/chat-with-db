#!/bin/bash

GREEN=$'\033[0;32m'
BLUE=$'\033[0;34m'
RED=$'\033[0;31m'
NC=$'\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"
TIMEOUT=${1:-0}

printf "${BLUE}Starting chat-with-db...${NC}\n"

# Check for .env
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    printf "${RED}Error: No .env file found in project root.${NC}\n"
    echo "Run: cp .env.example .env  then add your OPENAI_API_KEY and DB_URL"
    exit 1
fi

# Activate venv if present and not already active
if [ -z "$VIRTUAL_ENV" ] && [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

cleanup() {
    printf "\n${BLUE}Shutting down...${NC}\n"
    jobs -p | xargs kill 2>/dev/null
    wait
    printf "${GREEN}Stopped.${NC}\n"
    exit 0
}

trap cleanup EXIT INT TERM

printf "${GREEN}Starting FastAPI server...${NC}\n"
cd "$PROJECT_ROOT"
python main.py &
SERVER_PID=$!

sleep 2

if ! kill -0 $SERVER_PID 2>/dev/null; then
    printf "${RED}Server failed to start!${NC}\n"
    exit 1
fi

printf "${GREEN}✓ Server running${NC}\n"
printf "${BLUE}API:      http://localhost:8000${NC}\n"
printf "${BLUE}API Docs: http://localhost:8000/docs${NC}\n"
echo ""

if [ "$TIMEOUT" != "0" ]; then
    SECS=$(echo "$TIMEOUT" | sed 's/s$//')
    echo "Running for ${TIMEOUT}, then stopping..."
    sleep "$SECS"
else
    echo "Press Ctrl+C to stop..."
    wait
fi
