-- Temporarily disable foreign key constraints
SET session_replication_role = replica;

-- Run the data migration
\i data_migration.sql

-- Re-enable foreign key constraints
SET session_replication_role = DEFAULT;
