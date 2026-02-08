#!/bin/bash

# Install script for Ultra Scraper Cron Jobs
# This script sets up automated scraping with crontab

echo "🔧 Installing Ultra Scraper Cron Jobs..."

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ] && [ -z "$SUDO_USER" ]; then
    echo "⚠️  You may need to run with sudo for proper permissions"
fi

# Set proper working directory
cd /var/www/dataFlow

# Create logs directory
mkdir -p /var/www/dataFlow/logs
echo "✅ Created logs directory"

# Make scripts executable
chmod +x /var/www/dataFlow/cron_scraper.sh
chmod +x /var/www/dataFlow/cron_scraper_test.sh
echo "✅ Made scripts executable"

# Backup existing crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Backed up existing crontab"
else
    echo "ℹ️  No existing crontab found"
fi

# Install new crontab
crontab /var/www/dataFlow/crontab_scraper
if [ $? -eq 0 ]; then
    echo "✅ Installed scraper crontab"
else
    echo "❌ Failed to install crontab"
    exit 1
fi

# Show installed cron jobs
echo ""
echo "📋 Installed cron jobs:"
crontab -l

echo ""
echo "🎉 Ultra Scraper Cron Jobs installed successfully!"
echo ""
echo "📅 Schedule:"
echo "   - 02:00 (2 AM) - Full scraper"
echo "   - 10:00 (10 AM) - Full scraper"  
echo "   - 14:00 (2 PM) - Full scraper"
echo "   - 18:00 (6 PM) - Full scraper"
echo ""
echo "📁 Log files will be saved to: /var/www/dataFlow/logs/"
echo ""
echo "🔍 To monitor:"
echo "   tail -f /var/www/dataFlow/logs/cron_scraper_*.log"
echo ""
echo "🧪 To test manually:"
echo "   /var/www/dataFlow/cron_scraper_test.sh"
echo ""
echo "🗑️  To remove cron jobs:"
echo "   crontab -r"
echo ""

# Test the setup
echo "🧪 Running test scraper to verify setup..."
/var/www/dataFlow/cron_scraper_test.sh

echo "✅ Setup complete!"