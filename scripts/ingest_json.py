#!/usr/bin/env python3
"""
Ingest JSON data into the RAG vector store.

Supports multiple JSON formats:
- Firecrawl: {"pages": [{"url", "title", "text"}]}
- Generic: [{"text": "...", "metadata": {...}}]
- Auto-detection based on structure

Usage:
    python scripts/ingest_json.py --file data.json
    python scripts/ingest_json.py --file data.json --format firecrawl --clear
    python scripts/ingest_json.py --file data.json --dry-run
    python scripts/ingest_json.py --file data.json --collection custom_docs

Options:
    --file PATH         Path to JSON file to ingest (required)
    --format FORMAT     JSON format: firecrawl, generic, auto (default: auto)
    --clear             Clear existing collection before ingesting
    --dry-run           Preview ingestion without actually processing
    --collection NAME   Custom collection name (default: from settings)
    --batch-size SIZE   Batch size for ingestion (default: 10)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from tqdm import tqdm

from src.core.pipeline import RAGPipeline
from src.preprocessing.chunker import ArabicSentenceChunker


class JSONFormatError(Exception):
    """Raised when JSON format is invalid or unsupported."""

    pass


class JSONIngester:
    """Handles JSON data ingestion into the RAG vector store."""

    SUPPORTED_FORMATS = ["firecrawl", "generic", "auto"]

    def __init__(
        self,
        pipeline: Optional[RAGPipeline] = None,
        batch_size: int = 10,
    ):
        """
        Initialize JSON ingester.

        Args:
            pipeline: RAG pipeline instance (optional for dry-run mode)
            batch_size: Number of documents to process in each batch
        """
        self.pipeline = pipeline
        self.batch_size = batch_size
        self.chunker = ArabicSentenceChunker()

    def load_json(self, file_path: Path) -> Dict[str, Any]:
        """
        Load and validate JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Loaded JSON data

        Raises:
            JSONFormatError: If JSON is invalid or cannot be loaded
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            raise JSONFormatError(f"Invalid JSON file: {e}")
        except FileNotFoundError:
            raise JSONFormatError(f"File not found: {file_path}")
        except Exception as e:
            raise JSONFormatError(f"Error loading JSON: {e}")

    def detect_format(self, data: Union[Dict[str, Any], List[Dict]]) -> str:
        """
        Auto-detect JSON format.

        Args:
            data: Loaded JSON data

        Returns:
            Detected format: 'firecrawl' or 'generic'

        Raises:
            JSONFormatError: If format cannot be detected
        """
        # Check for Firecrawl format: {"pages": [...]}
        if isinstance(data, dict) and "pages" in data:
            if isinstance(data["pages"], list):
                return "firecrawl"

        # Check for Generic format: [{"text": "...", ...}]
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict) and "text" in first_item:
                return "generic"

        raise JSONFormatError(
            "Could not auto-detect JSON format. "
            "Expected Firecrawl format: {'pages': [{'url', 'title', 'text'}]} "
            "or Generic format: [{'text': '...', 'metadata': {...}}]"
        )

    def extract_firecrawl(self, data: Dict[str, Any]) -> Tuple[List[str], List[Dict]]:
        """
        Extract documents from Firecrawl format.

        Expected format:
        {
            "pages": [
                {"url": "...", "title": "...", "text": "..."}
            ]
        }

        Args:
            data: Firecrawl JSON data

        Returns:
            Tuple of (texts, metadatas)

        Raises:
            JSONFormatError: If required fields are missing
        """
        if "pages" not in data:
            raise JSONFormatError("Firecrawl format missing 'pages' field")

        pages = data["pages"]
        if not isinstance(pages, list):
            raise JSONFormatError("'pages' must be a list")

        texts = []
        metadatas = []

        for i, page in enumerate(pages):
            if not isinstance(page, dict):
                logger.warning(f"Skipping page {i}: not a dictionary")
                continue

            # Extract text (required)
            text = page.get("text", "").strip()
            if not text:
                logger.warning(f"Skipping page {i} ({page.get('url', 'unknown')}): no text content")
                continue

            # Extract metadata
            metadata = {
                "url": page.get("url", ""),
                "title": page.get("title", ""),
                "source": "firecrawl",
            }

            # Add any additional fields as metadata
            for key, value in page.items():
                if key not in ["text", "url", "title"]:
                    metadata[key] = value

            texts.append(text)
            metadatas.append(metadata)

        if not texts:
            raise JSONFormatError("No valid documents found in Firecrawl data")

        return texts, metadatas

    def extract_generic(self, data: List[Dict]) -> Tuple[List[str], List[Dict]]:
        """
        Extract documents from Generic format.

        Expected format:
        [
            {"text": "...", "metadata": {...}},
            {"text": "...", "metadata": {...}}
        ]

        Args:
            data: Generic JSON data

        Returns:
            Tuple of (texts, metadatas)

        Raises:
            JSONFormatError: If required fields are missing
        """
        if not isinstance(data, list):
            raise JSONFormatError("Generic format must be a list")

        texts = []
        metadatas = []

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                logger.warning(f"Skipping item {i}: not a dictionary")
                continue

            # Extract text (required)
            text = item.get("text", "").strip()
            if not text:
                logger.warning(f"Skipping item {i}: no text content")
                continue

            # Extract metadata (optional)
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            # Add source identifier
            metadata["source"] = metadata.get("source", "json")

            texts.append(text)
            metadatas.append(metadata)

        if not texts:
            raise JSONFormatError("No valid documents found in Generic data")

        return texts, metadatas

    def extract_documents(
        self, data: Union[Dict[str, Any], List[Dict]], format_type: str
    ) -> Tuple[List[str], List[Dict]]:
        """
        Extract documents based on format type.

        Args:
            data: Loaded JSON data
            format_type: Format type ('firecrawl', 'generic', or 'auto')

        Returns:
            Tuple of (texts, metadatas)

        Raises:
            JSONFormatError: If format is invalid or extraction fails
        """
        # Auto-detect if needed
        if format_type == "auto":
            format_type = self.detect_format(data)
            logger.info(f"✅ Auto-detected format: {format_type}")

        # Extract based on format
        if format_type == "firecrawl":
            if not isinstance(data, dict):
                raise JSONFormatError("Firecrawl format requires a dictionary")
            return self.extract_firecrawl(data)
        elif format_type == "generic":
            if not isinstance(data, list):
                raise JSONFormatError("Generic format requires a list")
            return self.extract_generic(data)
        else:
            raise JSONFormatError(f"Unsupported format: {format_type}")

    def preview_documents(
        self, texts: List[str], metadatas: List[Dict], max_preview: int = 5
    ) -> None:
        """
        Preview documents that would be ingested.

        Args:
            texts: Document texts
            metadatas: Document metadata
            max_preview: Maximum number of documents to preview
        """
        print(f"\n📄 Found {len(texts)} documents to ingest\n")
        print("[DRY RUN] Would ingest:\n")

        for i, (text, metadata) in enumerate(zip(texts[:max_preview], metadatas[:max_preview])):
            title = metadata.get("title", metadata.get("source", f"Document {i+1}"))
            char_count = len(text)
            print(f'  - Document {i+1}: "{title}" ({char_count:,} chars)')

            # Show first 100 chars of text
            preview_text = text[:100].replace("\n", " ")
            if len(text) > 100:
                preview_text += "..."
            print(f"    Preview: {preview_text}")
            print()

        if len(texts) > max_preview:
            print(f"  ... and {len(texts) - max_preview} more documents\n")

    def calculate_chunks(self, texts: List[str]) -> int:
        """
        Calculate total number of chunks that will be created.

        Args:
            texts: Document texts

        Returns:
            Total number of chunks
        """
        total_chunks = 0
        for text in texts:
            chunks = self.chunker.chunk(text)
            total_chunks += len(chunks)
        return total_chunks

    def ingest_with_progress(
        self, texts: List[str], metadatas: List[Dict], show_progress: bool = True
    ) -> Tuple[int, int, float]:
        """
        Ingest documents with progress tracking.

        Args:
            texts: Document texts
            metadatas: Document metadata
            show_progress: Whether to show progress bar

        Returns:
            Tuple of (documents_ingested, chunks_created, time_taken)

        Raises:
            ValueError: If pipeline is not initialized
        """
        if self.pipeline is None:
            raise ValueError("Pipeline not initialized. Cannot ingest in dry-run mode.")

        start_time = time.time()

        # Calculate chunks before ingestion
        logger.info("📊 Calculating chunks...")
        total_chunks = self.calculate_chunks(texts)

        # Ingest in batches
        logger.info("🚀 Ingesting documents...")

        pbar = None
        if show_progress:
            pbar = tqdm(
                total=len(texts),
                desc="Progress",
                unit="docs",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            )

        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i : i + self.batch_size]
            batch_metadatas = metadatas[i : i + self.batch_size]

            # Ingest batch
            self.pipeline.ingest_documents(texts=batch_texts, metadatas=batch_metadatas)

            if show_progress and pbar is not None:
                pbar.update(len(batch_texts))

        if show_progress and pbar is not None:
            pbar.close()

        time_taken = time.time() - start_time

        return len(texts), total_chunks, time_taken


def main() -> int:
    """Main ingestion function."""
    parser = argparse.ArgumentParser(
        description="Ingest JSON data into RAG vector store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect format and ingest
  python scripts/ingest_json.py --file data.json

  # Specify format and clear existing data
  python scripts/ingest_json.py --file data.json --format firecrawl --clear

  # Preview without ingesting
  python scripts/ingest_json.py --file data.json --dry-run

  # Use custom collection
  python scripts/ingest_json.py --file data.json --collection custom_docs

Supported formats:
  - firecrawl: {"pages": [{"url", "title", "text"}]}
  - generic: [{"text": "...", "metadata": {...}}]
  - auto: Auto-detect format (default)
        """,
    )

    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Path to JSON file to ingest",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=JSONIngester.SUPPORTED_FORMATS,
        default="auto",
        help="JSON format (default: auto-detect)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collection before ingesting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview ingestion without actually processing",
    )
    parser.add_argument(
        "--collection",
        type=str,
        help="Custom collection name (default: from settings)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for ingestion (default: 10)",
    )

    args = parser.parse_args()

    try:
        # Validate file path
        if not args.file.exists():
            logger.error(f"❌ File not found: {args.file}")
            return 1

        print(f"\n📥 Loading JSON from: {args.file}")

        # For dry-run, we don't need to initialize pipeline
        if args.dry_run:
            # Create temporary ingester without pipeline
            temp_ingester = JSONIngester(pipeline=None, batch_size=args.batch_size)

            # Load JSON
            try:
                data = temp_ingester.load_json(args.file)
            except JSONFormatError as e:
                logger.error(f"❌ {e}")
                return 1

            # Extract documents
            try:
                texts, metadatas = temp_ingester.extract_documents(data, args.format)
            except JSONFormatError as e:
                logger.error(f"❌ {e}")
                return 1

            # Preview documents
            temp_ingester.preview_documents(texts, metadatas)
            chunks = temp_ingester.calculate_chunks(texts)
            print(f"📊 Statistics:")
            print(f"  - Documents: {len(texts)}")
            print(f"  - Estimated chunks: {chunks}")
            print(f"  - Batch size: {args.batch_size}")
            print(f"\n💡 Run without --dry-run to actually ingest these documents\n")
            return 0

        # Initialize pipeline (only for actual ingestion)
        logger.info("Initializing RAG pipeline...")
        pipeline = RAGPipeline()

        # Initialize ingester
        ingester = JSONIngester(pipeline=pipeline, batch_size=args.batch_size)

        # Load JSON
        try:
            data = ingester.load_json(args.file)
        except JSONFormatError as e:
            logger.error(f"❌ {e}")
            return 1

        # Extract documents
        try:
            texts, metadatas = ingester.extract_documents(data, args.format)
        except JSONFormatError as e:
            logger.error(f"❌ {e}")
            return 1

        # Clear collection if requested
        if args.clear:
            logger.warning("⚠️  Clearing existing collection...")
            pipeline.clear_collection()

        # Ingest documents
        docs_count, chunks_count, time_taken = ingester.ingest_with_progress(
            texts=texts,
            metadatas=metadatas,
            show_progress=True,
        )

        # Print summary
        print(f"\n✅ Ingestion complete!")
        print(f"  - Documents: {docs_count}")
        print(f"  - Chunks created: {chunks_count}")
        print(f"  - Time: {time_taken:.1f}s")
        print(f"  - Rate: {docs_count/time_taken:.2f} docs/s")
        print(f"\n💡 Run 'streamlit run streamlit_app/app.py' to test the chatbot\n")

        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Ingestion interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.exception("Traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
