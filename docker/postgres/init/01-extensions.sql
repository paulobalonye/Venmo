-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_crypto for password hashing
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable citext for case-insensitive text (emails, usernames)
CREATE EXTENSION IF NOT EXISTS "citext";
