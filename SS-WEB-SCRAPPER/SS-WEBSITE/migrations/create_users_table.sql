-- Users, roles, subscription, and page access tables

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'power_user', 'mod', 'admin')),
    subscription_status VARCHAR(20) NOT NULL DEFAULT 'inactive' CHECK (subscription_status IN ('inactive', 'active', 'trialing', 'past_due', 'cancelled')),
    subscription_tier VARCHAR(50),
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Per-role default page visibility. Pages not listed are inherited from lower roles.
CREATE TABLE IF NOT EXISTS role_page_access (
    id SERIAL PRIMARY KEY,
    role VARCHAR(20) NOT NULL UNIQUE,
    allowed_pages TEXT[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Per-user overrides (add or remove pages from role defaults)
CREATE TABLE IF NOT EXISTS user_page_access (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    allowed_pages TEXT[] NOT NULL DEFAULT '{}',
    denied_pages TEXT[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Subscription plans (ready for future Stripe/PayPal integration)
CREATE TABLE IF NOT EXISTS subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    slug VARCHAR(64) NOT NULL UNIQUE,
    price_eur NUMERIC(10,2),
    billing_interval VARCHAR(20) NOT NULL DEFAULT 'monthly' CHECK (billing_interval IN ('monthly', 'yearly')),
    role_grant VARCHAR(20) NOT NULL DEFAULT 'user',
    features TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Initial admin account (password will be hashed by init script)
INSERT INTO users (username, email, role, password_hash, subscription_status)
VALUES ('admin', 'admin@ss-crawler.local', 'admin', 'TO_BE_HASHED', 'active')
ON CONFLICT (username) DO NOTHING;
