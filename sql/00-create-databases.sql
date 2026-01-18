-- ============================================================================
-- Create Both Databases for MCP Demo
-- ============================================================================
-- This script runs first and creates both databases needed for the demo:
-- 1. rag_service - For knowledge base search with pgvector
-- 2. cicd_service - For CI/CD data queries
-- ============================================================================

-- Create RAG database
CREATE DATABASE rag_service;

-- Create CI/CD database
CREATE DATABASE cicd_service;

-- Grant privileges to testuser
GRANT ALL PRIVILEGES ON DATABASE rag_service TO testuser;
GRANT ALL PRIVILEGES ON DATABASE cicd_service TO testuser;
