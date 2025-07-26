#!/bin/bash

############################################################################
# Container Entrypoint script
############################################################################

if [[ "$PRINT_ENV_ON_LOAD" = true || "$PRINT_ENV_ON_LOAD" = True ]]; then
  echo "=================================================="
  printenv
  echo "=================================================="
fi

if [[ "$WAIT_FOR_DB" = true || "$WAIT_FOR_DB" = True ]]; then
  dockerize \
    -wait tcp://$DB_HOST:$DB_PORT \
    -timeout 300s
  
  echo "Database is ready, running migrations..."
  # Run YouTube database migrations
  if python -c "
import sys
try:
    from db.migrations import create_tables, check_tables_exist
    tables_status = check_tables_exist()
    if tables_status and not all(tables_status.values()):
        print('Creating missing YouTube tables...')
        success = create_tables()
        if success:
            print('✅ YouTube database migration completed!')
        else:
            print('❌ YouTube database migration failed!')
            sys.exit(1)
    else:
        print('✅ All YouTube tables exist or database check failed')
except Exception as e:
    print(f'Migration check failed: {e}')
    # Don't fail the container if migration check fails
"; then
    echo "✅ Migration check completed"
  else
    echo "⚠️ Migration check had issues, but continuing..."
  fi
fi

############################################################################
# Start App
############################################################################

case "$1" in
  chill)
    ;;
  *)
    echo "Running: $@"
    exec "$@"
    ;;
esac

echo ">>> Hello World!"
while true; do sleep 18000; done
