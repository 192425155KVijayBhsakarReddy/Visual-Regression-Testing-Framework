import os
import pytest
import numpy as np
import cv2
from pathlib import Path
from visual_regression.vision.image_processor import ImageProcessor
from visual_regression.vision.visual_comparator import VisualComparator
from visual_regression.vision.heatmap_generator import HeatmapGenerator
from visual_regression.vision.layout_analyzer import LayoutAnalyzer

@pytest.fixture
def test_images(tmp_path):
    """Generates synthetic baseline and mutated images for deterministic computer vision testing."""
    # Create clean white canvas 400x300
    base = np.full((300, 400, 3), 255, dtype=np.uint8)
    # Draw blue button at (50, 50) width 100, height 40
    cv2.rectangle(base, (50, 50), (150, 90), (255, 0, 0), -1)

    # Identical copy
    identical = base.copy()

    # Mutated copy: Change button color from blue to red [0, 0, 255]
    color_changed = base.copy()
    cv2.rectangle(color_changed, (50, 50), (150, 90), (0, 0, 255), -1)

    # Mutated copy: Move button from (50, 50) to (180, 100)
    moved = np.full((300, 400, 3), 255, dtype=np.uint8)
    cv2.rectangle(moved, (180, 100), (280, 140), (255, 0, 0), -1)

    # Mutated copy: Missing button
    missing = np.full((300, 400, 3), 255, dtype=np.uint8)

    base_path = str(tmp_path / "base.png")
    identical_path = str(tmp_path / "identical.png")
    color_path = str(tmp_path / "color.png")
    moved_path = str(tmp_path / "moved.png")
    missing_path = str(tmp_path / "missing.png")

    ImageProcessor.save_image(base, base_path)
    ImageProcessor.save_image(identical, identical_path)
    ImageProcessor.save_image(color_changed, color_path)
    ImageProcessor.save_image(moved, moved_path)
    ImageProcessor.save_image(missing, missing_path)

    return {
        "base": base,
        "base_path": base_path,
        "identical": identical,
        "identical_path": identical_path,
        "color_changed": color_changed,
        "color_path": color_path,
        "moved": moved,
        "moved_path": moved_path,
        "missing": missing,
        "missing_path": missing_path,
        "tmp_dir": tmp_path
    }

def test_identical_images_comparison(test_images):
    """Test 1: Identical images must produce 0% difference and PASS."""
    comparator = VisualComparator()
    result = comparator.compare(test_images["base"], test_images["identical"], acceptable_threshold_percent=0.5)

    assert result["status"] == "PASS"
    assert result["difference_percentage"] == 0.0
    assert result["changed_pixels"] == 0
    assert result["defect_count"] == 0
    assert result["ssim_score"] == 1.0

def test_color_change_detection(test_images):
    """Test 2: Modifying element color must trigger pixel difference, contour bounding box, and FAIL."""
    comparator = VisualComparator()
    result = comparator.compare(test_images["base"], test_images["color_changed"], acceptable_threshold_percent=0.5)

    assert result["status"] == "FAIL"
    assert result["difference_percentage"] > 0.5
    assert result["changed_pixels"] > 0
    assert result["defect_count"] >= 1
    # Check bounding box matches button location
    box = result["bounding_boxes"][0]
    assert abs(box["x"] - 50) <= 2
    assert abs(box["y"] - 50) <= 2

def test_element_movement_detection(test_images):
    """Test 3: Moving an element must produce detected difference in original and new regions."""
    comparator = VisualComparator()
    result = comparator.compare(test_images["base"], test_images["moved"], acceptable_threshold_percent=0.5)

    assert result["status"] == "FAIL"
    assert result["difference_percentage"] > 1.0
    # Should detect 2 changed regions (old position removed, new position added)
    assert result["defect_count"] >= 2

def test_missing_element_detection(test_images):
    """Test 4: Removing an element must be flagged as a defect."""
    comparator = VisualComparator()
    result = comparator.compare(test_images["base"], test_images["missing"], acceptable_threshold_percent=0.5)

    assert result["status"] == "FAIL"
    assert result["changed_pixels"] > 3000

def test_ignored_regions(test_images):
    """Test 5: Explicitly ignored bounding box regions must be filtered from difference mask."""
    comparator = VisualComparator()
    # Mask out the button area (50, 50, 100, 40)
    ignored = [{"x": 48, "y": 48, "width": 104, "height": 44}]
    result = comparator.compare(
        test_images["base"],
        test_images["color_changed"],
        acceptable_threshold_percent=0.5,
        ignored_regions=ignored
    )

    # When ignored, difference should drop to 0% and PASS
    assert result["status"] == "PASS"
    assert result["changed_pixels"] == 0

def test_heatmap_generation(test_images):
    """Test 6: Heatmap generator creates valid continuous color matrix."""
    comparator = VisualComparator()
    res = comparator.compare(test_images["base"], test_images["color_changed"])
    heatmap = HeatmapGenerator.generate_heatmap(res["gray_diff"], test_images["color_changed"])

    assert heatmap is not None
    assert heatmap.shape == test_images["base"].shape
    assert heatmap.dtype == np.uint8

def test_image_dimension_alignment():
    """Test 7: Different sized viewports are automatically aligned/padded to avoid crashes."""
    img_small = np.zeros((200, 300, 3), dtype=np.uint8)
    img_large = np.zeros((250, 350, 3), dtype=np.uint8)

    aligned1, aligned2 = ImageProcessor.align_dimensions(img_small, img_large)
    assert aligned1.shape == (250, 350, 3)
    assert aligned2.shape == (250, 350, 3)

def test_layout_analyzer_dom_diff():
    """Test 8: DOM Layout Analyzer accurately detects moved, missing, and css modified elements."""
    base_dom = [
        {"id": "btn-1", "tag": "button", "text": "Submit", "x": 100, "y": 50, "width": 80, "height": 30, "backgroundColor": "rgb(0, 0, 255)", "color": "white", "fontSize": "14px"},
        {"id": "header-title", "tag": "h1", "text": "Dashboard", "x": 20, "y": 10, "width": 200, "height": 40, "backgroundColor": "", "color": "black", "fontSize": "24px"}
    ]

    # Current DOM: btn-1 moved and background color changed; header-title is missing
    curr_dom = [
        {"id": "btn-1", "tag": "button", "text": "Submit", "x": 150, "y": 50, "width": 80, "height": 30, "backgroundColor": "rgb(255, 0, 0)", "color": "white", "fontSize": "14px"}
    ]

    defects = LayoutAnalyzer.compare_layouts(base_dom, curr_dom)
    defect_types = [d["defect_type"] for d in defects]

    assert "element_missing" in defect_types
    assert "element_moved" in defect_types
    assert "css_modified" in defect_types

