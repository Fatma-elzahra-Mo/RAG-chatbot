"""
Manual demonstration of TextExtractor capabilities.

Run this script to see the TextExtractor in action with various text samples.
"""

import io
from src.preprocessing.extractors.text import TextExtractor


def demo_utf8_arabic():
    """Demo: Arabic text in UTF-8."""
    print("\n" + "=" * 60)
    print("DEMO 1: Arabic Text (UTF-8)")
    print("=" * 60)

    content = """
# دليل المستخدم

## المقدمة
هذا دليل استخدام النظام.

### الميزات الرئيسية

١. سهولة الاستخدام
٢. الأداء العالي
٣. الأمان المتقدم

• دعم اللغة العربية
• واجهة سهلة
• تحديثات منتظمة
""".encode(
        "utf-8"
    )

    extractor = TextExtractor()
    result = extractor.extract(io.BytesIO(content), "user_guide.txt")

    print(f"Detected Encoding: {result.metadata['detected_encoding']}")
    print(f"Confidence: {result.metadata['encoding_confidence']:.2%}")
    print(f"Line Ending: {result.metadata['line_ending_style']}")
    print(f"Has Structure: {result.metadata.get('has_structure', False)}")
    print(f"Numbered Items: {result.metadata.get('num_numbered_items', 0)}")
    print(f"Bullet Items: {result.metadata.get('num_bullet_items', 0)}")
    print(f"Content Type: {result.content_type.value}")
    print(f"\nExtracted Text (first 100 chars):\n{result.text[:100]}...")


def demo_windows_line_endings():
    """Demo: Windows CRLF line endings."""
    print("\n" + "=" * 60)
    print("DEMO 2: Windows CRLF Line Endings")
    print("=" * 60)

    content = "Line 1\r\nLine 2\r\nLine 3\r\n".encode("utf-8")

    extractor = TextExtractor()
    result = extractor.extract(io.BytesIO(content), "windows.txt")

    print(f"Detected Encoding: {result.metadata['detected_encoding']}")
    print(f"Line Ending: {result.metadata['line_ending_style']}")
    print(f"Line Count: {result.metadata['line_count']}")
    print(f"Warnings: {result.warnings}")


def demo_utf16():
    """Demo: UTF-16 encoded text."""
    print("\n" + "=" * 60)
    print("DEMO 3: UTF-16 Encoding")
    print("=" * 60)

    content = "Hello from UTF-16! مرحبا".encode("utf-16")

    extractor = TextExtractor()
    result = extractor.extract(io.BytesIO(content), "utf16.txt")

    print(f"Detected Encoding: {result.metadata['detected_encoding']}")
    print(f"Actual Encoding Used: {result.metadata['actual_encoding']}")
    print(f"File Size: {result.metadata['file_size_bytes']} bytes")
    print(f"Character Count: {result.metadata['char_count']}")
    print(f"Extracted Text: {result.text}")


def demo_structured_document():
    """Demo: Structured document with mixed formatting."""
    print("\n" + "=" * 60)
    print("DEMO 4: Structured Document")
    print("=" * 60)

    content = """
PROJECT REQUIREMENTS

1. Introduction
   Background information about the project.

2. Features
   2.1 User Authentication
   2.2 Data Processing
   2.3 Report Generation

3. Requirements
   • Python 3.11+
   • FastAPI
   • PostgreSQL

4. Installation Steps
   1. Clone repository
   2. Install dependencies
   3. Configure environment
   4. Run tests

Conclusion: Follow all steps carefully.
""".encode(
        "utf-8"
    )

    extractor = TextExtractor()
    result = extractor.extract(io.BytesIO(content), "requirements.txt")

    print(f"Has Structure: {result.metadata.get('has_structure', False)}")
    print(f"Has Numbered Sections: {result.metadata.get('has_numbered_sections', False)}")
    print(f"Has Bullet Points: {result.metadata.get('has_bullet_points', False)}")
    print(f"Has Headers: {result.metadata.get('has_headers', False)}")
    print(f"Has Indentation: {result.metadata.get('has_indentation', False)}")
    print(f"Number of Numbered Items: {result.metadata.get('num_numbered_items', 0)}")
    print(f"Number of Bullet Items: {result.metadata.get('num_bullet_items', 0)}")
    print(f"Number of Headers: {result.metadata.get('num_headers', 0)}")
    print(f"Content Type: {result.content_type.value}")


def demo_encoding_fallback():
    """Demo: Encoding fallback mechanism."""
    print("\n" + "=" * 60)
    print("DEMO 5: Encoding Fallback (Invalid Bytes)")
    print("=" * 60)

    # Create bytes that are invalid UTF-8
    content = b"Valid text \xff\xfe then more text"

    extractor = TextExtractor()
    result = extractor.extract(io.BytesIO(content), "corrupted.txt")

    print(f"Detected Encoding: {result.metadata['detected_encoding']}")
    print(f"Actual Encoding Used: {result.metadata['actual_encoding']}")
    print(f"Warnings: {len(result.warnings)}")
    for warning in result.warnings:
        print(f"  - {warning}")
    print(f"Text extracted successfully: {len(result.text)} characters")


def demo_mixed_line_endings():
    """Demo: Mixed line endings detection."""
    print("\n" + "=" * 60)
    print("DEMO 6: Mixed Line Endings")
    print("=" * 60)

    content = b"Unix line\nWindows line\r\nOld Mac line\rAnother Unix\n"

    extractor = TextExtractor()
    result = extractor.extract(io.BytesIO(content), "mixed.txt")

    print(f"Line Ending Style: {result.metadata['line_ending_style']}")
    print(f"Line Count: {result.metadata['line_count']}")
    print(f"Text: {repr(result.text)}")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("TextExtractor Demonstration")
    print("=" * 60)

    demo_utf8_arabic()
    demo_windows_line_endings()
    demo_utf16()
    demo_structured_document()
    demo_encoding_fallback()
    demo_mixed_line_endings()

    print("\n" + "=" * 60)
    print("All demos completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
