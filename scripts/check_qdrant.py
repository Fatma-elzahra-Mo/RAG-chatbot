#!/usr/bin/env python3
"""
Check and verify data in Qdrant vector database.

This utility script helps you:
- List all collections
- Count documents in a collection
- View sample documents
- Search for documents
- Verify collection health
- Check collection configuration

Usage:
    # List all collections
    python scripts/check_qdrant.py --list

    # Check default collection (from settings)
    python scripts/check_qdrant.py --info

    # Check specific collection
    python scripts/check_qdrant.py --collection my_docs --info

    # Show sample documents (first 5)
    python scripts/check_qdrant.py --samples 5

    # Search for documents containing text
    python scripts/check_qdrant.py --search "باقة WE Mix"

    # Full health check
    python scripts/check_qdrant.py --health

    # Delete collection (careful!)
    python scripts/check_qdrant.py --collection my_docs --delete
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from qdrant_client import QdrantClient

from src.config.settings import settings


class QdrantChecker:
    """Utility for checking and verifying Qdrant data."""

    def __init__(self, collection_name: Optional[str] = None):
        """Initialize Qdrant checker.

        Args:
            collection_name: Collection to check (default: from settings)
        """
        self.collection_name = collection_name or settings.qdrant_collection
        self.client = QdrantClient(url=settings.qdrant_url)
        logger.info(f"Connected to Qdrant at {settings.qdrant_url}")

    def list_collections(self) -> List[str]:
        """List all collections in Qdrant.

        Returns:
            List of collection names
        """
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            print("\n" + "=" * 60)
            print(f"📚 Collections in Qdrant ({len(collection_names)} total)")
            print("=" * 60)

            if collection_names:
                for idx, name in enumerate(collection_names, 1):
                    # Get count for each collection
                    try:
                        count = self.client.count(collection_name=name).count
                        print(f"  {idx}. {name} ({count:,} documents)")
                    except Exception:
                        print(f"  {idx}. {name} (unable to get count)")
            else:
                print("  No collections found.")

            print("=" * 60 + "\n")
            return collection_names

        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            print(f"❌ Error: {e}")
            return []

    def get_collection_info(self) -> Dict[str, Any]:
        """Get detailed information about the collection.

        Returns:
            Dictionary with collection info
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                print(f"\n❌ Collection '{self.collection_name}' does not exist.")
                print(f"   Available collections: {', '.join(collection_names) or 'None'}")
                return {}

            # Get collection info
            info = self.client.get_collection(collection_name=self.collection_name)
            count = self.client.count(collection_name=self.collection_name).count

            print("\n" + "=" * 60)
            print(f"📊 Collection Info: {self.collection_name}")
            print("=" * 60)
            print(f"  Status: {info.status}")
            print(f"  Documents: {count:,}")

            # Handle different Qdrant API versions
            if hasattr(info, 'vectors_count'):
                print(f"  Vectors Count: {info.vectors_count:,}")
            if hasattr(info, 'points_count'):
                print(f"  Points Count: {info.points_count:,}")
            if hasattr(info, 'indexed_vectors_count'):
                print(f"  Indexed Vectors: {info.indexed_vectors_count:,}")

            if info.config and info.config.params:
                print(f"\n  Vector Configuration:")
                if hasattr(info.config.params, "vectors"):
                    vectors_config = info.config.params.vectors
                    if isinstance(vectors_config, dict):
                        for vec_name, vec_params in vectors_config.items():
                            print(f"    - {vec_name}:")
                            if hasattr(vec_params, 'size'):
                                print(f"      Size: {vec_params.size}")
                            if hasattr(vec_params, 'distance'):
                                print(f"      Distance: {vec_params.distance}")
                    else:
                        if hasattr(vectors_config, 'size'):
                            print(f"    Size: {vectors_config.size}")
                        if hasattr(vectors_config, 'distance'):
                            print(f"    Distance: {vectors_config.distance}")

            print("=" * 60 + "\n")

            result = {
                "name": self.collection_name,
                "status": str(info.status),
                "count": count,
            }

            # Add optional fields if available
            if hasattr(info, 'vectors_count'):
                result["vectors_count"] = info.vectors_count
            if hasattr(info, 'points_count'):
                result["points_count"] = info.points_count

            return result

        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            print(f"❌ Error: {e}")
            return {}

    def get_samples(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample documents from the collection.

        Args:
            limit: Number of samples to retrieve

        Returns:
            List of sample documents
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                print(f"\n❌ Collection '{self.collection_name}' does not exist.")
                return []

            # Scroll to get samples
            records, _ = self.client.scroll(
                collection_name=self.collection_name, limit=limit, with_payload=True, with_vectors=False
            )

            print("\n" + "=" * 60)
            print(f"📄 Sample Documents from {self.collection_name} (showing {len(records)})")
            print("=" * 60)

            samples = []
            for idx, record in enumerate(records, 1):
                payload = record.payload or {}
                print(f"\n--- Sample {idx} (ID: {record.id}) ---")

                # Show page_content or text
                content = payload.get("page_content", payload.get("text", ""))
                if content:
                    preview = content[:150] + "..." if len(content) > 150 else content
                    print(f"Content: {preview}")

                # Show metadata
                metadata = payload.get("metadata", {})
                if metadata:
                    print(f"Metadata:")
                    for key, value in metadata.items():
                        print(f"  - {key}: {value}")

                # Show session_id if exists (for conversation memory)
                if "session_id" in payload:
                    print(f"Session ID: {payload['session_id']}")

                samples.append({"id": str(record.id), "payload": payload})

            print("\n" + "=" * 60 + "\n")
            return samples

        except Exception as e:
            logger.error(f"Error getting samples: {e}")
            print(f"❌ Error: {e}")
            return []

    def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for documents containing specific text.

        Args:
            query: Search query text
            limit: Number of results to return

        Returns:
            List of matching documents
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                print(f"\n❌ Collection '{self.collection_name}' does not exist.")
                return []

            print(f"\n🔍 Searching for: '{query}' in {self.collection_name}")
            print("=" * 60)

            # Use scroll with filter (simpler than semantic search for text matching)
            all_records, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,  # Get more to search through
                with_payload=True,
                with_vectors=False,
            )

            # Filter records containing query text
            matches = []
            query_lower = query.lower()

            for record in all_records:
                payload = record.payload or {}
                content = payload.get("page_content", payload.get("text", ""))

                if query_lower in content.lower():
                    matches.append(record)
                    if len(matches) >= limit:
                        break

            print(f"Found {len(matches)} matches\n")

            results = []
            for idx, record in enumerate(matches, 1):
                payload = record.payload or {}
                content = payload.get("page_content", payload.get("text", ""))

                print(f"--- Match {idx} (ID: {record.id}) ---")

                # Highlight the query in content
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"Content: {preview}")

                metadata = payload.get("metadata", {})
                if metadata:
                    print(f"Metadata: {metadata}")

                print()

                results.append({"id": str(record.id), "payload": payload, "content": content})

            print("=" * 60 + "\n")
            return results

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            print(f"❌ Error: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Dictionary with health status
        """
        print("\n" + "=" * 60)
        print("🏥 Qdrant Health Check")
        print("=" * 60)

        health = {
            "qdrant_connected": False,
            "collections_exist": False,
            "collection_accessible": False,
            "documents_exist": False,
        }

        # 1. Check Qdrant connection
        try:
            collections = self.client.get_collections()
            health["qdrant_connected"] = True
            print("✅ Qdrant connection: OK")
        except Exception as e:
            print(f"❌ Qdrant connection: FAILED - {e}")
            return health

        # 2. Check collections exist
        collection_names = [col.name for col in collections.collections]
        if collection_names:
            health["collections_exist"] = True
            print(f"✅ Collections exist: {len(collection_names)} found")
        else:
            print("⚠️  No collections found")

        # 3. Check specific collection
        if self.collection_name in collection_names:
            health["collection_accessible"] = True
            print(f"✅ Collection '{self.collection_name}': Accessible")

            # 4. Check document count
            try:
                count = self.client.count(collection_name=self.collection_name).count
                if count > 0:
                    health["documents_exist"] = True
                    print(f"✅ Documents in collection: {count:,}")
                else:
                    print("⚠️  Collection is empty (0 documents)")
            except Exception as e:
                print(f"❌ Error counting documents: {e}")
        else:
            print(f"⚠️  Collection '{self.collection_name}' not found")

        print("=" * 60 + "\n")

        # Summary
        all_good = all(health.values())
        if all_good:
            print("🎉 All checks passed! System is healthy.\n")
        else:
            print("⚠️  Some checks failed. Review the output above.\n")

        return health

    def delete_collection(self, confirm: bool = False) -> bool:
        """Delete the collection.

        Args:
            confirm: Must be True to actually delete

        Returns:
            True if deleted successfully
        """
        if not confirm:
            print(f"\n⚠️  Delete operation requires confirmation.")
            print(f"   Add --confirm flag to actually delete '{self.collection_name}'")
            return False

        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                print(f"\n❌ Collection '{self.collection_name}' does not exist.")
                return False

            # Get count before deleting
            count = self.client.count(collection_name=self.collection_name).count

            # Delete
            self.client.delete_collection(collection_name=self.collection_name)

            print(f"\n✅ Collection '{self.collection_name}' deleted successfully.")
            print(f"   Removed {count:,} documents.")
            return True

        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            print(f"❌ Error: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check and verify data in Qdrant vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all collections
  python scripts/check_qdrant.py --list

  # Check collection info
  python scripts/check_qdrant.py --info

  # Show 10 sample documents
  python scripts/check_qdrant.py --samples 10

  # Search for documents
  python scripts/check_qdrant.py --search "باقة WE Mix"

  # Full health check
  python scripts/check_qdrant.py --health

  # Delete collection (requires --confirm)
  python scripts/check_qdrant.py --collection test_docs --delete --confirm
        """,
    )

    parser.add_argument("--collection", type=str, help="Collection name (default: from settings)")

    parser.add_argument("--list", action="store_true", help="List all collections")

    parser.add_argument("--info", action="store_true", help="Show collection information")

    parser.add_argument("--samples", type=int, metavar="N", help="Show N sample documents")

    parser.add_argument(
        "--search", type=str, metavar="QUERY", help="Search for documents containing text"
    )

    parser.add_argument("--health", action="store_true", help="Perform health check")

    parser.add_argument("--delete", action="store_true", help="Delete collection")

    parser.add_argument(
        "--confirm", action="store_true", help="Confirm destructive operations (required for --delete)"
    )

    args = parser.parse_args()

    # Create checker
    checker = QdrantChecker(collection_name=args.collection)

    # Execute commands
    executed = False

    if args.list:
        checker.list_collections()
        executed = True

    if args.info:
        checker.get_collection_info()
        executed = True

    if args.samples is not None:
        checker.get_samples(limit=args.samples)
        executed = True

    if args.search:
        checker.search_documents(query=args.search)
        executed = True

    if args.health:
        checker.health_check()
        executed = True

    if args.delete:
        checker.delete_collection(confirm=args.confirm)
        executed = True

    # Default action: show info
    if not executed:
        print("\n💡 No action specified. Running default health check...\n")
        checker.health_check()
        print("💡 Use --help to see all available options.\n")


if __name__ == "__main__":
    main()
