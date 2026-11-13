import json
from typing import List, Dict, Any, Optional

class LayoutAnalyzer:
    """
    DOM-based layout inspection and regression engine.
    Extracts structural geometry from Selenium elements and identifies
    missing, moved, resized, or restyled UI components.
    """

    EXTRACT_SCRIPT = """
    var elements = document.querySelectorAll('button, a, input, select, textarea, h1, h2, h3, h4, h5, h6, p, nav, header, footer, [role="button"], .card, .btn');
    var results = [];
    for (var i = 0; i < elements.length; i++) {
        var el = elements[i];
        var rect = el.getBoundingClientRect();
        // Skip invisible / zero-sized elements
        if (rect.width === 0 || rect.height === 0 || window.getComputedStyle(el).display === 'none' || window.getComputedStyle(el).visibility === 'hidden') {
            continue;
        }
        var style = window.getComputedStyle(el);
        results.push({
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            className: el.className ? String(el.className).trim() : '',
            text: (el.innerText || el.value || '').trim().substring(0, 50),
            x: Math.round(rect.left + window.scrollX),
            y: Math.round(rect.top + window.scrollY),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            color: style.color || '',
            backgroundColor: style.backgroundColor || '',
            fontSize: style.fontSize || '',
            textAlign: style.textAlign || ''
        });
    }
    return JSON.stringify(results);
    """

    @classmethod
    def extract_dom_snapshot(cls, driver) -> List[Dict[str, Any]]:
        """Executes JavaScript via Selenium driver to retrieve all interactive & layout element geometries."""
        try:
            raw_json = driver.execute_script(cls.EXTRACT_SCRIPT)
            if raw_json:
                return json.loads(raw_json)
        except Exception as e:
            pass
        return []

    @staticmethod
    def _element_signature(el: Dict[str, Any]) -> str:
        """Generates a stable identifier for matching elements across snapshots."""
        if el.get("id"):
            return f"id:{el['id']}"
        tag = el.get("tag", "elem")
        text = el.get("text", "")[:20]
        cls_name = ".".join(el.get("className", "").split()[:2])
        return f"{tag}|{cls_name}|{text}"

    @classmethod
    def compare_layouts(
        cls,
        baseline_elements: List[Dict[str, Any]],
        current_elements: List[Dict[str, Any]],
        position_tolerance: int = 5,
        dimension_tolerance: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Compares baseline and current element inventories to detect structural DOM modifications:
        - Moved elements (x, y coordinates changed)
        - Resized elements (width, height changed)
        - Missing components (removed from DOM)
        - Newly added components
        - Styling changes (background-color, font-size, text-align)
        """
        defects = []
        base_map = {}
        for b in baseline_elements:
            sig = cls._element_signature(b)
            # If duplicates, store by indexed key
            if sig in base_map:
                sig = f"{sig}_{b.get('x', 0)}_{b.get('y', 0)}"
            base_map[sig] = b

        curr_map = {}
        for c in current_elements:
            sig = cls._element_signature(c)
            if sig in curr_map:
                sig = f"{sig}_{c.get('x', 0)}_{c.get('y', 0)}"
            curr_map[sig] = c

        # 1. Check for missing elements or modified elements
        for sig, base_el in base_map.items():
            if sig not in curr_map:
                defects.append({
                    "defect_type": "element_missing",
                    "description": f"Missing component <{base_el.get('tag')}> '{base_el.get('text', '')}' (Expected at x:{base_el.get('x')}, y:{base_el.get('y')})",
                    "x": base_el.get("x", 0),
                    "y": base_el.get("y", 0),
                    "width": base_el.get("width", 0),
                    "height": base_el.get("height", 0),
                    "severity": "HIGH"
                })
            else:
                curr_el = curr_map[sig]
                dx = abs(curr_el.get("x", 0) - base_el.get("x", 0))
                dy = abs(curr_el.get("y", 0) - base_el.get("y", 0))
                dw = abs(curr_el.get("width", 0) - base_el.get("width", 0))
                dh = abs(curr_el.get("height", 0) - base_el.get("height", 0))

                # Check position displacement
                if dx > position_tolerance or dy > position_tolerance:
                    defects.append({
                        "defect_type": "element_moved",
                        "description": f"Displaced element <{curr_el.get('tag')}> '{curr_el.get('text', '')}'. Shifted from ({base_el.get('x')}, {base_el.get('y')}) to ({curr_el.get('x')}, {curr_el.get('y')})",
                        "x": curr_el.get("x", 0),
                        "y": curr_el.get("y", 0),
                        "width": curr_el.get("width", 0),
                        "height": curr_el.get("height", 0),
                        "severity": "MEDIUM"
                    })

                # Check dimension changes
                if dw > dimension_tolerance or dh > dimension_tolerance:
                    defects.append({
                        "defect_type": "element_resized",
                        "description": f"Resized element <{curr_el.get('tag')}>. Size changed from {base_el.get('width')}x{base_el.get('height')} to {curr_el.get('width')}x{curr_el.get('height')}",
                        "x": curr_el.get("x", 0),
                        "y": curr_el.get("y", 0),
                        "width": curr_el.get("width", 0),
                        "height": curr_el.get("height", 0),
                        "severity": "LOW"
                    })

                # Check CSS styling changes
                style_changes = []
                if base_el.get("backgroundColor") != curr_el.get("backgroundColor") and base_el.get("backgroundColor"):
                    style_changes.append(f"background-color changed from {base_el.get('backgroundColor')} to {curr_el.get('backgroundColor')}")
                if base_el.get("color") != curr_el.get("color") and base_el.get("color"):
                    style_changes.append(f"text color changed from {base_el.get('color')} to {curr_el.get('color')}")
                if base_el.get("fontSize") != curr_el.get("fontSize") and base_el.get("fontSize"):
                    style_changes.append(f"font-size changed from {base_el.get('fontSize')} to {curr_el.get('fontSize')}")

                if style_changes:
                    defects.append({
                        "defect_type": "css_modified",
                        "description": f"CSS modification on <{curr_el.get('tag')}> '{curr_el.get('text', '')}': " + "; ".join(style_changes),
                        "x": curr_el.get("x", 0),
                        "y": curr_el.get("y", 0),
                        "width": curr_el.get("width", 0),
                        "height": curr_el.get("height", 0),
                        "severity": "MEDIUM"
                    })

        # 2. Check for newly appeared elements
        for sig, curr_el in curr_map.items():
            if sig not in base_map:
                defects.append({
                    "defect_type": "element_added",
                    "description": f"Unexpected new element <{curr_el.get('tag')}> '{curr_el.get('text', '')}' found at ({curr_el.get('x')}, {curr_el.get('y')})",
                    "x": curr_el.get("x", 0),
                    "y": curr_el.get("y", 0),
                    "width": curr_el.get("width", 0),
                    "height": curr_el.get("height", 0),
                    "severity": "LOW"
                })

        return defects

