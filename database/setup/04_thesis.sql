-- =====================================================
-- THESIS SCHEMA
-- =====================================================
-- This schema adds thesis storage to the portfolio dashboard
-- Run this AFTER the main schema (01_main_schema.sql)
-- =====================================================

-- Drop existing thesis table if it exists
DROP TABLE IF EXISTS fund_thesis CASCADE;

-- =====================================================
-- THESIS TABLE
-- =====================================================

-- Fund thesis table
CREATE TABLE fund_thesis (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    overview TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fund thesis pillars table
CREATE TABLE fund_thesis_pillars (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    thesis_id UUID NOT NULL REFERENCES fund_thesis(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    allocation VARCHAR(20) NOT NULL,
    thesis TEXT NOT NULL,
    pillar_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Fund thesis indexes
CREATE INDEX idx_fund_thesis_fund ON fund_thesis(fund);
CREATE INDEX idx_fund_thesis_pillars_thesis_id ON fund_thesis_pillars(thesis_id);
CREATE INDEX idx_fund_thesis_pillars_order ON fund_thesis_pillars(pillar_order);

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Updated_at triggers for thesis tables
CREATE TRIGGER update_fund_thesis_updated_at
    BEFORE UPDATE ON fund_thesis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fund_thesis_pillars_updated_at
    BEFORE UPDATE ON fund_thesis_pillars
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- RLS POLICIES
-- =====================================================

-- Enable RLS on thesis tables
ALTER TABLE fund_thesis ENABLE ROW LEVEL SECURITY;
ALTER TABLE fund_thesis_pillars ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (allow all for now - will be restricted by auth schema)
CREATE POLICY "Allow all operations on fund_thesis" ON fund_thesis
    FOR ALL USING (true);

CREATE POLICY "Allow all operations on fund_thesis_pillars" ON fund_thesis_pillars
    FOR ALL USING (true);

-- =====================================================
-- UTILITY FUNCTIONS
-- =====================================================

-- Function to get complete thesis data for a fund
CREATE OR REPLACE FUNCTION get_fund_thesis(fund_name VARCHAR(50))
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'guiding_thesis', json_build_object(
            'title', ft.title,
            'overview', ft.overview,
            'pillars', COALESCE(
                (SELECT json_agg(
                    json_build_object(
                        'name', ftp.name,
                        'allocation', ftp.allocation,
                        'thesis', ftp.thesis
                    ) ORDER BY ftp.pillar_order
                )
                FROM fund_thesis_pillars ftp 
                WHERE ftp.thesis_id = ft.id), 
                '[]'::json
            )
        )
    ) INTO result
    FROM fund_thesis ft
    WHERE ft.fund = fund_name;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SCHEMA COMPLETE
-- =====================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Thesis schema created successfully!';
    RAISE NOTICE '📋 Next step: Run migration script to populate thesis data';
    RAISE NOTICE '🔧 Use get_fund_thesis(fund_name) function to retrieve thesis data';
END $$;
