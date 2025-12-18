-- PostgreSQL initialization script
-- Multi-user crypto analytics platform

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    roles VARCHAR(50)[] DEFAULT ARRAY['user']::VARCHAR[],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- Crypto tickers metadata
CREATE TABLE tickers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    base_currency VARCHAR(10) NOT NULL,
    quote_currency VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    min_order_size DECIMAL(18, 8),
    price_precision INTEGER,
    volume_precision INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT tickers_symbol_format CHECK (length(symbol) >= 3)
);

CREATE INDEX idx_tickers_symbol ON tickers(symbol);
CREATE INDEX idx_tickers_exchange ON tickers(exchange);
CREATE INDEX idx_tickers_active ON tickers(is_active);
CREATE INDEX idx_tickers_base_currency ON tickers(base_currency);

-- Alert subscriptions
CREATE TABLE alert_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker_symbol VARCHAR(20) NOT NULL,
    condition_type VARCHAR(50) NOT NULL,  -- price_above, price_below, volume_spike, price_change_pct
    threshold_value DECIMAL(18, 8),
    comparison_operator VARCHAR(10),  -- >, <, >=, <=, ==
    timeframe_minutes INTEGER,  -- for time-based conditions
    is_active BOOLEAN DEFAULT true,
    notification_channels VARCHAR(20)[] DEFAULT ARRAY['email']::VARCHAR[],
    cooldown_minutes INTEGER DEFAULT 60,  -- prevent alert spam
    last_triggered_at TIMESTAMP,
    trigger_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT alert_valid_condition CHECK (condition_type IN ('price_above', 'price_below', 'volume_spike', 'price_change_pct', 'volatility_high'))
);

CREATE INDEX idx_alerts_user_id ON alert_subscriptions(user_id);
CREATE INDEX idx_alerts_ticker ON alert_subscriptions(ticker_symbol);
CREATE INDEX idx_alerts_active ON alert_subscriptions(is_active);

-- Stream sessions tracking
CREATE TABLE stream_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stream_id VARCHAR(100) NOT NULL UNIQUE,
    symbols VARCHAR(20)[] NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    stream_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',  -- active, stopped, error
    events_processed BIGINT DEFAULT 0,
    last_event_at TIMESTAMP,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stopped_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_stream_sessions_stream_id ON stream_sessions(stream_id);
CREATE INDEX idx_stream_sessions_status ON stream_sessions(status);

-- Notification logs
CREATE TABLE notification_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    notification_type VARCHAR(20) NOT NULL,  -- email, sms, push, sns
    subject VARCHAR(500),
    body TEXT,
    recipients TEXT[] NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, sent, failed, delivered
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    priority VARCHAR(10) DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_notifications_user_id ON notification_logs(user_id);
CREATE INDEX idx_notifications_status ON notification_logs(status);
CREATE INDEX idx_notifications_created_at ON notification_logs(created_at DESC);

-- Archive jobs tracking
CREATE TABLE archive_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    archive_id VARCHAR(100) NOT NULL UNIQUE,
    data_type VARCHAR(50) NOT NULL,  -- market_data, candles, alerts
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    s3_path TEXT,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    records_archived BIGINT DEFAULT 0,
    size_bytes BIGINT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_archive_jobs_archive_id ON archive_jobs(archive_id);
CREATE INDEX idx_archive_jobs_status ON archive_jobs(status);
CREATE INDEX idx_archive_jobs_created_at ON archive_jobs(created_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickers_updated_at BEFORE UPDATE ON tickers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON alert_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Refresh tokens table for JWT authentication
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT refresh_tokens_jti_unique UNIQUE (token_jti)
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_jti ON refresh_tokens(token_jti);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_revoked_at ON refresh_tokens(revoked_at);

COMMENT ON TABLE refresh_tokens IS 'Stores refresh tokens for JWT authentication with revocation support';

INSERT INTO tickers (symbol, name, exchange, base_currency, quote_currency) VALUES
    ('BTCUSDT', 'Bitcoin', 'binance', 'BTC', 'USDT'),
    ('ETHUSDT', 'Ethereum', 'binance', 'ETH', 'USDT'),
    ('BNBUSDT', 'Binance Coin', 'binance', 'BNB', 'USDT'),
    ('ADAUSDT', 'Cardano', 'binance', 'ADA', 'USDT'),
    ('SOLUSDT', 'Solana', 'binance', 'SOL', 'USDT');
