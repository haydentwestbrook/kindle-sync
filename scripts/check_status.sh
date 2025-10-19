#!/bin/bash

# Quick status check for GitHub Actions workflow
REPO="haydentwestbrook/kindle-sync"
RUN_ID="18416527428"

echo "🔍 GitHub Actions Status Check"
echo "📋 Repository: $REPO"
echo "🆔 Run ID: $RUN_ID"
echo "🌐 Web URL: https://github.com/$REPO/actions/runs/$RUN_ID"
echo ""

# Get workflow status
STATUS=$(curl -s "https://api.github.com/repos/$REPO/actions/runs/$RUN_ID" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
CONCLUSION=$(curl -s "https://api.github.com/repos/$REPO/actions/runs/$RUN_ID" | grep -o '"conclusion":"[^"]*"' | cut -d'"' -f4)
UPDATED=$(curl -s "https://api.github.com/repos/$REPO/actions/runs/$RUN_ID" | grep -o '"updated_at":"[^"]*"' | cut -d'"' -f4)

echo "📊 Status: $STATUS"
if [ "$CONCLUSION" != "null" ] && [ -n "$CONCLUSION" ]; then
    echo "✅ Conclusion: $CONCLUSION"
fi
echo "🕒 Last Updated: $UPDATED"
echo ""

# Get job statuses
echo "📋 Job Status:"
curl -s "https://api.github.com/repos/$REPO/actions/runs/$RUN_ID/jobs" | grep -E '"name"|"status"|"conclusion"' | while read line; do
    if [[ $line == *"name"* ]]; then
        JOB_NAME=$(echo $line | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
        echo -n "  🔧 $JOB_NAME: "
    elif [[ $line == *"status"* ]]; then
        JOB_STATUS=$(echo $line | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        echo -n "$JOB_STATUS"
    elif [[ $line == *"conclusion"* ]]; then
        JOB_CONCLUSION=$(echo $line | grep -o '"conclusion":"[^"]*"' | cut -d'"' -f4)
        if [ "$JOB_CONCLUSION" != "null" ] && [ -n "$JOB_CONCLUSION" ]; then
            echo " ($JOB_CONCLUSION)"
        else
            echo ""
        fi
    fi
done
