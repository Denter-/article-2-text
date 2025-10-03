-- Site configurations table
CREATE TABLE site_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain VARCHAR(255) UNIQUE NOT NULL,
    
    -- Configuration
    config_yaml TEXT NOT NULL, -- Full YAML config
    requires_browser BOOLEAN DEFAULT FALSE,
    
    -- Learning metadata
    learned_by_user_id UUID REFERENCES users(id),
    learned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    learn_iterations INTEGER DEFAULT 1,
    
    -- Usage stats
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Version control
    version INTEGER DEFAULT 1,
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance metrics
    avg_extraction_time_ms INTEGER
);

CREATE INDEX idx_site_configs_domain ON site_configs(domain);
CREATE INDEX idx_site_configs_requires_browser ON site_configs(requires_browser);
CREATE TRIGGER update_site_configs_updated_at BEFORE UPDATE ON site_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();



