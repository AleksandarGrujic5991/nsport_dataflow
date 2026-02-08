#!/bin/bash

# Cron wrapper for Ultra Scraper - TEST mode
# Runs scrapers in test mode for quick validation

# Set proper working directory  
cd /var/www/dataFlow

# Log file with timestamp
LOG_FILE="/var/www/dataFlow/logs/cron_test_$(date +'%Y%m%d_%H%M%S').log"
mkdir -p /var/www/dataFlow/logs

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== CRON TEST SCRAPER STARTED ==="
log "Log file: $LOG_FILE"

# Check environment
if [ -f "/var/www/dataFlow/venv/bin/python" ]; then
    PYTHON_CMD="/var/www/dataFlow/venv/bin/python"
    log "✅ Using venv python"
else
    PYTHON_CMD="python3"
    log "⚠️ Using system python"
fi

# Set environment
export PYTHONPATH="/var/www/dataFlow:$PYTHONPATH"
export PYTHONUNBUFFERED=1

log "🧪 Starting test mode scraper..."

# Run in test mode
$PYTHON_CMD /var/www/dataFlow/python_scraper/run_ultra_scraper.py --test 2>&1 | tee -a "$LOG_FILE"

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    log "✅ Test scraper completed successfully"
else
    log "❌ Test scraper failed with exit code: $TEST_EXIT_CODE"
fi

log "=== CRON TEST SCRAPER FINISHED ==="

exit $TEST_EXIT_CODE