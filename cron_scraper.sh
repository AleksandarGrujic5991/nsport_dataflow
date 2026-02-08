#!/bin/bash

# Cron wrapper for Ultra Scraper - Full automated run
# Runs all scrapers in ultra-parallel mode

# Set proper working directory
cd /var/www/dataFlow

# Log file with timestamp
LOG_FILE="/var/www/dataFlow/logs/cron_scraper_$(date +'%Y%m%d_%H%M%S').log"
mkdir -p /var/www/dataFlow/logs

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== CRON SCRAPER STARTED ==="
log "Log file: $LOG_FILE"
log "Working directory: $(pwd)"
log "Python environment: $(which python)"

# Check if venv exists
if [ -f "/var/www/dataFlow/venv/bin/python" ]; then
    log "✅ Virtual environment found"
    PYTHON_CMD="/var/www/dataFlow/venv/bin/python"
else
    log "⚠️ Virtual environment not found, using system python"
    PYTHON_CMD="python3"
fi

# Check if main script exists
if [ -f "/var/www/dataFlow/python_scraper/run_ultra_scraper.py" ]; then
    log "✅ Main scraper script found"
else
    log "❌ Main scraper script not found!"
    exit 1
fi

# Set environment variables
export PYTHONPATH="/var/www/dataFlow:$PYTHONPATH"
export PYTHONUNBUFFERED=1

log "🚀 Starting ultra-parallel scraper for all stores..."

# Run the scraper with full logging
$PYTHON_CMD /var/www/dataFlow/python_scraper/run_ultra_scraper.py --ultra-parallel 2>&1 | tee -a "$LOG_FILE"

SCRAPER_EXIT_CODE=$?

if [ $SCRAPER_EXIT_CODE -eq 0 ]; then
    log "✅ Scraper completed successfully"
else
    log "❌ Scraper failed with exit code: $SCRAPER_EXIT_CODE"
fi

# Cleanup old logs (keep last 30 days)
find /var/www/dataFlow/logs -name "cron_scraper_*.log" -mtime +30 -delete 2>/dev/null

log "=== CRON SCRAPER FINISHED ==="
log "Total execution time: $(date +'%Y-%m-%d %H:%M:%S')"

exit $SCRAPER_EXIT_CODE