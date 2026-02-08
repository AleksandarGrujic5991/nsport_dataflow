#!/bin/bash

# Simple Git Pull Script
echo "🔄 Git Pull..."

cd /var/www/dataFlow
git config user.name "AleksandarGrujic5991"
git config credential.helper store
echo "https://AleksandarGrujic5991:YOUR_GITHUB_TOKEN@github.com" > ~/.git-credentials
git pull origin master

echo "✅ Done!"