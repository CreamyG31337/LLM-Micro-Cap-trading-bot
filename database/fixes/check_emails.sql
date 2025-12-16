-- Check email formats in fund_contributions for Project Chimera
SELECT DISTINCT email, contributor FROM fund_contributions 
WHERE fund = 'Project Chimera'
ORDER BY contributor;
