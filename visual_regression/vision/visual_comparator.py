import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from visual_regression.vision.image_processor import ImageProcessor

# Try importing structural_similarity
try:
    from skimage.metrics import structural_similarity as ssim
    SSIM_AVAILABLE = True
except ImportError:
    SSIM_AVAILABLE = False


class VisualComparator:
    """
    Core Computer Vision engine for visual regression testing.
    Executes pixel-difference comparison, binary masking, contour detection,
    bounding box extraction, and overlay rendering.
    """

    def __init__(self, pixel_threshold: int = 25, min_contour_area: int = 15):
        """
        :param pixel_threshold: Intensity difference (0-255) to qualify a pixel as changed.
        :param min_contour_area: Minimum bounding box pixel area to filter minor anti-aliasing noise.
        """
        self.pixel_threshold = pixel_threshold
        self.min_contour_area = min_contour_area

    def compare(
        self,
        baseline_img: np.ndarray,
        current_img: np.ndarray,
        acceptable_threshold_percent: float = 0.5,
        ignored_regions: Optional[List[Dict[str, int]]] = None
    ) -> Dict[str, Any]:
        """
        Compares baseline and current screenshots.
        Returns comprehensive metrics, changed pixel counts, contours, and visualizations.
        """
        # Ensure dimensions match
        base_aligned, curr_aligned = ImageProcessor.align_dimensions(baseline_img, current_img)
        h, w, c = base_aligned.shape
        total_pixels = h * w

        # 1. Calculate absolute pixel difference across all channels
        diff = cv2.absdiff(base_aligned, curr_aligned)

        # 2. Convert difference to grayscale
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

        # 3. Apply ignored regions if specified (mask them out to 0)
        if ignored_regions:
            for region in ignored_regions:
                rx = region.get("x", 0)
                ry = region.get("y", 0)
                rw = region.get("width", 0)
                rh = region.get("height", 0)
                # Clip to image boundary
                rx1, ry1 = max(0, rx), max(0, ry)
                rx2, ry2 = min(w, rx + rw), min(h, ry + rh)
                if rx2 > rx1 and ry2 > ry1:
                    gray_diff[ry1:ry2, rx1:rx2] = 0

        # 4. Binary thresholding to isolate significant pixel changes
        _, thresh = cv2.threshold(gray_diff, self.pixel_threshold, 255, cv2.THRESH_BINARY)

        # Morphological operations to group neighboring pixel changes and remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        # 5. Changed pixel count & percentage
        changed_pixels = int(np.count_nonzero(thresh))
        diff_percentage = (changed_pixels / total_pixels) * 100.0 if total_pixels > 0 else 0.0

        # 6. Structural Similarity Index (SSIM)
        ssim_score = 1.0
        if SSIM_AVAILABLE:
            try:
                base_gray = ImageProcessor.to_grayscale(base_aligned)
                curr_gray = ImageProcessor.to_grayscale(curr_aligned)
                score, _ = ssim(base_gray, curr_gray, full=True)
                ssim_score = round(float(score), 4)
            except Exception:
                ssim_score = 1.0

        # 7. Find contours of changed regions
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bounding_boxes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= self.min_contour_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                bounding_boxes.append({
                    "x": int(x),
                    "y": int(y),
                    "width": int(bw),
                    "height": int(bh),
                    "area": float(area)
                })

        # 8. Generate Difference Overlay: Highlights defects in vivid magenta/red over current screenshot
        overlay = curr_aligned.copy()
        # Red tint on changed pixels: BGR [0, 0, 255]
        overlay[thresh > 0] = [0, 0, 255]
        # Blend overlay with current image (alpha blending)
        diff_overlay = cv2.addWeighted(curr_aligned, 0.6, overlay, 0.4, 0)

        # Draw red bounding boxes and markers around detected defect regions
        boxes_overlay = diff_overlay.copy()
        for idx, box in enumerate(bounding_boxes, 1):
            x, y, bw, bh = box["x"], box["y"], box["width"], box["height"]
            cv2.rectangle(boxes_overlay, (x, y), (x + bw, y + bh), (0, 0, 255), 2)
            cv2.putText(
                boxes_overlay,
                f"#{idx}",
                (x, max(15, y - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 255),
                1,
                cv2.LINE_AA
            )

        # 9. Determine Status
        status = "FAIL" if diff_percentage > acceptable_threshold_percent else "PASS"

        return {
            "status": status,
            "total_pixels": total_pixels,
            "changed_pixels": changed_pixels,
            "difference_percentage": round(diff_percentage, 4),
            "ssim_score": ssim_score,
            "threshold": acceptable_threshold_percent,
            "defect_count": len(bounding_boxes),
            "bounding_boxes": bounding_boxes,
            "diff_mask": thresh,
            "diff_overlay": boxes_overlay,
            "gray_diff": gray_diff,
            "width": w,
            "height": h
        }

