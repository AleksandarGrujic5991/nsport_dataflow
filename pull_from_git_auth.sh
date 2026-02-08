#!/bin/bash

# Git Pull Script with Authentication for dataFlow project
# Usage: ./pull_from_git_auth.sh

# GitHub credentials
GITHUB_USER="AleksandarGrujic5991"
GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
REPO_URL="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/AleksandarGrujic5991/dataFlow.git"

echo "🔄 Starting Authenticated Git Pull..."
echo "📍 Repository: AleksandarGrujic5991/dataFlow"
echo "👤 User: $GITHUB_USER"
echo "📍 Current directory: $(pwd)"

# Navigate to project directory
cd /var/www/dataFlow

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    
    # If not a git repo, clone it
    echo "🔄 Cloning repository..."
    cd /var/www/
    git clone $REPO_URL dataFlow
    cd dataFlow
    
    # Set up venv if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "🐍 Creating Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    fi
    
    echo "✅ Repository cloned successfully!"
    exit 0
fi

# Update remote URL to use token
git remote set-url origin $REPO_URL

# Show current status
echo "📊 Current Git Status:"
git status --porcelain

# Show current branch and commit
echo "🌿 Current branch: $(git branch --show-current)"
echo "📝 Current commit: $(git rev-parse --short HEAD)"

# Fetch latest changes
echo "🔍 Fetching latest changes..."
git fetch origin master

# Check if there are changes to pull
BEHIND=$(git rev-list --count HEAD..origin/master)
if [ $BEHIND -eq 0 ]; then
    echo "✅ Already up to date"
    exit 0
fi

# Show what will be pulled
echo "📈 $BEHIND commits to be pulled:"
git log --oneline HEAD..origin/master

# Pull the changes
echo "⬇️ Pulling changes from origin/master..."
git pull origin master

if [ $? -eq 0 ]; then
    echo "✅ Git pull successful!"
    
    # Show new commit
    echo "📝 New commit: $(git rev-parse --short HEAD)"
    
    # Check if Python requirements changed
    if git diff --name-only HEAD@{1} HEAD | grep -q "requirements.txt"; then
        echo "📦 Requirements.txt changed - installing new packages..."
        source venv/bin/activate
        pip install -r requirements.txt
        echo "✅ Python packages updated"
    fi
    
    # Check if any Python files changed
    if git diff --name-only HEAD@{1} HEAD | grep -q "\.py$"; then
        echo "🐍 Python files changed"
        
        # Test basic import
        echo "🧪 Testing basic import..."
        source venv/bin/activate
        cd python_scraper
        python -c "from run_ultra_scraper import UltraScraperOrchestrator; print('✅ Import test passed')" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "✅ Python scraper is working"
        else
            echo "❌ Python scraper has issues - check manually"
        fi
    fi
    
    # Clear any existing log files
    echo "🧹 Cleaning up old log files..."
    find . -name "*.log" -type f -delete 2>/dev/null
    find . -name "debug_*.html" -type f -delete 2>/dev/null
    find . -name "*_universal_cat*.json" -type f -delete 2>/dev/null
    
    echo "🎉 Deployment completed successfully!"
    
else
    echo "❌ Git pull failed!"
    exit 1
fi