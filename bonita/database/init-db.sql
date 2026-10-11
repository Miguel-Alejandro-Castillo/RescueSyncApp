SELECT 'CREATE DATABASE rescuesync OWNER bonita'
WHERE NOT EXISTS (
    SELECT
        FROM pg_database
        WHERE datname = 'rescuesync'
)\gexec