#!/usr/bin/env python3
"""
Export data from Qdrant vector database to JSON file.

This script exports all documents from a Qdrant collection to a JSON file
that can be shared with others and re-imported using ingest_json.py.

Usage:
    # Export default collection to file
    python scripts/export_qdrant.py --output exported_data.json

    # Export specific collection
    python scripts/export_qdrant.py --collection my_docs --output my_data.json

    # Export in specific format (firecrawl or generic)
    python scripts/export_qdrant.py --output data.json --format generic

    # Export with limit (only first N documents)
    python scripts/export_qdrant.py --output sample.json --limit 100

    # Include conversation memory (session data)
    python scripts/export_qdrant.py --output data.json --include-memory

Options:
    --collection NAME   Collection to export (default: from settings)
    --output PATH       Output JSON file path (required)
    --format FORMAT     Output format: generic, firecrawl (default: generic)
    --limit N           Limit number of documents to export
    --include-memory    Include conversation memory documents
    --batch-size SIZE   Batch size for pagination (default: 100)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from qdrant_client import QdrantClient
from tqdm import tqdm

from src.config.settings import settings


class QdrantExporter:
    """Export data from Qdrant to JSON file."""

    SUPPORTED_FORMATS = ["generic", "firecrawl"]

    def __init__(
        self,
        collection_name: Optional[str] = None,
        include_memory: bool = False,
        batch_size: int = 100,
    ):
        """
        Initialize Qdrant exporter.

        Args:
            collection_name: Collection to export (default: from settings)
            include_memory: Include conversation memory documents
            batch_size: Batch size for pagination
        """
        self.collection_name = collection_name or settings.qdrant_collection
        self.include_memory = include_memory
        self.batch_size = batch_size
        self.client = QdrantClient(url=settings.qdrant_url)

    def check_collection_exists(self) -> bool:
        """
        Check if collection exists in Qdrant.

        Returns:
            True if collection exists
        """
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            return self.collection_name in collection_names
        except Exception as e:
            logger.error(f"Error checking collections: {e}")
            return False

    def get_document_count(self) -> int:
        """
        Get total document count in collection.

        Returns:
            Total number of documents
        """
        try:
            if self.include_memory:
                # Count all documents
                count = self.client.count(collection_name=self.collection_name).count
            else:
                # Count only non-memory documents (filter out session_id documents)
                # This is tricky - we'll need to scroll through and count manually
                # For now, we'll get the total count
                count = self.client.count(collection_name=self.collection_name).count
            return count
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            return 0

    def export_documents(
        self, limit: Optional[int] = None, show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Export documents from Qdrant.

        Args:
            limit: Maximum number of documents to export (None = all)
            show_progress: Show progress bar

        Returns:
            List of documents with text and metadata
        """
        documents = []
        offset = None
        total_fetched = 0

        # Get total count for progress bar
        total_count = self.get_document_count()
        if limit and limit < total_count:
            total_count = limit

        pbar = None
        if show_progress:
            pbar = tqdm(
                total=total_count,
                desc="Exporting",
                unit="docs",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            )

        try:
            while True:
                # Scroll through documents
                records, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=self.batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not records:
                    break

                # Process records
                for record in records:
                    payload = record.payload or {}

                    # Skip conversation memory unless requested
                    if not self.include_memory and "session_id" in payload:
                        # This is a conversation memory entry
                        continue

                    # Extract text and metadata
                    text = payload.get("page_content", payload.get("text", ""))
                    if not text:
                        logger.warning(f"Skipping document {record.id}: no text content")
                        continue

                    metadata = payload.get("metadata", {})

                    # Add document
                    documents.append({"text": text, "metadata": metadata})

                    total_fetched += 1

                    # Update progress
                    if pbar:
                        pbar.update(1)

                    # Check limit
                    if limit and total_fetched >= limit:
                        break

                # Check if done
                if not next_offset or (limit and total_fetched >= limit):
                    break

                offset = next_offset

            if pbar:
                pbar.close()

        except Exception as e:
            logger.error(f"Error exporting documents: {e}")
            if pbar:
                pbar.close()
            raise

        return documents

    def format_as_generic(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format documents in generic format.

        Format: [{"text": "...", "metadata": {...}}]

        Args:
            documents: List of documents

        Returns:
            Documents in generic format
        """
        return documents

    def format_as_firecrawl(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format documents in Firecrawl format.

        Format: {"pages": [{"url": "...", "title": "...", "text": "..."}]}

        Args:
            documents: List of documents

        Returns:
            Documents in Firecrawl format
        """
        pages = []
        for doc in documents:
            metadata = doc.get("metadata", {})
            page = {
                "url": metadata.get("url", metadata.get("source", "")),
                "title": metadata.get("title", ""),
                "text": doc["text"],
            }
            # Include any extra metadata fields
            for key, value in metadata.items():
                if key not in ["url", "title", "source"]:
                    page[key] = value

            pages.append(page)

        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "pages_scraped": len(pages),
            "pages": pages,
        }

    def save_to_file(
        self, documents: List[Dict[str, Any]], output_path: Path, format_type: str
    ) -> bool:
        """
        Save documents to JSON file.

        Args:
            documents: List of documents
            output_path: Output file path
            format_type: Output format (generic or firecrawl)

        Returns:
            True if saved successfully
        """
        try:
            # Format documents
            if format_type == "firecrawl":
                data = self.format_as_firecrawl(documents)
            else:  # generic
                data = self.format_as_generic(documents)

            # Save to file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error(f"Error saving to file: {e}")
            return False


def main() -> int:
    """Main export function."""
    parser = argparse.ArgumentParser(
        description="Export data from Qdrant to JSON file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export default collection to file
  python scripts/export_qdrant.py --output exported_data.json

  # Export specific collection
  python scripts/export_qdrant.py --collection my_docs --output my_data.json

  # Export in Firecrawl format
  python scripts/export_qdrant.py --output data.json --format firecrawl

  # Export only first 100 documents
  python scripts/export_qdrant.py --output sample.json --limit 100

  # Include conversation memory
  python scripts/export_qdrant.py --output full_data.json --include-memory

Formats:
  - generic: [{"text": "...", "metadata": {...}}]
  - firecrawl: {"pages": [{"url", "title", "text"}]}
        """,
    )

    parser.add_argument(
        "--collection", type=str, help="Collection to export (default: from settings)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSON file path",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=QdrantExporter.SUPPORTED_FORMATS,
        default="generic",
        help="Output format (default: generic)",
    )

    parser.add_argument(
        "--limit", type=int, help="Limit number of documents to export (default: all)"
    )

    parser.add_argument(
        "--include-memory",
        action="store_true",
        help="Include conversation memory documents",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for pagination (default: 100)",
    )

    args = parser.parse_args()

    try:
        # Create exporter
        exporter = QdrantExporter(
            collection_name=args.collection,
            include_memory=args.include_memory,
            batch_size=args.batch_size,
        )

        # Check collection exists
        if not exporter.check_collection_exists():
            logger.error(f"❌ Collection '{exporter.collection_name}' does not exist")
            print(f"\n❌ Collection '{exporter.collection_name}' not found.")
            print("   Use --collection to specify a different collection.")
            print("   Run 'python scripts/check_qdrant.py --list' to see available collections.\n")
            return 1

        # Get document count
        total_count = exporter.get_document_count()
        export_count = args.limit if args.limit and args.limit < total_count else total_count

        print(f"\n📤 Exporting from Qdrant")
        print(f"  Collection: {exporter.collection_name}")
        print(f"  Total documents: {total_count:,}")
        print(f"  Exporting: {export_count:,}")
        print(f"  Format: {args.format}")
        print(f"  Output: {args.output}")
        if args.include_memory:
            print(f"  Including conversation memory: Yes")
        print()

        # Export documents
        start_time = time.time()
        documents = exporter.export_documents(limit=args.limit, show_progress=True)
        time_taken = time.time() - start_time

        if not documents:
            logger.warning("⚠️  No documents exported")
            print("\n⚠️  No documents found to export.")
            return 1

        # Save to file
        print(f"\n💾 Saving to {args.output}...")
        if exporter.save_to_file(documents, args.output, args.format):
            file_size = args.output.stat().st_size / 1024  # KB

            print(f"\n✅ Export complete!")
            print(f"  - Documents exported: {len(documents):,}")
            print(f"  - Time: {time_taken:.1f}s")
            print(f"  - Rate: {len(documents)/time_taken:.2f} docs/s")
            print(f"  - File size: {file_size:.1f} KB")
            print(f"\n💡 To import this data:")
            print(f"   python scripts/ingest_json.py --file {args.output}")
            print()
            return 0
        else:
            logger.error("❌ Failed to save to file")
            return 1

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Export interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.exception("Traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
