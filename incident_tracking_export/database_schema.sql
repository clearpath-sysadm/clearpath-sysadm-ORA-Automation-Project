-- ============================================================
-- INCIDENT TRACKING SYSTEM - DATABASE SCHEMA
-- ============================================================
-- PostgreSQL schema for production incident management
-- Supports: incidents, notes, screenshots, filtering, emoji text
-- ============================================================

-- Main incidents table
CREATE TABLE production_incidents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status VARCHAR(20) NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'in_progress', 'resolved', 'closed')),
    reported_by VARCHAR(255),
    cause TEXT,
    resolution TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Notes/updates table for incident timeline
CREATE TABLE incident_notes (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES production_incidents(id) ON DELETE CASCADE,
    note_type VARCHAR(20) NOT NULL CHECK (note_type IN ('user', 'system')),
    note TEXT NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Screenshots table for visual evidence
CREATE TABLE production_incident_screenshots (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES production_incidents(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_data BYTEA NOT NULL,
    uploaded_by VARCHAR(255),
    uploaded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_incident_notes_incident_id ON incident_notes(incident_id);
CREATE INDEX idx_screenshots_incident_id ON production_incident_screenshots(incident_id);
CREATE INDEX idx_incidents_status ON production_incidents(status);
CREATE INDEX idx_incidents_severity ON production_incidents(severity);
CREATE INDEX idx_incidents_created_at ON production_incidents(created_at DESC);

-- Sample data (optional - remove if not needed)
-- INSERT INTO production_incidents (title, description, severity, reported_by, status) 
-- VALUES ('Sample Incident', 'This is a test incident to verify the system is working', 'medium', 'System Admin', 'new');
