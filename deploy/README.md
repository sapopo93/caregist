## EC2 deploy notes

Current AWS EC2 runtime assets:

- `ecosystem.config.cjs` for the `caregist-api` PM2 process
- `deploy/nginx/api.caregist.co.uk.conf` for the API reverse proxy

Recommended deploy sequence:

1. Pull the target revision.
2. Apply migrations:
   `./.venv/bin/python db/apply_migrations.py`
3. Restart the API with updated environment:
   `pm2 restart ecosystem.config.cjs --only caregist-api --update-env`
4. Run the feed cycle once after deploy:
   `PYTHONPATH=. .venv/bin/python tools/run_new_registration_feed_cycle.py`
5. Confirm health:
   `curl -sS http://127.0.0.1:8000/api/v1/health`

Why this is repo-managed:

- The app now depends on post-launch feed migrations, including the trusted event ledger tables.
- PM2 must be restarted with `--update-env` or the API can continue serving stale configuration after a pull.
- The migration files `db/migrations/005_care_groups.sql` and `db/migrations/006_rating_changes.sql` intentionally tolerate legacy EC2 databases where older objects are owned by `postgres` rather than the application role.
