#!/bin/bash

# Monitor GitHub Actions workflow for kindle-sync repository
REPO="haydentwestbrook/kindle-sync"
RUN_ID="18416527428"

echo "🔍 Monitoring GitHub Actions workflow for $REPO"
echo "📋 Run ID: $RUN_ID"
echo "🌐 Web URL: https://github.com/$REPO/actions/runs/$RUN_ID"
echo ""

while true; do
    echo "⏰ $(date): Checking workflow status..."
    
    # Get workflow status
    STATUS=$(curl -s "https://api.github.com/repos/$REPO/actions/runs/$RUN_ID" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    CONCLUSION=$(curl -s "https://api.github.com/repos/$REPO/actions/runs/$RUN_ID" | grep -o '"conclusion":"[^"]*"' | cut -d'"' -f4)
    
    echo "📊 Status: $STATUS"
    if [ "$CONCLUSION" != "null" ] && [ -n "$CONCLUSION" ]; then
        echo "✅ Conclusion: $CONCLUSION"
    fi
    
    # Check if workflow is complete
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "🎉 Workflow completed with conclusion: $CONCLUSION"
        
        if [ "$CONCLUSION" = "success" ]; then
            echo "✅ All tests passed successfully!"
        else
            echo "❌ Workflow failed. Check the logs for details."
        fi
        
        echo "🌐 View full results at: https://github.com/$REPO/actions/runs/$RUN_ID"
        break
    fi
    
    echo "⏳ Workflow still running... checking again in 30 seconds"
    echo "----------------------------------------"
    sleep 30
done
