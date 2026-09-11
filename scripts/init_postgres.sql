-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Users Table (Authentication & RBAC)
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'user',
    department VARCHAR(128),
    avatar_color VARCHAR(32),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Thread Ownership Table
CREATE TABLE IF NOT EXISTS threads (
    thread_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Human-Readable Chat Messages Table
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(64) NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    sender VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_name VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Structured File Metadata Table
CREATE TABLE IF NOT EXISTS file_metadata (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(64) NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(message_id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id),
    original_filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type VARCHAR(128),
    file_size_bytes BIGINT NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. RAG Document Chunk Embeddings Table (pgvector)
CREATE TABLE IF NOT EXISTS rag_embeddings (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID REFERENCES file_metadata(file_id) ON DELETE CASCADE,
    source_filename VARCHAR(255) NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Persistent Cross-Session User Memories Table (pgvector)
CREATE TABLE IF NOT EXISTS user_memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    memory_type VARCHAR(64) NOT NULL DEFAULT 'fact',
    content TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed Default Accounts with pre-hashed default passwords
INSERT INTO users (user_id, username, name, role, department, avatar_color, password_hash)
VALUES 
    ('admin', 'admin', 'System Administrator', 'admin', 'Enterprise IT & Security', 'bg-blue-600', '0c4f731af482b1240e48922a5580d0b5$a123d4117dc3df762443f12dfa34222978c1837ef381e5a4b2cb3f5f05cac485'),
    ('engineer1', 'engineer1', 'Sathwik (Lead Engineer)', 'user', 'Refinery Operations', 'bg-emerald-500', '1f42346be89edaf4001d6bec456f235b$18ff76d90dc2c0537dee1f53ac8077c290c0e8744e0d63297a251b11cce5f86d'),
    ('analyst1', 'analyst1', 'Dr. Ananya (Data Analyst)', 'user', 'Process & Quality Engineering', 'bg-amber-500', '0c4f731af482b1240e48922a5580d0b5$a123d4117dc3df762443f12dfa34222978c1837ef381e5a4b2cb3f5f05cac485')
ON CONFLICT (user_id) DO NOTHING;
