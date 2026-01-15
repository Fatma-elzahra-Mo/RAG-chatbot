# Scripts Documentation

This directory contains utility scripts for managing the Arabic RAG chatbot.

## Scripts Overview

### `ingest_json.py` - JSON to Qdrant Ingestion

Robust script for ingesting JSON documents into the Qdrant vector store.

#### Features

- **Multiple Format Support**:
  - Firecrawl format: `{"pages": [{"url", "title", "text"}]}`
  - Generic format: `[{"text": "...", "metadata": {...}}]`
  - Auto-detection of format

- **Validation**: Comprehensive JSON validation before processing

- **Preview Mode**: Dry-run capability to preview ingestion without processing

- **Progress Tracking**: Real-time progress bar with tqdm for large datasets

- **Batch Processing**: Configurable batch size for memory efficiency

- **Error Handling**: Graceful error handling with clear error messages

- **Statistics**: Detailed ingestion statistics (docs, chunks, time, rate)

#### Usage

```bash
# Auto-detect format and ingest
python scripts/ingest_json.py --file data.json

# Specify format explicitly
python scripts/ingest_json.py --file data.json --format firecrawl

# Preview without ingesting (doesn't require Qdrant)
python scripts/ingest_json.py --file data.json --dry-run

# Clear existing data before ingesting
python scripts/ingest_json.py --file data.json --clear

# Custom batch size for large files
python scripts/ingest_json.py --file data.json --batch-size 50

# Use custom collection name
python scripts/ingest_json.py --file data.json --collection my_docs
```

#### Supported JSON Formats

**Firecrawl Format**:
```json
{
  "timestamp": "2026-01-12T02:26:56",
  "pages_scraped": 20,
  "pages": [
    {
      "url": "https://example.com/page1",
      "title": "Page Title",
      "text": "Full page content here..."
    }
  ]
}
```

**Generic Format**:
```json
[
  {
    "text": "Document content here...",
    "metadata": {
      "source": "manual_entry",
      "category": "internet",
      "date": "2026-01-12"
    }
  }
]
```

#### Example Output

```
📥 Loading JSON from: data.json
✅ Auto-detected format: firecrawl
📄 Found 20 documents to ingest

🚀 Ingesting documents...
Progress: 100% ████████████ 20/20 [00:15<00:00, 1.33docs/s]

✅ Ingestion complete!
  - Documents: 20
  - Chunks created: 156
  - Time: 15.2s
  - Rate: 1.32 docs/s

💡 Run 'streamlit run streamlit_app/app.py' to test the chatbot
```

#### Error Handling

The script handles various error scenarios:

- **File not found**: Clear error message with file path
- **Invalid JSON**: Shows JSON parsing error with line number
- **Unsupported format**: Explains expected formats
- **Missing text fields**: Skips documents with warnings
- **Qdrant connection issues**: Clear error for connection problems

#### Sample Data

Sample JSON files are provided in the `data/` directory:

- `data/sample_firecrawl.json` - Example Firecrawl format
- `data/sample_generic.json` - Example Generic format

#### Requirements

- Qdrant must be running for actual ingestion (not needed for `--dry-run`)
- All dependencies installed: `uv pip install -e ".[dev]"`

#### Advanced Usage

**Testing with dry-run**:
```bash
# Preview what would be ingested
python scripts/ingest_json.py --file data.json --dry-run
```

**Large file ingestion**:
```bash
# Use larger batch size for efficiency
python scripts/ingest_json.py --file large_dataset.json --batch-size 100
```

**Replacing existing data**:
```bash
# Clear collection before ingesting new data
python scripts/ingest_json.py --file new_data.json --clear
```

---

### `export_qdrant.py` - Export Data from Qdrant

Export documents from Qdrant vector database to JSON file for sharing or backup.

#### Features

- **Multiple Format Support**: Export in generic or Firecrawl format
- **Selective Export**: Filter out conversation memory or export everything
- **Batch Processing**: Efficient pagination for large collections
- **Progress Tracking**: Real-time progress bar with tqdm
- **Limit Support**: Export only a subset of documents
- **Compatible with ingestion**: Exported JSON can be re-imported using `ingest_json.py`

#### Usage

```bash
# Export default collection to file
python scripts/export_qdrant.py --output exported_data.json

# Export specific collection
python scripts/export_qdrant.py --collection my_docs --output my_data.json

# Export in Firecrawl format
python scripts/export_qdrant.py --output data.json --format firecrawl

# Export only first 100 documents (for testing)
python scripts/export_qdrant.py --output sample.json --limit 100

# Include conversation memory documents
python scripts/export_qdrant.py --output full_data.json --include-memory

# Custom batch size for large collections
python scripts/export_qdrant.py --output data.json --batch-size 200
```

#### Output Formats

**Generic Format** (default):
```json
[
  {
    "text": "Document content here...",
    "metadata": {
      "source": "document.pdf",
      "category": "internet",
      "date": "2026-01-12"
    }
  }
]
```

**Firecrawl Format**:
```json
{
  "timestamp": "2026-01-15T10:30:00",
  "pages_scraped": 20,
  "pages": [
    {
      "url": "https://example.com/page1",
      "title": "Page Title",
      "text": "Full page content here..."
    }
  ]
}
```

#### Common Use Cases

**Sharing data with coworkers**:
```bash
# Export your collection
python scripts/export_qdrant.py --output shared_data.json

# Coworker imports the data
python scripts/ingest_json.py --file shared_data.json
```

**Creating backups**:
```bash
# Export everything including conversation history
python scripts/export_qdrant.py --output backup_$(date +%Y%m%d).json --include-memory
```

**Creating test datasets**:
```bash
# Export small sample for testing
python scripts/export_qdrant.py --output test_sample.json --limit 50
```

#### Example Output

```
📤 Exporting from Qdrant
  Collection: arabic_docs
  Total documents: 156
  Exporting: 156
  Format: generic
  Output: exported_data.json

Exporting: 100% ████████████ 156/156 [00:03<00:00, 52.1docs/s]

💾 Saving to exported_data.json...

✅ Export complete!
  - Documents exported: 156
  - Time: 3.1s
  - Rate: 50.3 docs/s
  - File size: 2.4 MB

💡 To import this data:
   python scripts/ingest_json.py --file exported_data.json
```

---

### `check_qdrant.py` - Verify Qdrant Data

Check and verify data in Qdrant vector database.

#### Features

- List all collections
- Count documents in collections
- View sample documents
- Search for documents by text
- Verify collection health
- Delete collections (with confirmation)

#### Usage

```bash
# List all collections
python scripts/check_qdrant.py --list

# Check default collection
python scripts/check_qdrant.py --info

# Show 10 sample documents
python scripts/check_qdrant.py --samples 10

# Search for documents
python scripts/check_qdrant.py --search "باقة WE Mix"

# Full health check
python scripts/check_qdrant.py --health

# Delete collection (requires --confirm)
python scripts/check_qdrant.py --collection test_docs --delete --confirm
```

---

### `ingest_te_website.py` - TE Website Scraper

Scrapes and ingests content from te.eg website.

#### Usage

```bash
# Scrape and ingest with default settings
python scripts/ingest_te_website.py

# Clear existing data before scraping
python scripts/ingest_te_website.py --clear

# Custom delay between requests
python scripts/ingest_te_website.py --delay 2.0
```

#### Options

- `--clear`: Clear existing collection before ingesting
- `--delay`: Delay between requests in seconds (default: 1.0)

---

## Common Workflows

### Adding New Documents

1. **From JSON file**:
   ```bash
   # Preview first
   python scripts/ingest_json.py --file my_data.json --dry-run

   # Then ingest
   python scripts/ingest_json.py --file my_data.json
   ```

2. **From te.eg website**:
   ```bash
   python scripts/ingest_te_website.py --clear
   ```

### Sharing Data with Coworkers

```bash
# Export your collection
python scripts/export_qdrant.py --output shared_data.json

# Send the JSON file to your coworker

# Coworker imports the data
python scripts/ingest_json.py --file shared_data.json
```

### Creating Backups

```bash
# Export current data with timestamp
python scripts/export_qdrant.py --output backup_$(date +%Y%m%d).json

# Include conversation history (optional)
python scripts/export_qdrant.py --output backup_full.json --include-memory
```

### Replacing All Data

```bash
# Clear and ingest fresh data
python scripts/ingest_json.py --file new_dataset.json --clear
```

### Testing Changes

```bash
# Export small sample for testing
python scripts/export_qdrant.py --output test_sample.json --limit 50

# Use dry-run to verify JSON format
python scripts/ingest_json.py --file test_data.json --dry-run

# Ingest to test collection
python scripts/ingest_json.py --file test_data.json --collection test_docs
```

---

## Troubleshooting

### Qdrant Connection Error

**Error**: `Connection refused` or `Qdrant not available`

**Solution**:
```bash
# Start Qdrant with Docker Compose
docker-compose up -d qdrant

# Or use dry-run mode (doesn't need Qdrant)
python scripts/ingest_json.py --file data.json --dry-run
```

### Module Not Found Error

**Error**: `ModuleNotFoundError: No module named 'X'`

**Solution**:
```bash
# Install dependencies with uv
uv pip install -e ".[dev]"

# Or use uv run (automatically manages environment)
uv run python scripts/ingest_json.py --file data.json
```

### JSON Format Error

**Error**: `Could not auto-detect JSON format`

**Solution**:
- Check JSON structure matches supported formats
- Use `--format` flag to specify format explicitly
- Ensure JSON has required fields (`text` for generic, `pages` with `text` for firecrawl)

### Empty Text Warning

**Warning**: `Skipping page X: no text content`

**Solution**:
- This is expected for pages without content
- The script will skip these and continue with valid pages
- Check source data if all pages are being skipped

---

## Development

### Adding New Formats

To add support for a new JSON format:

1. Add format name to `SUPPORTED_FORMATS` in `JSONIngester`
2. Create extraction method: `extract_<format_name>()`
3. Add detection logic to `detect_format()`
4. Update documentation

### Running Tests

```bash
# Test with sample data
uv run python scripts/ingest_json.py --file data/sample_firecrawl.json --dry-run
uv run python scripts/ingest_json.py --file data/sample_generic.json --dry-run

# Test error handling
uv run python scripts/ingest_json.py --file data/nonexistent.json
```

---

## Best Practices

1. **Always preview first**: Use `--dry-run` to check data before ingesting
2. **Use batch processing**: For large files, adjust `--batch-size` for optimal performance
3. **Clear selectively**: Only use `--clear` when replacing all data
4. **Monitor progress**: Check progress bar for long-running ingestion
5. **Verify ingestion**: Test chatbot after ingestion to ensure data is searchable
