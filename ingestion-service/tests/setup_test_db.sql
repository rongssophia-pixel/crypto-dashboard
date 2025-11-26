-- Create stream_sessions table for testing
CREATE TABLE IF NOT EXISTS stream_sessions (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    stream_id VARCHAR(255) UNIQUE NOT NULL,
    symbols TEXT[] NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    stream_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    events_processed INTEGER DEFAULT 0,
    started_at TIMESTAMP NOT NULL,
    stopped_at TIMESTAMP,
    last_event_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_stream_sessions_tenant ON stream_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_stream_sessions_stream_id ON stream_sessions(stream_id);
CREATE INDEX IF NOT EXISTS idx_stream_sessions_status ON stream_sessions(status);

-- Add comment
COMMENT ON TABLE stream_sessions IS 'Tracks active and historical data stream sessions';
