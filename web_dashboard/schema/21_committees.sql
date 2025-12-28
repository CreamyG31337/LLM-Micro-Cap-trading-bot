-- =====================================================
-- CREATE COMMITTEES METADATA TABLES (Supabase)
-- =====================================================
-- Stores current US Congress members, committees, and their assignments
-- Part of Congress Trading Module - Conflict Score Calculation
-- 
-- Purpose: Enable Granite AI to identify when politicians trade stocks
--          in sectors related to their committee assignments
-- =====================================================

-- =====================================================
-- POLITICIANS TABLE
-- =====================================================
-- Stores current members of Congress with their basic information
CREATE TABLE IF NOT EXISTS politicians (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    bioguide_id VARCHAR(20) NOT NULL UNIQUE,  -- Unique identifier from congress-legislators project
    party VARCHAR(50),                         -- e.g., "Democrat", "Republican", "Independent"
    state VARCHAR(2) NOT NULL,                -- Two-letter state code (e.g., "CA", "NY")
    chamber VARCHAR(20) NOT NULL CHECK (chamber IN ('House', 'Senate')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for politicians table
CREATE INDEX IF NOT EXISTS idx_politicians_bioguide_id ON politicians(bioguide_id);
CREATE INDEX IF NOT EXISTS idx_politicians_name ON politicians(name);
CREATE INDEX IF NOT EXISTS idx_politicians_chamber ON politicians(chamber);
CREATE INDEX IF NOT EXISTS idx_politicians_state ON politicians(state);

-- Add comments
COMMENT ON TABLE politicians IS 
  'Current members of US Congress. One politician can serve on multiple committees.';
COMMENT ON COLUMN politicians.bioguide_id IS 
  'Unique identifier from unitedstates/congress-legislators project. Used to link with committee assignments.';

-- =====================================================
-- COMMITTEES TABLE
-- =====================================================
-- Stores congressional committees with their target sectors
CREATE TABLE IF NOT EXISTS committees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,               -- Full committee name (e.g., "House Committee on Armed Services")
    code VARCHAR(20),                         -- Committee code from YAML (e.g., "SSAF", "HASC")
    chamber VARCHAR(20) NOT NULL CHECK (chamber IN ('House', 'Senate')),
    target_sectors JSONB DEFAULT '[]'::jsonb, -- Array of sectors this committee regulates (from committee_map.py)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, chamber)                      -- Same committee name can't exist in both chambers
);

-- Indexes for committees table
CREATE INDEX IF NOT EXISTS idx_committees_name ON committees(name);
CREATE INDEX IF NOT EXISTS idx_committees_code ON committees(code);
CREATE INDEX IF NOT EXISTS idx_committees_chamber ON committees(chamber);
CREATE INDEX IF NOT EXISTS idx_committees_target_sectors ON committees USING GIN(target_sectors);  -- GIN index for JSONB queries

-- Add comments
COMMENT ON TABLE committees IS 
  'Congressional committees with their target sectors. Used to calculate conflict scores for stock trades.';
COMMENT ON COLUMN committees.target_sectors IS 
  'JSONB array of sectors this committee regulates (e.g., ["Industrials", "Defense", "Aerospace"]). From data/committee_map.py.';

-- =====================================================
-- COMMITTEE ASSIGNMENTS TABLE (Many-to-Many)
-- =====================================================
-- Links politicians to committees - one politician can be on multiple committees
CREATE TABLE IF NOT EXISTS committee_assignments (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL REFERENCES politicians(id) ON DELETE CASCADE,
    committee_id INTEGER NOT NULL REFERENCES committees(id) ON DELETE CASCADE,
    rank INTEGER,                              -- Committee rank/position (1 = highest rank)
    title VARCHAR(100),                        -- e.g., "Chairman", "Ranking Member", "Member"
    party VARCHAR(50),                         -- Party affiliation in committee context (majority/minority)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(politician_id, committee_id)        -- Prevent duplicate assignments
);

-- Indexes for committee_assignments table
CREATE INDEX IF NOT EXISTS idx_committee_assignments_politician ON committee_assignments(politician_id);
CREATE INDEX IF NOT EXISTS idx_committee_assignments_committee ON committee_assignments(committee_id);
CREATE INDEX IF NOT EXISTS idx_committee_assignments_politician_committee ON committee_assignments(politician_id, committee_id);

-- Add comments
COMMENT ON TABLE committee_assignments IS 
  'Many-to-many relationship: Links politicians to committees. One politician can serve on multiple committees.';
COMMENT ON COLUMN committee_assignments.rank IS 
  'Committee rank/position. Lower numbers = higher rank (1 = Chairman/Ranking Member).';

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
DECLARE
    politician_count INTEGER;
    committee_count INTEGER;
    assignment_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO politician_count FROM politicians;
    SELECT COUNT(*) INTO committee_count FROM committees;
    SELECT COUNT(*) INTO assignment_count FROM committee_assignments;
    
    RAISE NOTICE '✅ Committees metadata tables created!';
    RAISE NOTICE '   Politicians: %', politician_count;
    RAISE NOTICE '   Committees: %', committee_count;
    RAISE NOTICE '   Assignments: %', assignment_count;
    RAISE NOTICE '';
    RAISE NOTICE '   Run seed_committees.py to populate data from YAML files.';
END $$;

