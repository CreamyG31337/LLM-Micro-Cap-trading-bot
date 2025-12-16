-- Fix RLS policy for benchmark_data table to allow caching
-- This allows the application to cache benchmark data (S&P 500, QQQ, etc.) from Yahoo Finance

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow public read access to benchmark data" ON benchmark_data;
DROP POLICY IF EXISTS "Allow service role to insert benchmark data" ON benchmark_data;
DROP POLICY IF EXISTS "Allow service role to update benchmark data" ON benchmark_data;

-- Create new policies that allow the application to cache benchmark data
-- Read access: Anyone can read benchmark data (it's public market data)
CREATE POLICY "Allow public read access to benchmark data"
ON benchmark_data
FOR SELECT
USING (true);

-- Insert access: Service role can insert new benchmark data
CREATE POLICY "Allow service role to insert benchmark data"
ON benchmark_data
FOR INSERT
WITH CHECK (
  -- Allow if using service role key (backend operations)
  auth.jwt() ->> 'role' = 'service_role'
  OR
  -- Allow if using anon key (for caching from frontend)
  auth.jwt() ->> 'role' = 'anon'
  OR
  -- Allow if authenticated (logged in users can cache benchmarks)
  auth.uid() IS NOT NULL
);

-- Update access: Service role can update existing benchmark data
CREATE POLICY "Allow service role to update benchmark data"
ON benchmark_data
FOR UPDATE
USING (
  auth.jwt() ->> 'role' = 'service_role'
  OR
  auth.jwt() ->> 'role' = 'anon'
  OR
  auth.uid() IS NOT NULL
);

-- Verify RLS is enabled
ALTER TABLE benchmark_data ENABLE ROW LEVEL SECURITY;

-- Test the policies
SELECT 
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
FROM pg_policies 
WHERE tablename = 'benchmark_data'
ORDER BY policyname;
