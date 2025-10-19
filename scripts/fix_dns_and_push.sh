#!/bin/bash

echo "🔧 DNS Fix and Git Push Script"
echo "=============================="
echo ""

# Backup current DNS config
echo "📋 Backing up current DNS config..."
sudo cp /etc/resolv.conf /etc/resolv.conf.backup
echo "✅ DNS config backed up to /etc/resolv.conf.backup"
echo ""

# Set Google DNS servers
echo "📋 Setting Google DNS servers..."
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf
echo "✅ DNS servers updated"
echo ""

# Test DNS resolution
echo "📋 Testing DNS resolution..."
if ping -c 2 github.com >/dev/null 2>&1; then
    echo "✅ DNS resolution working - github.com is reachable"
else
    echo "❌ DNS resolution still failing"
    exit 1
fi
echo ""

# Change back to SSH remote (if needed)
echo "📋 Setting git remote to SSH..."
git remote set-url origin git@github.com:haydentwestbrook/kindle-sync.git
echo "✅ Git remote set to SSH"
echo ""

# Push to GitHub
echo "📋 Pushing to GitHub..."
if git push origin main; then
    echo "✅ Successfully pushed to GitHub!"
    echo ""
    echo "🎉 All changes have been pushed successfully!"
    echo "📋 Commits pushed:"
    git log --oneline -5
else
    echo "❌ Git push failed"
    echo "📋 Current git status:"
    git status
    exit 1
fi

echo ""
echo "📋 Restoring original DNS config (optional)..."
echo "To restore original DNS: sudo cp /etc/resolv.conf.backup /etc/resolv.conf"
