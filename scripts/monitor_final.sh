#!/bin/bash

# Final monitoring script for GitHub Actions
REPO="haydentwestbrook/kindle-sync"
RUN_ID="18416527428"

echo "🔍 GitHub Actions Workflow Monitor"
echo "📋 Repository: $REPO"
echo "🆔 Run ID: $RUN_ID"
echo "🌐 Web URL: https://github.com/$REPO/actions/runs/$RUN_ID"
echo ""

while true; do
    echo "⏰ $(date): Checking workflow status..."

    # Get workflow status
    WORKFLOW_DATA=$(curl -s "https://api.github.com/repos/$REPO/actions/runs/$RUN_ID")
    STATUS=$(echo "$WORKFLOW_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['status'])")
    CONCLUSION=$(echo "$WORKFLOW_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['conclusion'] if data['conclusion'] else 'None')")
    UPDATED=$(echo "$WORKFLOW_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['updated_at'])")

    echo "📊 Overall Status: $STATUS"
    if [ "$CONCLUSION" != "None" ]; then
        echo "✅ Conclusion: $CONCLUSION"
    fi
    echo "🕒 Last Updated: $UPDATED"
    echo ""

    # Get job statuses
    echo "📋 Job Status:"
    JOBS_DATA=$(curl -s "https://api.github.com/repos/$REPO/actions/runs/$RUN_ID/jobs")
    echo "$JOBS_DATA" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for job in data['jobs']:
    conclusion = job['conclusion'] if job['conclusion'] else 'running'
    status_icon = '✅' if job['conclusion'] == 'success' else '❌' if job['conclusion'] == 'failure' else '⏳'
    print(f'  {status_icon} {job[\"name\"]}: {job[\"status\"]} ({conclusion})')
"

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

    echo ""
    echo "⏳ Workflow still running... checking again in 30 seconds"
    echo "----------------------------------------"
    sleep 30
done
