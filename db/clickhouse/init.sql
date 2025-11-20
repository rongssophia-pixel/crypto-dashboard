-- ClickHouse initialization script
-- High-performance time-series storage for crypto market data

-- Create database
CREATE DATABASE IF NOT EXISTS crypto_analytics;

USE crypto_analytics;

-- Raw market data table (tick-level data)
CREATE TABLE IF NOT EXISTS market_data (
    tenant_id UUID,
    timestamp DateTime64(3),
    symbol String,
    exchange String,
    price Decimal(18, 8),
    volume Decimal(18, 8),
    bid_price Decimal(18, 8),
    ask_price Decimal(18, 8),
    bid_volume Decimal(18, 8),
    ask_volume Decimal(18, 8),
    high_24h Decimal(18, 8),
    low_24h Decimal(18, 8),
    volume_24h Decimal(18, 8),
    price_change_24h Decimal(18, 8),
    price_change_pct_24h Decimal(10, 4),
    trade_count UInt32,
    metadata String  -- JSON string for flexible additional data
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, symbol, timestamp)
SETTINGS index_granularity = 8192;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp) TYPE minmax GRANULARITY 4;
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol) TYPE set(100) GRANULARITY 4;

-- Aggregated candles table (OHLCV data)
CREATE TABLE IF NOT EXISTS market_candles (
    tenant_id UUID,
    timestamp DateTime64(3),
    symbol String,
    exchange String,
    interval String,  -- '1m', '5m', '15m', '1h', '4h', '1d'
    open Decimal(18, 8),
    high Decimal(18, 8),
    low Decimal(18, 8),
    close Decimal(18, 8),
    volume Decimal(18, 8),
    quote_volume Decimal(18, 8),
    trade_count UInt32,
    taker_buy_volume Decimal(18, 8),
    taker_buy_quote_volume Decimal(18, 8)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, symbol, interval, timestamp)
SETTINGS index_granularity = 8192;

CREATE INDEX IF NOT EXISTS idx_candles_timestamp ON market_candles(timestamp) TYPE minmax GRANULARITY 4;
CREATE INDEX IF NOT EXISTS idx_candles_symbol ON market_candles(symbol) TYPE set(100) GRANULARITY 4;
CREATE INDEX IF NOT EXISTS idx_candles_interval ON market_candles(interval) TYPE set(10) GRANULARITY 4;

-- Alert events table
CREATE TABLE IF NOT EXISTS alert_events (
    tenant_id UUID,
    timestamp DateTime64(3),
    alert_id UUID,
    user_id UUID,
    symbol String,
    condition_type String,
    threshold_value Decimal(18, 8),
    triggered_value Decimal(18, 8),
    comparison_operator String,
    message String,
    metadata String  -- JSON string
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, timestamp, alert_id)
SETTINGS index_granularity = 8192;

CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alert_events(timestamp) TYPE minmax GRANULARITY 4;
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON alert_events(symbol) TYPE set(100) GRANULARITY 4;

-- Materialized view for 1-minute aggregations (real-time)
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_1m_mv
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, symbol, timestamp)
AS SELECT
    tenant_id,
    toStartOfMinute(timestamp) AS timestamp,
    symbol,
    exchange,
    argMin(price, timestamp) AS open,
    max(price) AS high,
    min(price) AS low,
    argMax(price, timestamp) AS close,
    sum(volume) AS volume,
    count() AS trade_count,
    avg(price) AS avg_price,
    stddevPop(price) AS price_stddev
FROM market_data
GROUP BY tenant_id, symbol, exchange, toStartOfMinute(timestamp);

-- Materialized view for 5-minute aggregations
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_5m_mv
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, symbol, timestamp)
AS SELECT
    tenant_id,
    toStartOfFiveMinutes(timestamp) AS timestamp,
    symbol,
    exchange,
    argMin(price, timestamp) AS open,
    max(price) AS high,
    min(price) AS low,
    argMax(price, timestamp) AS close,
    sum(volume) AS volume,
    count() AS trade_count,
    avg(price) AS avg_price,
    stddevPop(price) AS price_stddev
FROM market_data
GROUP BY tenant_id, symbol, exchange, toStartOfFiveMinutes(timestamp);

-- Materialized view for hourly aggregations
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_1h_mv
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, symbol, timestamp)
AS SELECT
    tenant_id,
    toStartOfHour(timestamp) AS timestamp,
    symbol,
    exchange,
    argMin(price, timestamp) AS open,
    max(price) AS high,
    min(price) AS low,
    argMax(price, timestamp) AS close,
    sum(volume) AS volume,
    count() AS trade_count,
    avg(price) AS avg_price,
    stddevPop(price) AS price_stddev,
    (max(price) - min(price)) / min(price) * 100 AS volatility_pct
FROM market_data
GROUP BY tenant_id, symbol, exchange, toStartOfHour(timestamp);

-- Table for tracking data quality metrics
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    tenant_id UUID,
    timestamp DateTime64(3),
    symbol String,
    exchange String,
    metric_type String,  -- 'missing_data', 'latency', 'duplicate', 'anomaly'
    metric_value Float64,
    severity String,  -- 'low', 'medium', 'high', 'critical'
    description String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, timestamp, symbol)
SETTINGS index_granularity = 8192;

-- TTL policies for data retention (30 days for hot storage)
-- Uncomment to enable automatic data cleanup
-- ALTER TABLE market_data MODIFY TTL timestamp + INTERVAL 30 DAY;
-- ALTER TABLE market_candles MODIFY TTL timestamp + INTERVAL 90 DAY;
-- ALTER TABLE alert_events MODIFY TTL timestamp + INTERVAL 180 DAY;

-- Example queries for reference:

-- Get latest price for a symbol
-- SELECT symbol, timestamp, price, volume 
-- FROM market_data 
-- WHERE tenant_id = 'xxx' AND symbol = 'BTCUSDT' 
-- ORDER BY timestamp DESC LIMIT 1;

-- Get OHLCV candles
-- SELECT timestamp, open, high, low, close, volume 
-- FROM market_candles 
-- WHERE tenant_id = 'xxx' AND symbol = 'BTCUSDT' AND interval = '1h'
-- AND timestamp >= now() - INTERVAL 24 HOUR
-- ORDER BY timestamp DESC;

-- Calculate price volatility
-- SELECT 
--     symbol,
--     toStartOfHour(timestamp) as hour,
--     avg(price) as avg_price,
--     stddevPop(price) as volatility,
--     (max(price) - min(price)) / min(price) * 100 as price_range_pct
-- FROM market_data
-- WHERE tenant_id = 'xxx' AND timestamp >= now() - INTERVAL 24 HOUR
-- GROUP BY symbol, hour
-- ORDER BY hour DESC;

