-- Job status enum
CREATE TYPE job_status AS ENUM (
    'queued',
    'processing',
    'learning',
    'extracting',
    'generating_descriptions',
    'completed',
    'failed'
);

-- Extraction jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    status job_status DEFAULT 'queued',
    worker_type VARCHAR(50), -- 'go' or 'python'
    
    -- Progress tracking
    progress_percent INTEGER DEFAULT 0,
    progress_message TEXT,
    
    -- Results
    result_path TEXT, -- Path in storage
    markdown_content TEXT,
    
    -- Metadata
    title TEXT,
    author TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    word_count INTEGER,
    image_count INTEGER,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timing
    queued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Cost tracking
    credits_used INTEGER DEFAULT 1,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_domain ON jobs(domain);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();



