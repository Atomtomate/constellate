-- The constellate database and the role that owns it, on a Postgres this project shares with
-- its sibling (compose.yaml at the repository root says how the sharing works).
--
-- Run as the server's superuser against any database -- `postgres` will do -- and through psql,
-- which both callers are: the image's entrypoint on an empty volume, and the command in
-- infra/README.md on a server that already holds data. psql rather than plain SQL because
-- `\gexec` is psql's: CREATE DATABASE cannot run inside a transaction block, so neither
-- statement can sit in a DO block, and "only if missing" has to be a query whose one row psql
-- then executes. Safe to run twice: a second run finds both present and does nothing.
--
-- CREATEDB because the API's test suite, when it runs against Postgres, provisions a throwaway
-- database per run and drops it after (api/tests/conftest.py, the sibling's pattern). The
-- password is development-only and is the one in config.py's default URL; a rig that faces the
-- internet (Q-E) sets its own.

SELECT 'CREATE ROLE constellate LOGIN CREATEDB PASSWORD ''constellate'''
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'constellate')
\gexec

SELECT 'CREATE DATABASE constellate OWNER constellate'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'constellate')
\gexec
