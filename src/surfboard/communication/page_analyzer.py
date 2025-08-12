"""
Page analyzer for intelligent content summarization.

This module provides LLM-optimized page analysis capabilities,
extracting structured information from web pages.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from ..protocols.cdp_domains import CDPSession
from ..protocols.llm_protocol import PageInfo

logger = logging.getLogger(__name__)


@dataclass
class ElementAnalysis:
    """Analysis of a page element."""

    tag_name: str
    text: str
    attributes: Dict[str, str]
    is_interactive: bool
    is_visible: bool
    bounding_box: Dict[str, float]
    importance_score: float


class PageAnalyzer:
    """Analyzes web pages for LLM consumption."""

    def __init__(self):
        """Initialize page analyzer."""
        self.interactive_tags = {
            "a",
            "button",
            "input",
            "select",
            "textarea",
            "form",
            "details",
            "summary",
            "area",
            "map",
        }

        self.content_tags = {
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "div",
            "span",
            "article",
            "section",
            "main",
            "aside",
            "nav",
        }

        self.structural_tags = {
            "header",
            "footer",
            "nav",
            "main",
            "aside",
            "section",
            "article",
        }

    async def analyze_page(
        self,
        session: CDPSession,
        include_text: bool = True,
        include_links: bool = True,
        include_images: bool = False,
        include_forms: bool = True,
        max_elements: int = 50,
    ) -> PageInfo:
        """Analyze page and return structured information.

        Args:
            session: CDP session
            include_text: Include text content analysis
            include_links: Include link analysis
            include_images: Include image analysis
            include_forms: Include form analysis
            max_elements: Maximum elements to analyze

        Returns:
            Structured page information
        """
        # Get basic page information
        page_data = await self._get_basic_page_info(session)

        # Analyze page structure
        elements = await self._analyze_page_elements(session, max_elements)

        # Extract specific content types
        headings = await self._extract_headings(session) if include_text else []
        links = (
            await self._extract_links(session, page_data["url"])
            if include_links
            else []
        )
        images = (
            await self._extract_images(session, page_data["url"])
            if include_images
            else []
        )
        forms = await self._extract_forms(session) if include_forms else []

        # Extract and clean text content
        text_content = ""
        word_count = 0
        if include_text:
            text_content = await self._extract_text_content(session)
            word_count = len(text_content.split()) if text_content else 0

        return PageInfo(
            title=page_data["title"],
            url=page_data["url"],
            domain=page_data["domain"],
            meta_description=page_data.get("meta_description"),
            headings=headings,
            links=links,
            images=images,
            forms=forms,
            text_content=text_content,
            word_count=word_count,
        )

    async def _get_basic_page_info(self, session: CDPSession) -> Dict[str, str]:
        """Get basic page information."""
        script = """
        (function() {
            const metaDescription = document.querySelector('meta[name="description"]');
            const metaOgDescription = document.querySelector('meta[property="og:description"]');

            return {
                title: document.title || '',
                url: window.location.href,
                domain: window.location.hostname,
                meta_description: (metaDescription && metaDescription.content) ||
                                (metaOgDescription && metaOgDescription.content) ||
                                null
            };
        })()
        """

        return await session.runtime.evaluate(script) or {}

    async def _analyze_page_elements(
        self, session: CDPSession, max_elements: int
    ) -> List[ElementAnalysis]:
        """Analyze page elements for structure and content."""
        script = f"""
        (function() {{
            const elements = Array.from(document.querySelectorAll('*')).slice(0, {max_elements});
            const results = [];

            elements.forEach((el, index) => {{
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);

                // Skip hidden or tiny elements
                if (style.display === 'none' ||
                    style.visibility === 'hidden' ||
                    rect.width < 1 || rect.height < 1) {{
                    return;
                }}

                const isInteractive = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'FORM'].includes(el.tagName) ||
                                     el.onclick || el.getAttribute('role') === 'button';

                const text = el.textContent ? el.textContent.trim().substring(0, 200) : '';

                results.push({{
                    tagName: el.tagName.toLowerCase(),
                    text: text,
                    attributes: Object.fromEntries(
                        Array.from(el.attributes).map(attr => [attr.name, attr.value])
                    ),
                    isInteractive: isInteractive,
                    isVisible: true,
                    boundingBox: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }},
                    importanceScore: 0.5 // Basic scoring
                }});
            }});

            return results;
        }})()
        """

        results = await session.runtime.evaluate(script) or []

        elements = []
        for data in results:
            element = ElementAnalysis(
                tag_name=data.get("tagName", ""),
                text=data.get("text", ""),
                attributes=data.get("attributes", {}),
                is_interactive=data.get("isInteractive", False),
                is_visible=data.get("isVisible", True),
                bounding_box=data.get("boundingBox", {}),
                importance_score=self._calculate_importance_score(data),
            )
            elements.append(element)

        return elements

    async def _extract_headings(self, session: CDPSession) -> List[Dict[str, str]]:
        """Extract headings with hierarchy."""
        script = """
        (function() {
            const headings = [];
            const headingTags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];

            headingTags.forEach(tag => {
                document.querySelectorAll(tag).forEach(heading => {
                    const text = heading.textContent.trim();
                    if (text) {
                        headings.push({
                            level: tag,
                            text: text,
                            id: heading.id || null
                        });
                    }
                });
            });

            return headings;
        })()
        """

        return await session.runtime.evaluate(script) or []

    async def _extract_links(
        self, session: CDPSession, base_url: str
    ) -> List[Dict[str, str]]:
        """Extract links with context."""
        script = """
        (function() {
            const links = [];

            document.querySelectorAll('a[href]').forEach(link => {
                const href = link.getAttribute('href');
                const text = link.textContent.trim();
                const title = link.getAttribute('title');

                if (href && text) {
                    links.push({
                        url: href,
                        text: text,
                        title: title || null,
                        isExternal: href.startsWith('http') && !href.includes(window.location.hostname)
                    });
                }
            });

            return links;
        })()
        """

        links = await session.runtime.evaluate(script) or []

        # Resolve relative URLs
        for link in links:
            if not link["url"].startswith("http"):
                link["url"] = urljoin(base_url, link["url"])

        return links

    async def _extract_images(
        self, session: CDPSession, base_url: str
    ) -> List[Dict[str, str]]:
        """Extract images with metadata."""
        script = """
        (function() {
            const images = [];

            document.querySelectorAll('img').forEach(img => {
                const src = img.getAttribute('src');
                const alt = img.getAttribute('alt');
                const title = img.getAttribute('title');

                if (src) {
                    images.push({
                        src: src,
                        alt: alt || null,
                        title: title || null,
                        width: img.naturalWidth || img.width,
                        height: img.naturalHeight || img.height
                    });
                }
            });

            return images;
        })()
        """

        images = await session.runtime.evaluate(script) or []

        # Resolve relative URLs
        for image in images:
            if not image["src"].startswith("http"):
                image["src"] = urljoin(base_url, image["src"])

        return images

    async def _extract_forms(self, session: CDPSession) -> List[Dict[str, Any]]:
        """Extract forms with field information."""
        script = """
        (function() {
            const forms = [];

            document.querySelectorAll('form').forEach((form, index) => {
                const fields = [];

                form.querySelectorAll('input, select, textarea').forEach(field => {
                    const fieldInfo = {
                        tag: field.tagName.toLowerCase(),
                        type: field.getAttribute('type') || 'text',
                        name: field.getAttribute('name') || null,
                        id: field.getAttribute('id') || null,
                        placeholder: field.getAttribute('placeholder') || null,
                        required: field.hasAttribute('required'),
                        value: field.value || null
                    };

                    if (field.tagName === 'SELECT') {
                        fieldInfo.options = Array.from(field.options).map(opt => ({
                            value: opt.value,
                            text: opt.text
                        }));
                    }

                    fields.push(fieldInfo);
                });

                const submitButton = form.querySelector('input[type="submit"], button[type="submit"], button:not([type])');

                forms.push({
                    index: index,
                    action: form.getAttribute('action') || null,
                    method: form.getAttribute('method') || 'GET',
                    fields: fields,
                    submitText: submitButton ? submitButton.textContent.trim() || submitButton.value : null
                });
            });

            return forms;
        })()
        """

        return await session.runtime.evaluate(script) or []

    async def _extract_text_content(self, session: CDPSession) -> str:
        """Extract and clean main text content."""
        script = """
        (function() {
            // Remove script and style elements
            const scripts = document.querySelectorAll('script, style, nav, header, footer');
            scripts.forEach(el => el.remove());

            // Get text from main content areas
            const contentSelectors = [
                'main', 'article', '[role="main"]', '.content', '#content',
                '.post', '.article', '.entry-content'
            ];

            let content = '';

            for (const selector of contentSelectors) {
                const element = document.querySelector(selector);
                if (element) {
                    content = element.textContent;
                    break;
                }
            }

            // Fallback to body content
            if (!content) {
                content = document.body.textContent || '';
            }

            // Clean up whitespace
            return content.replace(/\\s+/g, ' ')
                         .replace(/\\n+/g, '\\n')
                         .trim()
                         .substring(0, 5000); // Limit to 5000 chars
        })()
        """

        return await session.runtime.evaluate(script) or ""

    def _calculate_importance_score(self, element_data: Dict[str, Any]) -> float:
        """Calculate importance score for an element."""
        score = 0.5  # Base score

        tag_name = element_data.get("tagName", "").lower()
        text = element_data.get("text", "")
        attributes = element_data.get("attributes", {})
        is_interactive = element_data.get("isInteractive", False)
        bounding_box = element_data.get("boundingBox", {})

        # Tag importance
        if tag_name in ["h1", "h2", "h3"]:
            score += 0.3
        elif tag_name in ["button", "a"]:
            score += 0.2
        elif tag_name in ["input", "select", "textarea"]:
            score += 0.15
        elif tag_name in ["form"]:
            score += 0.1

        # Interactive elements get bonus
        if is_interactive:
            score += 0.1

        # Text content quality
        if text:
            text_length = len(text)
            if 10 < text_length < 200:  # Sweet spot for useful text
                score += 0.1
            elif text_length > 200:
                score += 0.05  # Long text is less important for interaction

        # Position importance (elements higher on page are more important)
        y_position = bounding_box.get("y", 1000)
        if y_position < 100:  # Top of page
            score += 0.1
        elif y_position < 500:  # Above fold
            score += 0.05

        # Size importance (larger elements might be more important)
        area = bounding_box.get("width", 0) * bounding_box.get("height", 0)
        if area > 10000:  # Large element
            score += 0.05

        # Attribute-based scoring
        if attributes.get("id"):
            score += 0.05
        if attributes.get("class"):
            classes = attributes.get("class", "").lower()
            if any(keyword in classes for keyword in ["button", "link", "nav", "menu"]):
                score += 0.05

        return min(score, 1.0)  # Cap at 1.0

    async def get_interactive_elements(
        self, session: CDPSession, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get interactive elements sorted by importance."""
        script = f"""
        (function() {{
            const interactiveSelectors = [
                'a[href]', 'button', 'input', 'select', 'textarea',
                '[role="button"]', '[onclick]', 'details', 'summary'
            ];

            const elements = [];

            interactiveSelectors.forEach(selector => {{
                document.querySelectorAll(selector).forEach(el => {{
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);

                    // Skip hidden elements
                    if (style.display === 'none' ||
                        style.visibility === 'hidden' ||
                        rect.width < 5 || rect.height < 5) {{
                        return;
                    }}

                    const text = el.textContent ? el.textContent.trim().substring(0, 100) : '';
                    const tag = el.tagName.toLowerCase();

                    elements.push({{
                        tag: tag,
                        text: text || el.getAttribute('alt') || el.getAttribute('title') || '',
                        selector: el.id ? `#${{el.id}}` :
                                 el.className ? `.${{el.className.split(' ')[0]}}` :
                                 tag,
                        position: {{
                            x: rect.x,
                            y: rect.y
                        }},
                        size: {{
                            width: rect.width,
                            height: rect.height
                        }}
                    }});
                }});
            }});

            // Sort by position (top-left first)
            elements.sort((a, b) => {{
                if (Math.abs(a.position.y - b.position.y) < 50) {{
                    return a.position.x - b.position.x;
                }}
                return a.position.y - b.position.y;
            }});

            return elements.slice(0, {limit});
        }})()
        """

        return await session.runtime.evaluate(script) or []

    async def get_form_fields(self, session: CDPSession) -> List[Dict[str, Any]]:
        """Get detailed form field information for LLM interaction."""
        script = """
        (function() {
            const fields = [];

            document.querySelectorAll('input, select, textarea').forEach(field => {
                const rect = field.getBoundingClientRect();
                const style = window.getComputedStyle(field);

                if (style.display === 'none' || style.visibility === 'hidden') {
                    return;
                }

                const label = field.closest('label') ||
                             document.querySelector(`label[for="${field.id}"]`) ||
                             field.previousElementSibling;

                fields.push({
                    tag: field.tagName.toLowerCase(),
                    type: field.getAttribute('type') || 'text',
                    name: field.getAttribute('name') || null,
                    id: field.getAttribute('id') || null,
                    placeholder: field.getAttribute('placeholder') || null,
                    label: label ? label.textContent.trim() : null,
                    required: field.hasAttribute('required'),
                    value: field.value || null,
                    selector: field.id ? `#${field.id}` :
                             field.name ? `[name="${field.name}"]` :
                             field.placeholder ? `[placeholder="${field.placeholder}"]` :
                             null
                });
            });

            return fields;
        })()
        """

        return await session.runtime.evaluate(script) or []
