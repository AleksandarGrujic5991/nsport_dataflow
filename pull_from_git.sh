#!/bin/bash

# Git Pull Script for dataFlow project
# Usage: ./pull_from_git.sh

echo "🔄 Starting Git Pull..."
echo "📍 Repository: AleksandarGrujic5991/dataFlow"
echo "📍 Current directory: $(pwd)"

# Navigate to project directory
cd /var/www/dataFlow

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Show current status
echo "📊 Current Git Status:"
git status --porcelain

# Show current branch and commit
echo "🌿 Current branch: $(git branch --show-current)"
echo "📝 Current commit: $(git rev-parse --short HEAD)"

# Fetch latest changes
echo "🔍 Fetching latest changes..."
git fetch origin master

# Show what will be pulled
echo "📈 Commits to be pulled:"
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
        python -c "from run_ultra_scraper import UltraScraperOrchestrator; print('✅ Import test passed')"
        
        if [ $? -eq 0 ]; then
            echo "✅ Python scraper is working"
        else
            echo "❌ Python scraper has issues - check manually"
        fi
    fi
    
    echo "🎉 Deployment completed successfully!"
    
else
    echo "❌ Git pull failed!"
    exit 1
fi