# Research Reports Processing System

## Overview

The Research Reports Processing System automatically processes PDF research reports stored in organized folders, extracts text and tables using pdfplumber, generates vector embeddings, and stores them in the research_articles database for semantic search.

## Architecture

```
User Upload → Research/{TICKER}/ or Research/_NEWS/ or Research/_FUND/
                    ↓
            Scheduled Job (process_research_reports_job)
                    ↓
        [Add Date Prefix] → [Extract Text] → [Generate Embedding] → [AI Summary]
                    ↓
            Store in research_articles table
                    ↓
        Available for semantic search & display
```

## Folder Structure

Research reports are organized in the `Research/` directory:

```
Research/
├── {TICKER}/          # Ticker-specific reports (e.g., GANX, NVDA)
│   └── YYYYMMDD_filename.pdf
├── _NEWS/             # Market/news reports
│   └── YYYYMMDD_filename.pdf
└── _FUND/             # Fund-specific reports
    └── YYYYMMDD_filename.pdf
```

### Folder Types

1. **Ticker-specific** (`Research/{TICKER}/`)
   - Reports about specific companies
   - Example: `Research/GANX/20250115_Researching Gain Therapeutics.pdf`
   - Ticker is extracted from folder name

2. **News/Market** (`Research/_NEWS/`)
   - General market news and analysis
   - No specific ticker associated
   - Example: `Research/_NEWS/20250115_Market Analysis Q1 2025.pdf`

3. **Fund-specific** (`Research/_FUND/`)
   - Reports prepared for specific funds
   - Example: `Research/_FUND/20250115_Project Chimera Weekly Report.pdf`
   - Fund name can be extracted from filename or set manually

## File Naming Convention

- **Date Prefix**: Files must have `YYYYMMDD_` prefix (added automatically by job)
- **Format**: `YYYYMMDD_descriptive_title.pdf`
- **Example**: `20250115_Researching Gain Therapeutics Drug Testing.pdf`

The processing job automatically adds the date prefix (current date) if missing.

## Upload Methods

### 1. Web UI Upload (Bulk Supported)

**Location**: Research page → Admin Tools → Upload Report

**Features**:
- Single or multiple file upload (select multiple PDFs at once)
- Progress indicator for bulk uploads
- Automatic folder organization
- Skips duplicate files (already exists check)

**Steps**:
1. Select report type: Ticker-specific, News/Market, or Fund-specific
2. Enter ticker symbol (for ticker reports) or select fund (for fund reports)
3. Select one or multiple PDF files
4. Click "Save File(s)"
5. Files are saved to appropriate folder
6. Job processes them automatically

**Bulk Upload**:
- Select multiple files using Ctrl+Click (Windows) or Cmd+Click (Mac)
- All files are saved to the same target folder
- Progress bar shows upload status
- Each file is processed individually by the job

### 2. Manual File Placement

You can also manually place PDF files in the appropriate folders:
- Copy files directly to `Research/{TICKER}/` folders
- Job will detect and process them automatically

## Processing Job

### Job Name
`process_research_reports_job`

### Schedule
Configure in scheduler (recommended: hourly or every 6 hours)

### Process Flow

1. **Scan Folders**
   - Scans all subdirectories in `Research/`
   - Finds all `.pdf` files recursively

2. **Check Already Processed**
   - Queries database by file path (`url` field)
   - Skips files already in database

3. **Add Date Prefix** (if missing)
   - Adds `YYYYMMDD_` prefix using current date
   - Renames file automatically

4. **Extract Metadata**
   - Extracts title from filename (removes date prefix)
   - Determines report type from folder
   - Extracts ticker from folder name (if applicable)
   - Parses date from filename

5. **Extract Content**
   - Uses pdfplumber to extract text (better formatting than pypdf)
   - Preserves paragraph structure
   - Extracts tables (if present)

6. **Generate AI Analysis**
   - Generates vector embedding (768 dimensions)
   - Creates AI summary with Chain of Thought analysis
   - Extracts claims, fact-check, conclusion, sentiment

7. **Store in Database**
   - Saves to `research_articles` table
   - `url` field stores relative file path
   - `article_type` = `'research_report'`
   - Full text in `content` field
   - Embedding for semantic search

## Database Schema

Reports are stored in the existing `research_articles` table:

| Field | Value | Description |
|-------|-------|-------------|
| `url` | `Research/GANX/20250115_report.pdf` | Relative file path (UNIQUE) |
| `article_type` | `'research_report'` | Type identifier |
| `ticker` | `'GANX'` or NULL | Extracted from folder name |
| `fund` | Fund name or NULL | For fund-specific reports |
| `title` | Cleaned filename | Without date prefix |
| `content` | Full extracted text | From pdfplumber |
| `embedding` | Vector(768) | For semantic search |
| `published_at` | Date from filename | Parsed YYYYMMDD |
| `source` | `'Research Report'` | Source identifier |

## File Serving

PDFs are served via Caddy web server:

- **URL Pattern**: `https://your-domain.com/research/{TICKER}/filename.pdf`
- **Example**: `https://your-domain.com/research/GANX/20250115_Researching Gain Therapeutics.pdf`
- **Configuration**: See `Caddyfile.example` for setup

## Deployment

### Git Ignore
- PDF files are gitignored: `Research/**/*.pdf`
- Folder structure is preserved
- Files are deployed via Woodpecker CI/CD

### Woodpecker Configuration
- Efficient incremental copying (only changed files)
- Preserves folder structure
- Skips if no Research folder exists

### Caddy Configuration
- Static file server for `/research/*` paths
- Cache headers for performance
- See `Caddyfile.example` for setup

## Usage Examples

### Upload Single Ticker Report
1. Go to Research page → Admin Tools
2. Select "Ticker-specific"
3. Enter ticker: `GANX`
4. Upload PDF file
5. File saved to `Research/GANX/`
6. Job processes automatically

### Bulk Upload Multiple Reports
1. Go to Research page → Admin Tools
2. Select "Ticker-specific"
3. Enter ticker: `NVDA`
4. Select multiple PDF files (Ctrl+Click)
5. Click "Save Files"
6. All files saved to `Research/NVDA/`
7. Job processes all files automatically

### Manual Placement
1. Copy PDF files to `Research/{TICKER}/` folder
2. Job detects new files on next run
3. Processes automatically

## Troubleshooting

### Files Not Processing
- Check job logs: `process_research_reports_job`
- Verify files are in correct folder structure
- Check if files already processed (query database by `url`)
- Ensure PDFs are valid (not corrupted)

### Missing Date Prefix
- Job automatically adds date prefix if missing
- Uses current date when processing
- Original filename preserved in title

### Duplicate Files
- Upload handler skips files that already exist
- Job skips files already in database
- Check by querying `research_articles` table with file path

### Text Extraction Issues
- pdfplumber handles most PDFs well
- Scanned PDFs (images) may not extract text
- Check job logs for extraction errors

## Integration with Research System

Processed reports are:
- **Searchable**: Via semantic search using vector embeddings
- **Filterable**: By ticker, fund, date, type
- **Displayable**: In Research page with full content
- **Linkable**: Direct PDF links for viewing original

## Future Enhancements

- Support for DOCX files
- HTML export for better table display
- Automatic ticker extraction from PDF content
- Fund name extraction from filename patterns
- ZIP file upload and extraction
- Batch processing status tracking

