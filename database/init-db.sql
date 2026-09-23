SELECT 'CREATE DATABASE rescuesync OWNER TO bonita'
WHERE NOT EXISTS (
    SELECT
        FROM pg_database
        WHERE datname = 'rescuesync'
)\gexec