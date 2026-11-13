import cv2
import numpy as np

class HeatmapGenerator:
    """
    Generates difference heatmaps using OpenCV color mapping (COLORMAP_JET / COLORMAP_INFERNO).
    Visualizes distribution and intensity of visual variance across the viewport.
    """

    @staticmethod
    def generate_heatmap(
        gray_diff: np.ndarray,
        current_img: np.ndarray,
        colormap: int = cv2.COLORMAP_JET,
        alpha: float = 0.5
    ) -> np.ndarray:
        """
        Creates a color-mapped heatmap blended directly over the original screen image.
        :param gray_diff: Grayscale difference image (values 0-255).
        :param current_img: Current RGB/BGR screenshot to blend with.
        :param colormap: OpenCV colormap constant.
        :param alpha: Transparency weighting of heatmap over original screenshot.
        :return: Blended heatmap image (BGR).
        """
        # Ensure dimensions match
        if gray_diff.shape[:2] != current_img.shape[:2]:
            gray_diff = cv2.resize(gray_diff, (current_img.shape[1], current_img.shape[0]))

        # Smooth grayscale difference to create a smooth, continuous heat distribution
        blurred_diff = cv2.GaussianBlur(gray_diff, (15, 15), 0)

        # Normalize difference to full 0-255 dynamic range if there are changes
        max_val = np.max(blurred_diff)
        if max_val > 0:
            norm_diff = np.uint8((blurred_diff.astype(np.float32) / max_val) * 255.0)
        else:
            norm_diff = blurred_diff

        # Apply false-color heatmap
        color_heatmap = cv2.applyColorMap(norm_diff, colormap)

        # For zero-difference areas, do not tint blue; keep original background
        mask = norm_diff > 10
        blended = current_img.copy()
        blended[mask] = cv2.addWeighted(current_img, 1.0 - alpha, color_heatmap, alpha, 0)[mask]

        return blended

