"""
HTML Preprocessing Pipeline
Multi-stage preprocessing to reduce HTML to clean, semantic content
"""

from bs4 import BeautifulSoup, Comment
from readability import Document
import re
from typing import Tuple, List


class HTMLPreprocessor:
    """Preprocesses HTML to reduce token count while preserving content"""

    # Tags to completely remove along with their content
    STRIP_TAGS = [
        'script', 'style', 'noscript', 'iframe', 'embed', 'object',
        'svg', 'canvas', 'meta', 'link', 'base'
    ]

    # Navigation and UI elements to remove
    NAV_TAGS = [
        'nav', 'header', 'footer', 'aside', 'form', 'button'
    ]

    # Semantic tags to preserve
    SEMANTIC_TAGS = [
        'article', 'section', 'main', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
        'blockquote', 'pre', 'code', 'a', 'img', 'strong', 'em', 'b', 'i',
        'br', 'hr', 'div', 'span', 'dl', 'dt', 'dd'
    ]

    def __init__(self):
        pass

    def preprocess(self, html: str, url: str = "") -> Tuple[str, dict]:
        """
        Full preprocessing pipeline

        Args:
            html: Raw HTML string
            url: Source URL (for readability)

        Returns:
            Tuple of (cleaned_html, metadata_dict)
        """
        metadata = {
            'original_size': len(html),
            'preprocessing_stages': []
        }

        # Stage 1: Aggressive Stripping
        html = self._stage1_aggressive_strip(html)
        metadata['preprocessing_stages'].append('aggressive_strip')
        metadata['after_stage1_size'] = len(html)

        # Stage 2: Content Isolation (using readability)
        html = self._stage2_content_isolation(html, url)
        metadata['preprocessing_stages'].append('content_isolation')
        metadata['after_stage2_size'] = len(html)

        # Stage 3: Semantic Simplification
        html = self._stage3_semantic_simplification(html)
        metadata['preprocessing_stages'].append('semantic_simplification')
        metadata['final_size'] = len(html)

        # Calculate reduction percentage
        if metadata['original_size'] > 0:
            reduction = (1 - metadata['final_size'] / metadata['original_size']) * 100
            metadata['reduction_percentage'] = round(reduction, 2)

        return html, metadata

    def _stage1_aggressive_strip(self, html: str) -> str:
        """Stage 1: Remove scripts, styles, tracking, and noise"""
        soup = BeautifulSoup(html, 'lxml')

        # Remove script and style tags with content
        for tag in self.STRIP_TAGS:
            for element in soup.find_all(tag):
                element.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove data-* attributes, tracking pixels
        for tag in soup.find_all(True):
            # Remove data attributes
            attrs_to_remove = [attr for attr in tag.attrs if attr.startswith('data-')]
            for attr in attrs_to_remove:
                del tag[attr]

            # Remove style attributes
            if 'style' in tag.attrs:
                del tag['style']

            # Remove class and id (we'll preserve semantic meaning through tags)
            if 'class' in tag.attrs:
                del tag['class']
            if 'id' in tag.attrs:
                del tag['id']

            # Remove onclick and other event handlers
            event_attrs = [attr for attr in tag.attrs if attr.startswith('on')]
            for attr in event_attrs:
                del tag[attr]

        return str(soup)

    def _stage2_content_isolation(self, html: str, url: str) -> str:
        """Stage 2: Extract main content using readability"""
        try:
            # Use readability to extract main content
            doc = Document(html)
            content_html = doc.summary()

            # Also get title
            title = doc.title()

            # Wrap in a simple structure
            soup = BeautifulSoup(content_html, 'lxml')

            # Remove navigation elements that might have slipped through
            for tag in self.NAV_TAGS:
                for element in soup.find_all(tag):
                    element.decompose()

            # Remove elements commonly used for ads/tracking
            for element in soup.find_all(class_=re.compile(r'(ad|advertisement|banner|sidebar|related|comment|sponsor|promo)', re.I)):
                element.decompose()

            for element in soup.find_all(id=re.compile(r'(ad|advertisement|banner|sidebar|related|comment|sponsor|promo)', re.I)):
                element.decompose()

            return str(soup)
        except Exception as e:
            # If readability fails, return the html as-is
            print(f"Readability extraction failed: {e}")
            return html

    def _stage3_semantic_simplification(self, html: str) -> str:
        """Stage 3: Keep only semantic tags and essential attributes"""
        soup = BeautifulSoup(html, 'lxml')

        # Process all tags
        for tag in soup.find_all(True):
            # If tag is not in semantic list, unwrap it (keep content, remove tag)
            if tag.name not in self.SEMANTIC_TAGS:
                tag.unwrap()
                continue

            # For semantic tags, keep only essential attributes
            if tag.name == 'a':
                # Keep only href for links
                href = tag.get('href')
                tag.attrs.clear()
                if href:
                    tag['href'] = href
            elif tag.name == 'img':
                # Keep only src and alt for images
                src = tag.get('src')
                alt = tag.get('alt', '')
                tag.attrs.clear()
                if src:
                    tag['src'] = src
                if alt:
                    tag['alt'] = alt
            else:
                # For all other tags, remove all attributes
                tag.attrs.clear()

        # Remove empty elements (except br, hr, img)
        self._remove_empty_elements(soup)

        # Normalize whitespace
        html_str = str(soup)
        html_str = re.sub(r'\n\s*\n', '\n\n', html_str)  # Remove excessive newlines
        html_str = re.sub(r' +', ' ', html_str)  # Normalize spaces

        return html_str

    def _remove_empty_elements(self, soup: BeautifulSoup):
        """Recursively remove empty elements"""
        changed = True
        self_closing = {'br', 'hr', 'img'}

        while changed:
            changed = False
            for tag in soup.find_all(True):
                if tag.name in self_closing:
                    continue

                # Check if element is empty (no text and no children, or only whitespace)
                if not tag.get_text(strip=True) and not tag.find_all(True):
                    tag.decompose()
                    changed = True

    def extract_links(self, html: str, base_url: str) -> dict:
        """
        Extract and categorize links from HTML

        Args:
            html: HTML string
            base_url: Base URL for categorization

        Returns:
            Dict with internal_links, external_links, media_links
        """
        from urllib.parse import urljoin, urlparse

        soup = BeautifulSoup(html, 'lxml')
        base_domain = urlparse(base_url).netloc

        internal_links = set()
        external_links = set()
        media_links = set()

        # Media extensions
        media_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico',
            '.mp4', '.webm', '.mov', '.avi',
            '.mp3', '.wav', '.ogg',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz'
        }

        # Extract from <a> tags
        for link in soup.find_all('a', href=True):
            url = urljoin(base_url, link['href'])

            # Skip anchors, javascript, mailto, tel
            if url.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue

            parsed = urlparse(url)

            # Check if it's a media file
            is_media = any(parsed.path.lower().endswith(ext) for ext in media_extensions)

            if is_media:
                media_links.add(url)
            elif parsed.netloc == base_domain or not parsed.netloc:
                internal_links.add(url)
            else:
                external_links.add(url)

        # Extract from <img>, <video>, <audio>, <source> tags
        for tag in soup.find_all(['img', 'video', 'audio', 'source']):
            src = tag.get('src') or tag.get('data-src')
            if src:
                url = urljoin(base_url, src)
                media_links.add(url)

        return {
            'internal_links': sorted(list(internal_links)),
            'external_links': sorted(list(external_links)),
            'media_links': sorted(list(media_links))
        }


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation (1 token ≈ 4 characters for English)
    More accurate would use tiktoken, but this is sufficient
    """
    return len(text) // 4
