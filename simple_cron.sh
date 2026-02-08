#!/bin/bash

# JEDNOSTAVAN CRON ZA SVE PRODAVNICE
# Poziva admin panel runScraper sa all_stores

# Log file
LOG_FILE="/var/www/dataFlow/logs/simple_cron_$(date +'%Y%m%d_%H%M%S').log"
mkdir -p /var/www/dataFlow/logs

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== JEDNOSTAVAN CRON STARTED ==="
log "Pozivam Laravel runScraper sa all_stores..."

# Set proper working directory
cd /var/www/dataFlow

# Pozovi Laravel Artisan command ili direktno HTTP poziv
if [ -f "/var/www/dataFlow/venv/bin/python" ]; then
    PYTHON_CMD="/var/www/dataFlow/venv/bin/python"
    log "Koristim venv python: $PYTHON_CMD"
else
    PYTHON_CMD="python3"
    log "Koristim system python: $PYTHON_CMD"
fi

# JEDNOSTAVNO: Direktno pozovi ultra-parallel scraper (kao runScraper sa all_stores)
SCRIPT="/var/www/dataFlow/python_scraper/run_ultra_scraper.py"
CMD="$PYTHON_CMD $SCRIPT --ultra-parallel"

log "Pokretam: $CMD"

# Set environment variables (kao u runScraper metodi)
export PYTHONIOENCODING=utf-8
export PYTHONLEGACYWINDOWSSTDIO=1
export PYTHONUNBUFFERED=1
export DISPLAY=:99
export PATH=/var/www/dataFlow/venv/bin:$PATH

# Pokreni scraper (ekvivalent runScraper->all_stores)
$CMD 2>&1 | tee -a "$LOG_FILE"

SCRAPER_EXIT_CODE=$?

if [ $SCRAPER_EXIT_CODE -eq 0 ]; then
    log "Scraper completed successfully"
else
    log "Scraper failed with exit code: $SCRAPER_EXIT_CODE"
fi

# Cleanup old logs (keep last 30 days)
find /var/www/dataFlow/logs -name "simple_cron_*.log" -mtime +30 -delete 2>/dev/null

log "=== JEDNOSTAVAN CRON FINISHED ==="

exit $SCRAPER_EXIT_CODE