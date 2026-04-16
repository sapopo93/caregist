# PgBouncer Setup

PgBouncer sits between the application workers and PostgreSQL, reducing the number of actual server-side connections from `workers × pool_max_size` down to `default_pool_size`.

## Why

asyncpg holds a real Postgres connection for the lifetime of a pool slot. Under multi-worker deployments (e.g. gunicorn with 4 workers, each with `max_size=20`), that is 80 real connections. With PgBouncer in transaction mode, all 80 application slots share a pool of 50 Postgres connections, since most requests hold a connection only for milliseconds.

## Install (EC2 / Ubuntu)

```bash
sudo apt-get install -y pgbouncer
sudo cp deploy/pgbouncer/pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
sudo cp deploy/pgbouncer/userlist.txt /etc/pgbouncer/userlist.txt
```

Generate the password hash and replace the placeholder in `userlist.txt`:

```bash
psql -U postgres -c "SELECT concat('\"caregist\" \"', passwd, '\"') FROM pg_shadow WHERE usename='caregist';"
```

## Application DATABASE_URL

Point the application at PgBouncer instead of Postgres directly:

```
DATABASE_URL=postgresql://caregist:PASSWORD@127.0.0.1:6432/caregist
```

## Start / enable

```bash
sudo systemctl enable pgbouncer
sudo systemctl start pgbouncer
```

## Verify

```bash
psql -h 127.0.0.1 -p 6432 -U caregist pgbouncer -c "SHOW pools;"
```

## Important caveats

- **Transaction pooling** means `SET LOCAL`, advisory locks, and `LISTEN/NOTIFY` do not work across statements. CareGist uses `pg_advisory_lock` only in the feed cycle cron tool (which uses a raw `asyncpg.connect()` direct connection, not the pool), so this is safe.
- Do not use PgBouncer for the feed cycle cron — it connects directly to Postgres (`asyncpg.connect()`) and must keep the advisory lock alive for the duration of the run.
