"""
Web scraper for te.eg (WE - Telecom Egypt).

Extracts content from te.eg website for RAG indexing.
Handles Arabic content and various page types.
"""

import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger


@dataclass
class ScrapedPage:
    """Represents a scraped page."""

    url: str
    title: str
    content: str
    category: str
    language: str
    metadata: Dict


class TEScraper:
    """
    Web scraper for te.eg (WE - Telecom Egypt).

    Features:
    - Scrapes service pages, plans, support content
    - Handles Arabic and English content
    - Respects rate limits
    - Extracts structured metadata

    Example:
        >>> scraper = TEScraper()
        >>> pages = scraper.scrape_all()
        >>> for page in pages:
        ...     print(f"{page.title}: {len(page.content)} chars")
    """

    BASE_URL = "https://www.te.eg"

    # Main pages to scrape (Arabic site)
    PAGES_TO_SCRAPE = [
        # Home and main sections
        "/ar",
        # Internet services
        "/ar/personal/internet",
        "/ar/personal/internet/home-internet",
        "/ar/personal/internet/we-space",
        "/ar/personal/internet/te-data",
        # Mobile services
        "/ar/personal/mobile",
        "/ar/personal/mobile/prepaid",
        "/ar/personal/mobile/postpaid",
        "/ar/personal/mobile/plans",
        # Landline
        "/ar/personal/landline",
        "/ar/personal/landline/plans",
        # Entertainment
        "/ar/personal/entertainment",
        "/ar/personal/entertainment/we-tv",
        # Support
        "/ar/support",
        "/ar/support/faq",
        "/ar/support/coverage",
        # Business
        "/ar/business",
        "/ar/business/internet",
        "/ar/business/mobile",
        # About
        "/ar/about-we",
        "/ar/about-we/who-we-are",
    ]

    def __init__(
        self,
        delay_between_requests: float = 1.0,
        timeout: float = 30.0,
    ):
        """
        Initialize scraper.

        Args:
            delay_between_requests: Seconds to wait between requests
            timeout: Request timeout in seconds
        """
        self.delay = delay_between_requests
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ArabicRAGBot/1.0; +https://github.com)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ar,en;q=0.5",
            },
        )

    def __del__(self):
        """Close HTTP client."""
        if hasattr(self, "client"):
            self.client.close()

    def scrape_all(self) -> List[ScrapedPage]:
        """
        Scrape all configured pages.

        Returns:
            List of scraped pages
        """
        pages = []
        for path in self.PAGES_TO_SCRAPE:
            url = urljoin(self.BASE_URL, path)
            try:
                page = self.scrape_page(url)
                if page and page.content:
                    pages.append(page)
                    logger.info(f"Scraped: {page.title} ({len(page.content)} chars)")
                time.sleep(self.delay)
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")

        logger.info(f"Scraped {len(pages)} pages total")
        return pages

    def scrape_page(self, url: str) -> Optional[ScrapedPage]:
        """
        Scrape a single page.

        Args:
            url: Page URL to scrape

        Returns:
            ScrapedPage or None if failed
        """
        try:
            response = self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Extract content
            title = self._extract_title(soup)
            content = self._extract_content(soup)
            category = self._categorize_url(url)
            language = "ar" if "/ar/" in url else "en"

            # Extract metadata
            metadata = {
                "url": url,
                "category": category,
                "language": language,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            return ScrapedPage(
                url=url,
                title=title,
                content=content,
                category=category,
                language=language,
                metadata=metadata,
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error scraping {url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try og:title first
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title:
            content = og_title.get("content") if hasattr(og_title, "get") else None
            if content:
                return str(content).strip()

        # Try regular title
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text().strip()

        # Fallback to h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()

        return "Untitled"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from page.

        Removes navigation, footers, scripts, etc.
        """
        # Remove unwanted elements
        for element in soup.find_all(
            ["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]
        ):
            element.decompose()

        # Remove elements by class patterns
        for element in soup.find_all(class_=re.compile(r"nav|menu|footer|header|sidebar|ad|cookie")):
            element.decompose()

        # Try to find main content area
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(class_=re.compile(r"content|main|body"))
            or soup.find("div", class_="container")
        )

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            # Fallback to body
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else ""

        # Clean up text
        text = self._clean_text(text)

        return text

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        # Remove common noise patterns
        noise_patterns = [
            r"جميع الحقوق محفوظة.*",
            r"All rights reserved.*",
            r"تابعنا على.*",
            r"Follow us.*",
            r"اتصل بنا.*",
            r"Contact us.*",
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text.strip()

    def _categorize_url(self, url: str) -> str:
        """Categorize URL by content type."""
        path = urlparse(url).path.lower()

        if "internet" in path:
            return "internet"
        elif "mobile" in path:
            return "mobile"
        elif "landline" in path:
            return "landline"
        elif "entertainment" in path or "tv" in path:
            return "entertainment"
        elif "support" in path or "faq" in path:
            return "support"
        elif "business" in path:
            return "business"
        elif "about" in path:
            return "about"
        else:
            return "general"

    def get_pages_as_documents(self) -> List[Dict]:
        """
        Scrape pages and return as documents for RAG ingestion.

        Returns:
            List of document dicts with text and metadata
        """
        pages = self.scrape_all()
        documents = []

        for page in pages:
            if page.content:
                documents.append(
                    {
                        "text": f"{page.title}\n\n{page.content}",
                        "metadata": {
                            "source": page.url,
                            "title": page.title,
                            "category": page.category,
                            "language": page.language,
                            **page.metadata,
                        },
                    }
                )

        return documents


def scrape_te_website() -> List[Dict]:
    """
    Convenience function to scrape te.eg website.

    Returns:
        List of documents ready for RAG ingestion
    """
    scraper = TEScraper()
    return scraper.get_pages_as_documents()
