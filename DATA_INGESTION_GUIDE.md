# 📚 Data Ingestion & Verification Guide

Complete guide for inserting data into Qdrant and verifying it's there.

---

## 🚀 Quick Start: Insert & Verify Data

### Step 1: Start Qdrant

```bash
# Start Qdrant using Docker
docker-compose up -d qdrant

# Verify Qdrant is running
curl http://localhost:6333/healthz
```

### Step 2: Insert JSON Data

```bash
# Basic ingestion (auto-detects format)
python scripts/ingest_json.py --file data/sample_firecrawl.json

# Dry-run mode (preview without inserting)
python scripts/ingest_json.py --file data/sample_firecrawl.json --dry-run

# Clear existing data before inserting
python scripts/ingest_json.py --file data/sample_firecrawl.json --clear

# Specify format explicitly
python scripts/ingest_json.py --file data/sample_generic.json --format generic
```

### Step 3: Verify Data is in Qdrant

```bash
# Health check (default - shows if everything is working)
python scripts/check_qdrant.py --health

# List all collections
python scripts/check_qdrant.py --list

# Get collection info and document count
python scripts/check_qdrant.py --info

# Show 5 sample documents
python scripts/check_qdrant.py --samples 5

# Search for specific content
python scripts/check_qdrant.py --search "باقة WE Mix"
```

---

## 📊 Script 1: `ingest_json.py` - Insert Data

### Purpose
Inserts JSON data into Qdrant vector database for RAG retrieval.

### Supported Formats

#### 1. Firecrawl Format
```json
{
  "pages": [
    {
      "url": "https://example.com/page1",
      "title": "Page Title",
      "text": "Page content here..."
    }
  ]
}
```

#### 2. Generic Format
```json
[
  {
    "text": "Document content here...",
    "metadata": {
      "source": "document.pdf",
      "page": 1
    }
  }
]
```

### Usage Examples

```bash
# Auto-detect format (recommended)
python scripts/ingest_json.py --file data/my_data.json

# Preview before inserting (dry-run)
python scripts/ingest_json.py --file data/my_data.json --dry-run

# Clear existing collection first
python scripts/ingest_json.py --file data/my_data.json --clear

# Custom collection name
python scripts/ingest_json.py --file data/my_data.json --collection custom_docs

# Specify format explicitly
python scripts/ingest_json.py --file data/my_data.json --format firecrawl

# Custom batch size
python scripts/ingest_json.py --file data/my_data.json --batch-size 20
```

### Output Example

```
================================================================================
JSON INGESTION SUMMARY
================================================================================
Format detected: firecrawl
Documents found: 3
Preview mode: False
Collection: arabic_documents

Processing documents: 100%|███████████████| 3/3 [00:02<00:00, 1.23it/s]

✅ Successfully ingested 3 documents (15 chunks)

Statistics:
- Total documents: 3
- Total chunks: 15
- Average chunk size: 342 characters
- Collection: arabic_documents
================================================================================
```

---

## 🔍 Script 2: `check_qdrant.py` - Verify Data

### Purpose
Check, verify, and inspect data in Qdrant collections.

### Commands

#### 1. Health Check (Recommended First Step)
```bash
python scripts/check_qdrant.py --health
```

**Output:**
```
============================================================
🏥 Qdrant Health Check
============================================================
✅ Qdrant connection: OK
✅ Collections exist: 2 found
✅ Collection 'arabic_documents': Accessible
✅ Documents in collection: 45
============================================================

🎉 All checks passed! System is healthy.
```

#### 2. List All Collections
```bash
python scripts/check_qdrant.py --list
```

**Output:**
```
============================================================
📚 Collections in Qdrant (2 total)
============================================================
  1. arabic_documents (45 documents)
  2. conversation_memory (12 documents)
============================================================
```

#### 3. Get Collection Information
```bash
# Default collection (from settings)
python scripts/check_qdrant.py --info

# Specific collection
python scripts/check_qdrant.py --collection arabic_documents --info
```

**Output:**
```
============================================================
📊 Collection Info: arabic_documents
============================================================
  Status: CollectionStatus.GREEN
  Documents: 45
  Vectors Count: 45
  Points Count: 45
  Indexed Vectors: 45

  Vector Configuration:
    Size: 1024
    Distance: COSINE
============================================================
```

#### 4. View Sample Documents
```bash
# Show 5 samples (default)
python scripts/check_qdrant.py --samples 5

# Show 10 samples
python scripts/check_qdrant.py --samples 10
```

**Output:**
```
============================================================
📄 Sample Documents from arabic_documents (showing 5)
============================================================

--- Sample 1 (ID: 12a3b4c5) ---
Content: باقة WE Mix 200 هي باقة شاملة من WE مصر. السعر الشهري: 200 جنيه مصري...
Metadata:
  - source: WE packages
  - category: Mix
  - price: 200

--- Sample 2 (ID: 45d6e7f8) ---
Content: خدمة سلفني من WE مصر تتيح للمشتركين اقتراض رصيد...
Metadata:
  - source: WE services
  - category: Credit
============================================================
```

#### 5. Search for Documents
```bash
# Search in default collection
python scripts/check_qdrant.py --search "باقة WE Mix"

# Search in specific collection
python scripts/check_qdrant.py --collection arabic_documents --search "5G"
```

**Output:**
```
🔍 Searching for: 'باقة WE Mix' in arabic_documents
============================================================
Found 3 matches

--- Match 1 (ID: 12a3b4c5) ---
Content: باقة WE Mix 200 هي باقة شاملة من WE مصر...
Metadata: {'source': 'WE packages', 'category': 'Mix'}

--- Match 2 (ID: 89g0h1i2) ---
Content: باقة WE Mix 100 هي باقة اقتصادية...
Metadata: {'source': 'WE packages', 'category': 'Mix'}
============================================================
```

#### 6. Delete Collection (Use Carefully!)
```bash
# Preview delete (shows warning)
python scripts/check_qdrant.py --collection test_docs --delete

# Actually delete (requires --confirm)
python scripts/check_qdrant.py --collection test_docs --delete --confirm
```

---

## 🔄 Complete Workflow Example

### Scenario: Ingest WE Egypt telecom data and verify it

```bash
# 1. Start Qdrant
docker-compose up -d qdrant

# 2. Check Qdrant is healthy (before ingestion)
python scripts/check_qdrant.py --health

# 3. Preview data before inserting (dry-run)
python scripts/ingest_json.py --file data/we_egypt_data.json --dry-run

# 4. Insert data (clear old data first)
python scripts/ingest_json.py --file data/we_egypt_data.json --clear

# 5. Verify data was inserted
python scripts/check_qdrant.py --info

# 6. View sample documents
python scripts/check_qdrant.py --samples 3

# 7. Search for specific package
python scripts/check_qdrant.py --search "Mix 200"

# 8. Test query via Python
python tests/qa_agent_2_detailed_report.py
```

---

## 📝 Creating Test Data

### Example 1: Firecrawl Format (Web Scraping)

Create `data/my_firecrawl_data.json`:
```json
{
  "pages": [
    {
      "url": "https://example.com/page1",
      "title": "باقات WE مصر",
      "text": "باقة WE Mix 200 هي باقة شاملة من WE مصر. السعر الشهري: 200 جنيه مصري."
    },
    {
      "url": "https://example.com/page2",
      "title": "خدمة العملاء",
      "text": "أرقام خدمة العملاء WE مصر: من الموبايل: 19777، من الخط الأرضي: 111"
    }
  ]
}
```

### Example 2: Generic Format (Custom Data)

Create `data/my_generic_data.json`:
```json
[
  {
    "text": "باقة WE Mix 200 هي باقة شاملة من WE مصر. السعر الشهري: 200 جنيه مصري.",
    "metadata": {
      "source": "WE website",
      "category": "packages",
      "price": "200"
    }
  },
  {
    "text": "خدمة سلفني من WE مصر تتيح للمشتركين اقتراض رصيد عند نفاد الرصيد.",
    "metadata": {
      "source": "WE services",
      "category": "credit"
    }
  }
]
```

Then ingest:
```bash
python scripts/ingest_json.py --file data/my_generic_data.json
```

---

## 🐛 Troubleshooting

### Issue: "Connection refused" when checking Qdrant
**Solution:** Make sure Qdrant is running
```bash
docker-compose up -d qdrant
# Wait 5 seconds for startup
curl http://localhost:6333/healthz
```

### Issue: "Collection does not exist"
**Solution:** Check collection name or create by ingesting data
```bash
# List all collections
python scripts/check_qdrant.py --list

# Use correct collection name
python scripts/check_qdrant.py --collection arabic_documents --info
```

### Issue: Empty collection (0 documents)
**Solution:** Ingest data first
```bash
python scripts/ingest_json.py --file data/sample_firecrawl.json
```

### Issue: "No module named 'loguru'"
**Solution:** Install dependencies
```bash
uv pip install -e ".[dev]"
```

---

## 🎯 Best Practices

### 1. Always Use Dry-Run First
```bash
# Preview before inserting
python scripts/ingest_json.py --file data/new_data.json --dry-run
```

### 2. Check Collection Before Clearing
```bash
# Check what's there first
python scripts/check_qdrant.py --info

# Then clear if needed
python scripts/ingest_json.py --file data/new_data.json --clear
```

### 3. Verify After Ingestion
```bash
# Ingest
python scripts/ingest_json.py --file data/my_data.json

# Immediately verify
python scripts/check_qdrant.py --health
python scripts/check_qdrant.py --samples 3
```

### 4. Use Descriptive Metadata
```json
{
  "text": "Document content...",
  "metadata": {
    "source": "document.pdf",
    "page": 1,
    "category": "telecom",
    "language": "arabic",
    "date": "2024-01-13"
  }
}
```

### 5. Test Queries After Ingestion
```bash
# Ingest data
python scripts/ingest_json.py --file data/we_data.json

# Test search
python scripts/check_qdrant.py --search "باقة"

# Test with RAG pipeline
python tests/qa_agent_2_detailed_report.py
```

---

## 📚 Additional Resources

- **Qdrant Documentation:** https://qdrant.tech/documentation/
- **Project README:** `README.md`
- **QA Testing Guide:** `tests/qa/README_QA_TESTING.md`
- **Test Scripts:** `tests/qa_agent_2_*.py`

---

## 🎓 Summary

**Two scripts for complete data management:**

1. **`ingest_json.py`** - Insert data into Qdrant
   - Supports Firecrawl and Generic formats
   - Auto-detection
   - Dry-run mode
   - Progress tracking

2. **`check_qdrant.py`** - Verify data in Qdrant
   - Health checks
   - Collection info
   - Sample viewing
   - Search functionality

**Typical workflow:**
```bash
# Start → Insert → Verify → Test
docker-compose up -d qdrant
python scripts/ingest_json.py --file data/my_data.json --dry-run
python scripts/ingest_json.py --file data/my_data.json
python scripts/check_qdrant.py --health
python scripts/check_qdrant.py --samples 5
```

**Ready to use! 🚀**
