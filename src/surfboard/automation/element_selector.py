"""
Advanced Element Selection System.

This module provides intelligent element selection strategies with fallback
mechanisms, visual detection, and context-aware selection.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from ..protocols.cdp_domains import CDPSession
from ..protocols.llm_protocol import ElementSelector, ElementSelectorType

logger = logging.getLogger(__name__)


class SelectionStrategy(str, Enum):
    """Element selection strategies."""

    EXACT_MATCH = "exact_match"
    FUZZY_TEXT = "fuzzy_text"
    VISUAL_SIMILARITY = "visual_similarity"
    CONTEXT_AWARE = "context_aware"
    ATTRIBUTE_PATTERN = "attribute_pattern"
    STRUCTURAL = "structural"


@dataclass
class SelectionResult:
    """Result of element selection."""

    element_id: Optional[str]
    selector_used: str
    strategy: SelectionStrategy
    confidence: float
    bounding_box: Dict[str, float]
    attributes: Dict[str, str]
    text_content: str
    screenshot_data: Optional[str] = None


class AdvancedElementSelector:
    """Advanced element selection with multiple strategies."""

    def __init__(self):
        """Initialize advanced element selector."""
        self.strategies = [
            SelectionStrategy.EXACT_MATCH,
            SelectionStrategy.FUZZY_TEXT,
            SelectionStrategy.CONTEXT_AWARE,
            SelectionStrategy.ATTRIBUTE_PATTERN,
            SelectionStrategy.VISUAL_SIMILARITY,
            SelectionStrategy.STRUCTURAL,
        ]

    async def find_element(
        self,
        session: CDPSession,
        selector: ElementSelector,
        context: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3,
        adaptive_timeout: bool = True,
    ) -> Optional[SelectionResult]:
        """Find element using advanced strategies.

        Args:
            session: CDP session
            selector: Element selector
            context: Additional context for selection
            max_attempts: Maximum selection attempts
            adaptive_timeout: Use adaptive timeout based on page complexity

        Returns:
            Selection result or None if not found
        """
        logger.debug(
            f"Finding element with selector: {selector.type.value}={selector.value}"
        )

        # Adjust timeout based on page complexity if adaptive
        timeout = selector.timeout
        if adaptive_timeout:
            timeout = await self._calculate_adaptive_timeout(session, selector.timeout)

        # Try each strategy in order
        for attempt in range(max_attempts):
            for strategy in self.strategies:
                try:
                    result = await self._try_strategy(
                        session, selector, strategy, context, timeout
                    )

                    if result and result.confidence > 0.7:  # High confidence threshold
                        logger.debug(f"Element found using {strategy.value} strategy")
                        return result

                except Exception as e:
                    logger.debug(f"Strategy {strategy.value} failed: {e}")
                    continue

            # Wait before retry
            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5)

        logger.warning(f"Element not found after {max_attempts} attempts")
        return None

    async def find_multiple_elements(
        self,
        session: CDPSession,
        selector: ElementSelector,
        limit: int = 10,
        similarity_threshold: float = 0.8,
    ) -> List[SelectionResult]:
        """Find multiple similar elements."""
        logger.debug(
            f"Finding multiple elements: {selector.type.value}={selector.value}"
        )

        # Start with exact matches
        results = await self._find_exact_matches(session, selector, limit)

        # If not enough results, try fuzzy matching
        if len(results) < limit:
            fuzzy_results = await self._find_fuzzy_matches(
                session, selector, limit - len(results), similarity_threshold
            )
            results.extend(fuzzy_results)

        return results[:limit]

    async def _try_strategy(
        self,
        session: CDPSession,
        selector: ElementSelector,
        strategy: SelectionStrategy,
        context: Optional[Dict[str, Any]],
        timeout: float,
    ) -> Optional[SelectionResult]:
        """Try a specific selection strategy."""

        if strategy == SelectionStrategy.EXACT_MATCH:
            return await self._exact_match_strategy(session, selector)
        elif strategy == SelectionStrategy.FUZZY_TEXT:
            return await self._fuzzy_text_strategy(session, selector)
        elif strategy == SelectionStrategy.CONTEXT_AWARE:
            return await self._context_aware_strategy(session, selector, context)
        elif strategy == SelectionStrategy.ATTRIBUTE_PATTERN:
            return await self._attribute_pattern_strategy(session, selector)
        elif strategy == SelectionStrategy.VISUAL_SIMILARITY:
            return await self._visual_similarity_strategy(session, selector)
        elif strategy == SelectionStrategy.STRUCTURAL:
            return await self._structural_strategy(session, selector)

        return None

    async def _exact_match_strategy(
        self, session: CDPSession, selector: ElementSelector
    ) -> Optional[SelectionResult]:
        """Exact match selection strategy."""

        if selector.type == ElementSelectorType.CSS:
            script = f"""
            (function() {{
                const element = document.querySelector({repr(selector.value)});
                if (!element) return null;

                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);

                if (style.display === 'none' || style.visibility === 'hidden') {{
                    return null;
                }}

                return {{
                    elementId: element.id || null,
                    tagName: element.tagName.toLowerCase(),
                    text: element.textContent.trim(),
                    attributes: Object.fromEntries(
                        Array.from(element.attributes).map(attr => [attr.name, attr.value])
                    ),
                    boundingBox: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }},
                    isVisible: rect.width > 0 && rect.height > 0
                }};
            }})()
            """

        elif selector.type == ElementSelectorType.XPATH:
            script = f"""
            (function() {{
                const result = document.evaluate(
                    {repr(selector.value)},
                    document,
                    null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null
                );

                const element = result.singleNodeValue;
                if (!element) return null;

                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);

                if (style.display === 'none' || style.visibility === 'hidden') {{
                    return null;
                }}

                return {{
                    elementId: element.id || null,
                    tagName: element.tagName.toLowerCase(),
                    text: element.textContent.trim(),
                    attributes: Object.fromEntries(
                        Array.from(element.attributes).map(attr => [attr.name, attr.value])
                    ),
                    boundingBox: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }},
                    isVisible: rect.width > 0 && rect.height > 0
                }};
            }})()
            """

        elif selector.type == ElementSelectorType.TEXT:
            script = f"""
            (function() {{
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_ELEMENT
                );

                let element = null;
                const targetText = {repr(selector.value.lower())};

                while (walker.nextNode()) {{
                    const node = walker.currentNode;
                    const text = node.textContent.trim().toLowerCase();

                    if (text === targetText) {{
                        element = node;
                        break;
                    }}
                }}

                if (!element) return null;

                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);

                if (style.display === 'none' || style.visibility === 'hidden') {{
                    return null;
                }}

                return {{
                    elementId: element.id || null,
                    tagName: element.tagName.toLowerCase(),
                    text: element.textContent.trim(),
                    attributes: Object.fromEntries(
                        Array.from(element.attributes).map(attr => [attr.name, attr.value])
                    ),
                    boundingBox: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }},
                    isVisible: rect.width > 0 && rect.height > 0
                }};
            }})()
            """
        else:
            return None

        result_data = await session.runtime.evaluate(script)
        if not result_data:
            return None

        return SelectionResult(
            element_id=result_data.get("elementId"),
            selector_used=selector.value,
            strategy=SelectionStrategy.EXACT_MATCH,
            confidence=1.0,
            bounding_box=result_data.get("boundingBox", {}),
            attributes=result_data.get("attributes", {}),
            text_content=result_data.get("text", ""),
        )

    async def _fuzzy_text_strategy(
        self, session: CDPSession, selector: ElementSelector
    ) -> Optional[SelectionResult]:
        """Fuzzy text matching strategy."""

        if selector.type != ElementSelectorType.TEXT:
            return None

        script = f"""
        (function() {{
            const targetText = {repr(selector.value.lower())};
            const elements = Array.from(document.querySelectorAll('*'));

            let bestMatch = null;
            let bestScore = 0;

            function calculateSimilarity(str1, str2) {{
                const longer = str1.length > str2.length ? str1 : str2;
                const shorter = str1.length > str2.length ? str2 : str1;

                if (longer.length === 0) return 1.0;

                const editDistance = levenshteinDistance(longer, shorter);
                return (longer.length - editDistance) / longer.length;
            }}

            function levenshteinDistance(str1, str2) {{
                const matrix = [];
                for (let i = 0; i <= str2.length; i++) {{
                    matrix[i] = [i];
                }}
                for (let j = 0; j <= str1.length; j++) {{
                    matrix[0][j] = j;
                }}
                for (let i = 1; i <= str2.length; i++) {{
                    for (let j = 1; j <= str1.length; j++) {{
                        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {{
                            matrix[i][j] = matrix[i - 1][j - 1];
                        }} else {{
                            matrix[i][j] = Math.min(
                                matrix[i - 1][j - 1] + 1,
                                matrix[i][j - 1] + 1,
                                matrix[i - 1][j] + 1
                            );
                        }}
                    }}
                }}
                return matrix[str2.length][str1.length];
            }}

            elements.forEach(element => {{
                const text = element.textContent.trim().toLowerCase();
                if (text.length === 0) return;

                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);

                if (style.display === 'none' || style.visibility === 'hidden') {{
                    return;
                }}

                // Check exact substring match first
                let score = 0;
                if (text.includes(targetText)) {{
                    score = 0.9;
                }} else {{
                    // Fuzzy matching
                    score = calculateSimilarity(text, targetText);
                }}

                if (score > bestScore && score > 0.6) {{
                    bestScore = score;
                    bestMatch = {{
                        element: element,
                        score: score,
                        elementId: element.id || null,
                        tagName: element.tagName.toLowerCase(),
                        text: element.textContent.trim(),
                        attributes: Object.fromEntries(
                            Array.from(element.attributes).map(attr => [attr.name, attr.value])
                        ),
                        boundingBox: {{
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }}
                    }};
                }}
            }});

            return bestMatch;
        }})()
        """

        result_data = await session.runtime.evaluate(script)
        if not result_data:
            return None

        return SelectionResult(
            element_id=result_data.get("elementId"),
            selector_used=selector.value,
            strategy=SelectionStrategy.FUZZY_TEXT,
            confidence=result_data.get("score", 0.0),
            bounding_box=result_data.get("boundingBox", {}),
            attributes=result_data.get("attributes", {}),
            text_content=result_data.get("text", ""),
        )

    async def _context_aware_strategy(
        self,
        session: CDPSession,
        selector: ElementSelector,
        context: Optional[Dict[str, Any]],
    ) -> Optional[SelectionResult]:
        """Context-aware selection strategy."""

        if not context:
            return None

        # Use context hints to improve selection
        nearby_text = context.get("nearby_text")
        form_context = context.get("form_context")
        section_context = context.get("section_context")

        script = f"""
        (function() {{
            const targetValue = {repr(selector.value)};
            const nearbyText = {repr(nearby_text) if nearby_text else 'null'};
            const formContext = {repr(form_context) if form_context else 'null'};
            const sectionContext = {repr(section_context) if section_context else 'null'};

            let candidates = [];

            // Find potential elements
            if ({repr(selector.type.value)} === 'css') {{
                candidates = Array.from(document.querySelectorAll(targetValue));
            }} else if ({repr(selector.type.value)} === 'text') {{
                candidates = Array.from(document.querySelectorAll('*')).filter(el =>
                    el.textContent.toLowerCase().includes(targetValue.toLowerCase())
                );
            }}

            if (candidates.length === 0) return null;
            if (candidates.length === 1) {{
                const element = candidates[0];
                const rect = element.getBoundingClientRect();

                return {{
                    elementId: element.id || null,
                    tagName: element.tagName.toLowerCase(),
                    text: element.textContent.trim(),
                    attributes: Object.fromEntries(
                        Array.from(element.attributes).map(attr => [attr.name, attr.value])
                    ),
                    boundingBox: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }}
                }};
            }}

            // Multiple candidates - use context to disambiguate
            let bestMatch = null;
            let bestScore = 0;

            candidates.forEach(element => {{
                let score = 0.5; // Base score

                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);

                if (style.display === 'none' || style.visibility === 'hidden') {{
                    return;
                }}

                // Check nearby text context
                if (nearbyText) {{
                    const parent = element.closest('form, section, div, article');
                    if (parent && parent.textContent.toLowerCase().includes(nearbyText.toLowerCase())) {{
                        score += 0.3;
                    }}
                }}

                // Check form context
                if (formContext && element.closest('form')) {{
                    const form = element.closest('form');
                    if (form && form.textContent.toLowerCase().includes(formContext.toLowerCase())) {{
                        score += 0.2;
                    }}
                }}

                // Check section context
                if (sectionContext) {{
                    const section = element.closest('section, article, main, div');
                    if (section && section.textContent.toLowerCase().includes(sectionContext.toLowerCase())) {{
                        score += 0.2;
                    }}
                }}

                if (score > bestScore) {{
                    bestScore = score;
                    bestMatch = {{
                        element: element,
                        score: score,
                        elementId: element.id || null,
                        tagName: element.tagName.toLowerCase(),
                        text: element.textContent.trim(),
                        attributes: Object.fromEntries(
                            Array.from(element.attributes).map(attr => [attr.name, attr.value])
                        ),
                        boundingBox: {{
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }}
                    }};
                }}
            }});

            return bestMatch;
        }})()
        """

        result_data = await session.runtime.evaluate(script)
        if not result_data:
            return None

        return SelectionResult(
            element_id=result_data.get("elementId"),
            selector_used=selector.value,
            strategy=SelectionStrategy.CONTEXT_AWARE,
            confidence=result_data.get("score", 0.5),
            bounding_box=result_data.get("boundingBox", {}),
            attributes=result_data.get("attributes", {}),
            text_content=result_data.get("text", ""),
        )

    async def _attribute_pattern_strategy(
        self, session: CDPSession, selector: ElementSelector
    ) -> Optional[SelectionResult]:
        """Attribute pattern matching strategy."""

        script = f"""
        (function() {{
            const selectorType = {repr(selector.type.value)};
            const selectorValue = {repr(selector.value)};

            let candidates = [];

            if (selectorType === 'placeholder') {{
                candidates = Array.from(document.querySelectorAll(`[placeholder*="${{selectorValue}}"]`));
            }} else if (selectorType === 'aria_label') {{
                candidates = Array.from(document.querySelectorAll(`[aria-label*="${{selectorValue}}"]`));
            }} else if (selectorType === 'role') {{
                candidates = Array.from(document.querySelectorAll(`[role="${{selectorValue}}"]`));
            }} else if (selectorType === 'tag_name') {{
                candidates = Array.from(document.querySelectorAll(selectorValue));
            }}

            // Find best match based on attribute relevance
            let bestMatch = null;
            let bestScore = 0;

            candidates.forEach(element => {{
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);

                if (style.display === 'none' || style.visibility === 'hidden' ||
                    rect.width < 1 || rect.height < 1) {{
                    return;
                }}

                let score = 0.7; // Base score for attribute match

                // Boost score for interactive elements
                if (['button', 'input', 'select', 'textarea', 'a'].includes(element.tagName.toLowerCase())) {{
                    score += 0.2;
                }}

                // Boost score for elements with meaningful text
                const text = element.textContent.trim();
                if (text.length > 0 && text.length < 100) {{
                    score += 0.1;
                }}

                if (score > bestScore) {{
                    bestScore = score;
                    bestMatch = {{
                        elementId: element.id || null,
                        tagName: element.tagName.toLowerCase(),
                        text: text,
                        attributes: Object.fromEntries(
                            Array.from(element.attributes).map(attr => [attr.name, attr.value])
                        ),
                        boundingBox: {{
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }},
                        score: score
                    }};
                }}
            }});

            return bestMatch;
        }})()
        """

        result_data = await session.runtime.evaluate(script)
        if not result_data:
            return None

        return SelectionResult(
            element_id=result_data.get("elementId"),
            selector_used=selector.value,
            strategy=SelectionStrategy.ATTRIBUTE_PATTERN,
            confidence=result_data.get("score", 0.7),
            bounding_box=result_data.get("boundingBox", {}),
            attributes=result_data.get("attributes", {}),
            text_content=result_data.get("text", ""),
        )

    async def _visual_similarity_strategy(
        self, session: CDPSession, selector: ElementSelector
    ) -> Optional[SelectionResult]:
        """Visual similarity strategy (placeholder for future ML integration)."""

        # This would integrate with computer vision models
        # For now, return None to fall back to other strategies
        logger.debug("Visual similarity strategy not yet implemented")
        return None

    async def _structural_strategy(
        self, session: CDPSession, selector: ElementSelector
    ) -> Optional[SelectionResult]:
        """Structural relationship-based strategy."""

        script = f"""
        (function() {{
            const selectorValue = {repr(selector.value)};
            const selectorType = {repr(selector.type.value)};

            // Find elements using structural relationships
            let candidates = [];

            if (selectorType === 'text') {{
                // Find by text content and then check structural context
                const allElements = Array.from(document.querySelectorAll('*'));
                allElements.forEach(element => {{
                    const text = element.textContent.trim().toLowerCase();
                    if (text.includes(selectorValue.toLowerCase())) {{
                        candidates.push(element);
                    }}
                }});
            }} else if (selectorType === 'css') {{
                candidates = Array.from(document.querySelectorAll(selectorValue));
            }}

            // Score based on structural importance
            let bestMatch = null;
            let bestScore = 0;

            candidates.forEach(element => {{
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);

                if (style.display === 'none' || style.visibility === 'hidden') {{
                    return;
                }}

                let score = 0.5;

                // Structural scoring
                const depth = element.querySelectorAll('*').length;
                if (depth === 0) score += 0.1; // Leaf elements are often more specific

                // Parent context scoring
                const parent = element.parentElement;
                if (parent) {{
                    const parentTag = parent.tagName.toLowerCase();
                    if (['form', 'nav', 'header', 'main'].includes(parentTag)) {{
                        score += 0.2;
                    }}
                }}

                // Position scoring (elements in viewport are more relevant)
                if (rect.y >= 0 && rect.y <= window.innerHeight) {{
                    score += 0.1;
                }}

                // Size scoring (reasonably sized elements)
                const area = rect.width * rect.height;
                if (area > 100 && area < 100000) {{
                    score += 0.1;
                }}

                if (score > bestScore) {{
                    bestScore = score;
                    bestMatch = {{
                        elementId: element.id || null,
                        tagName: element.tagName.toLowerCase(),
                        text: element.textContent.trim(),
                        attributes: Object.fromEntries(
                            Array.from(element.attributes).map(attr => [attr.name, attr.value])
                        ),
                        boundingBox: {{
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }},
                        score: score
                    }};
                }}
            }});

            return bestMatch;
        }})()
        """

        result_data = await session.runtime.evaluate(script)
        if not result_data:
            return None

        return SelectionResult(
            element_id=result_data.get("elementId"),
            selector_used=selector.value,
            strategy=SelectionStrategy.STRUCTURAL,
            confidence=result_data.get("score", 0.5),
            bounding_box=result_data.get("boundingBox", {}),
            attributes=result_data.get("attributes", {}),
            text_content=result_data.get("text", ""),
        )

    async def _calculate_adaptive_timeout(
        self, session: CDPSession, base_timeout: float
    ) -> float:
        """Calculate adaptive timeout based on page complexity."""

        script = """
        (function() {
            const elementCount = document.querySelectorAll('*').length;
            const imageCount = document.querySelectorAll('img').length;
            const scriptCount = document.querySelectorAll('script').length;

            return {
                elementCount: elementCount,
                imageCount: imageCount,
                scriptCount: scriptCount,
                loadState: document.readyState
            };
        })()
        """

        page_info = await session.runtime.evaluate(script)
        if not page_info:
            return base_timeout

        element_count = page_info.get("elementCount", 100)
        image_count = page_info.get("imageCount", 0)
        script_count = page_info.get("scriptCount", 0)

        # Complexity scoring
        complexity_score = 1.0

        if element_count > 1000:
            complexity_score += 0.5
        elif element_count > 500:
            complexity_score += 0.3

        if image_count > 20:
            complexity_score += 0.2
        elif image_count > 10:
            complexity_score += 0.1

        if script_count > 10:
            complexity_score += 0.3

        # Cap the multiplier
        complexity_score = min(complexity_score, 2.0)

        adaptive_timeout = base_timeout * complexity_score
        logger.debug(
            f"Adaptive timeout: {adaptive_timeout:.1f}s (complexity: {complexity_score:.1f})"
        )

        return adaptive_timeout

    async def _find_exact_matches(
        self, session: CDPSession, selector: ElementSelector, limit: int
    ) -> List[SelectionResult]:
        """Find exact matches for multiple elements."""

        if selector.type == ElementSelectorType.CSS:
            script = f"""
            (function() {{
                const elements = Array.from(document.querySelectorAll({repr(selector.value)}))
                    .slice(0, {limit});

                return elements.map(element => {{
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);

                    return {{
                        elementId: element.id || null,
                        tagName: element.tagName.toLowerCase(),
                        text: element.textContent.trim(),
                        attributes: Object.fromEntries(
                            Array.from(element.attributes).map(attr => [attr.name, attr.value])
                        ),
                        boundingBox: {{
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }},
                        isVisible: style.display !== 'none' && style.visibility !== 'hidden'
                    }};
                }}).filter(item => item.isVisible);
            }})()
            """
        else:
            return []

        results_data = await session.runtime.evaluate(script) or []

        results = []
        for data in results_data:
            result = SelectionResult(
                element_id=data.get("elementId"),
                selector_used=selector.value,
                strategy=SelectionStrategy.EXACT_MATCH,
                confidence=1.0,
                bounding_box=data.get("boundingBox", {}),
                attributes=data.get("attributes", {}),
                text_content=data.get("text", ""),
            )
            results.append(result)

        return results

    async def _find_fuzzy_matches(
        self,
        session: CDPSession,
        selector: ElementSelector,
        limit: int,
        threshold: float,
    ) -> List[SelectionResult]:
        """Find fuzzy matches for multiple elements."""

        # Implement fuzzy matching logic similar to single element
        # but return multiple results above threshold
        return []  # Placeholder for now
