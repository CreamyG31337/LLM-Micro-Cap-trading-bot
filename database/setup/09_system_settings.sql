-- Migration: System Settings Table
-- Description: Create a flexible key-value store for global system configuration
-- Author: AI Assistant
-- Date: 2025-12-24

-- Create system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES auth.users(id)
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_system_settings_updated_at ON system_settings(updated_at DESC);

-- Enable RLS
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone authenticated can view settings
CREATE POLICY "Anyone can view system settings"
    ON system_settings
    FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Only admins can insert/update/delete settings
CREATE POLICY "Only admins can modify system settings"
    ON system_settings
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM user_profiles
            WHERE user_profiles.user_id = auth.uid()
            AND user_profiles.role = 'admin'
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM user_profiles
            WHERE user_profiles.user_id = auth.uid()
            AND user_profiles.role = 'admin'
        )
    );

-- Insert default AI model setting (if not exists)
INSERT INTO system_settings (key, value, description, updated_by)
VALUES (
    'ai_default_model',
    '"llama3"'::jsonb,
    'Default AI model for new users and system prompts',
    (SELECT id FROM auth.users WHERE email = 'admin@example.com' LIMIT 1)
)
ON CONFLICT (key) DO NOTHING;

-- Add comment
COMMENT ON TABLE system_settings IS 'Global system configuration key-value store. Values are stored as JSONB for flexibility.';
