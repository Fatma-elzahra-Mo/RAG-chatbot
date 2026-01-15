# 🚀 Quick Reference - Data Ingestion & Verification

## ✅ Yes! You have both scripts:

### 1. **Insert Data** → `scripts/ingest_json.py`
### 2. **Check Data** → `scripts/check_qdrant.py` ✨ (just created!)

---

## 🎯 Most Common Commands

### Insert JSON Data
```bash
# Use the virtual environment Python
.venv/bin/python scripts/ingest_json.py --file data/my_data.json
```

### Check if Data is in Qdrant
```bash
# Health check (recommended first)
.venv/bin/python scripts/check_qdrant.py --health

# List all collections
.venv/bin/python scripts/check_qdrant.py --list

# Show collection info with document count
.venv/bin/python scripts/check_qdrant.py --info

# View 5 sample documents
.venv/bin/python scripts/check_qdrant.py --samples 5

# Search for specific text
.venv/bin/python scripts/check_qdrant.py --search "باقة WE Mix"
```

---

## 📊 Live Example Output

### Current Status
```
📚 Collections in Qdrant (2 total)
  1. conversation_history (88 documents)
  2. arabic_documents (16 documents)
```

### Collection Info
```
📊 Collection Info: arabic_documents
  Status: green
  Documents: 16
  Points Count: 16
  Vector Configuration:
    Size: 768
    Distance: Cosine
```

### Sample Documents
```
📄 Sample Documents (showing 3)

--- Sample 1 ---
Content: باقة WE Mix 200 هي باقة شاملة من WE مصر
السعر الشهري: 200 جنيه مصري تشمل الباقة: 50 جيجابايت...

--- Sample 2 ---
Content: باقة WE Mix 100 هي باقة اقتصادية
السعر الشهري: 100 جنيه مصري...

--- Sample 3 ---
Content: خدمة سلفني من WE مصر تتيح للمشتركين اقتراض رصيد...
```

### Search Results
```
🔍 Searching for: 'Mix 200'
Found 2 matches

--- Match 1 (ID: 0) ---
Content: باقة WE Mix 200 هي باقة شاملة...
```

---

## 🔄 Complete Workflow

```bash
# Step 1: Start Qdrant
docker-compose up -d qdrant

# Step 2: Check Qdrant is healthy
.venv/bin/python scripts/check_qdrant.py --health

# Step 3: Insert your data
.venv/bin/python scripts/ingest_json.py --file data/my_data.json

# Step 4: Verify it was inserted
.venv/bin/python scripts/check_qdrant.py --info
.venv/bin/python scripts/check_qdrant.py --samples 3

# Step 5: Search for your data
.venv/bin/python scripts/check_qdrant.py --search "your search term"
```

---

## 📝 Data Format Examples

### Firecrawl Format
```json
{
  "pages": [
    {
      "url": "https://example.com",
      "title": "Page Title",
      "text": "Content here..."
    }
  ]
}
```

### Generic Format
```json
[
  {
    "text": "Document content...",
    "metadata": {
      "source": "document.pdf",
      "category": "telecom"
    }
  }
]
```

---

## 🎓 Tips

1. **Always use `.venv/bin/python`** - ensures correct virtual environment
2. **Health check first** - verify Qdrant is running before ingesting
3. **Use dry-run** - preview data before inserting: `--dry-run`
4. **Check after insert** - always verify with `--info` or `--samples`
5. **Search to test** - use `--search` to confirm your data is retrievable

---

## 📚 Full Documentation

- **Complete Guide:** `DATA_INGESTION_GUIDE.md`
- **QA Testing:** `tests/qa/README_QA_TESTING.md`
- **Project Completion:** `PROJECT_COMPLETION_SUMMARY.md`

---

## ✅ You're Ready!

Both scripts are working and tested:
- ✅ **ingest_json.py** - Insert data (was already there)
- ✅ **check_qdrant.py** - Verify data (just created!)

**Start ingesting and verifying your data now!** 🚀
