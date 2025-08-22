#!/bin/bash
# Script to clean up old GitHub Actions runs

echo "🧹 GitHub Actions Cleanup Script"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to delete runs by status
delete_runs_by_status() {
    local status=$1
    local limit=${2:-50}

    echo -e "${YELLOW}Finding $status runs to delete (limit: $limit)...${NC}"

    run_ids=$(gh run list --limit $limit --json databaseId,status,conclusion,createdAt \
        --jq ".[] | select(.conclusion == \"$status\") | .databaseId")

    if [ -z "$run_ids" ]; then
        echo -e "${GREEN}No $status runs found to delete.${NC}"
        return
    fi

    count=$(echo "$run_ids" | wc -l | tr -d ' ')
    echo -e "${YELLOW}Found $count $status runs to delete${NC}"

    echo "$run_ids" | while read -r id; do
        echo -n "Deleting run $id... "
        if gh run delete $id 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    done
}

# Function to delete old runs
delete_old_runs() {
    local days=${1:-30}

    echo -e "${YELLOW}Finding runs older than $days days...${NC}"

    cutoff_date=$(date -v-${days}d +%Y-%m-%d 2>/dev/null || date -d "$days days ago" +%Y-%m-%d)

    run_ids=$(gh run list --limit 200 --json databaseId,createdAt \
        --jq ".[] | select(.createdAt < \"$cutoff_date\") | .databaseId")

    if [ -z "$run_ids" ]; then
        echo -e "${GREEN}No runs older than $days days found.${NC}"
        return
    fi

    count=$(echo "$run_ids" | wc -l | tr -d ' ')
    echo -e "${YELLOW}Found $count runs older than $days days${NC}"

    echo "$run_ids" | while read -r id; do
        echo -n "Deleting run $id... "
        if gh run delete $id 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    done
}

# Main menu
echo ""
echo "What would you like to clean up?"
echo "1) Delete all failed runs"
echo "2) Delete all cancelled runs"
echo "3) Delete runs older than 30 days"
echo "4) Delete runs older than 7 days"
echo "5) Delete ALL except last 10 successful runs"
echo "6) Show statistics only (no deletion)"
echo "0) Exit"
echo ""
read -p "Enter your choice (0-6): " choice

case $choice in
    1)
        delete_runs_by_status "failure" 100
        ;;
    2)
        delete_runs_by_status "cancelled" 100
        ;;
    3)
        delete_old_runs 30
        ;;
    4)
        delete_old_runs 7
        ;;
    5)
        echo -e "${RED}⚠️  WARNING: This will delete ALL runs except the last 10 successful ones!${NC}"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            # Keep last 10 successful runs
            keep_ids=$(gh run list --limit 10 --json databaseId,conclusion \
                --jq '.[] | select(.conclusion == "success") | .databaseId')

            # Get all run IDs
            all_ids=$(gh run list --limit 200 --json databaseId --jq '.[].databaseId')

            # Delete everything except the ones to keep
            echo "$all_ids" | while read -r id; do
                if ! echo "$keep_ids" | grep -q "^$id$"; then
                    echo -n "Deleting run $id... "
                    if gh run delete $id 2>/dev/null; then
                        echo -e "${GREEN}✓${NC}"
                    else
                        echo -e "${RED}✗${NC}"
                    fi
                fi
            done
        else
            echo "Cancelled."
        fi
        ;;
    6)
        echo -e "${YELLOW}GitHub Actions Statistics:${NC}"
        echo ""

        total=$(gh run list --limit 200 --json databaseId | jq '. | length')
        successful=$(gh run list --limit 200 --json conclusion --jq '[.[] | select(.conclusion == "success")] | length')
        failed=$(gh run list --limit 200 --json conclusion --jq '[.[] | select(.conclusion == "failure")] | length')
        cancelled=$(gh run list --limit 200 --json conclusion --jq '[.[] | select(.conclusion == "cancelled")] | length')

        echo "Total runs (last 200): $total"
        echo -e "${GREEN}Successful: $successful${NC}"
        echo -e "${RED}Failed: $failed${NC}"
        echo -e "${YELLOW}Cancelled: $cancelled${NC}"

        echo ""
        echo "Storage usage:"
        gh api /repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions/cache/usage | jq
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice!${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"
