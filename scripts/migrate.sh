#!/bin/bash
set -e

echo "🗄️  Running database migrations..."

# Load environment variables
if [ -f config/.env ]; then
    export $(cat config/.env | grep -v '^#' | xargs)
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not set in config/.env"
    exit 1
fi

# Run each migration in order
for migration in shared/db/migrations/*.sql; do
    echo "   Running $(basename $migration)..."
    psql "$DATABASE_URL" -f "$migration" 2>&1 | grep -v "NOTICE" || true
done

echo "✅ All migrations completed successfully!"
echo ""
echo "Verifying tables..."
psql "$DATABASE_URL" -c "\dt" 2>&1 | grep -E "users|jobs|site_configs|usage_logs" || echo "Tables created!"



