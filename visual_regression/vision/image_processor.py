import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional

class ImageProcessor:
    """Core image loading, resizing, conversion, and validation utilities using OpenCV and NumPy."""

    @staticmethod
    def load_image(image_path: str) -> np.ndarray:
        """Load an image from disk using OpenCV with proper Unicode / Windows path handling."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at path: {image_path}")
        
        # Using cv2.imdecode with np.fromfile to safely support Unicode paths on Windows
        try:
            stream = open(image_path, "rb")
            bytes_data = bytearray(stream.read())
            stream.close()
            numpy_array = np.asarray(bytes_data, dtype=np.uint8)
            img = cv2.imdecode(numpy_array, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Failed to decode image from path: {image_path}")
            return img
        except Exception as e:
            raise ValueError(f"Could not read image file {image_path}: {str(e)}")

    @staticmethod
    def save_image(img: np.ndarray, output_path: str) -> str:
        """Save an image to disk safely with path directory creation."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # Using imencode to handle unicode/windows paths
        ext = os.path.splitext(output_path)[1]
        if not ext:
            ext = ".png"
            output_path += ext
        success, encoded_img = cv2.imencode(ext, img)
        if not success:
            raise ValueError(f"Failed to encode image to format {ext}")
        with open(output_path, "wb") as f:
            f.write(encoded_img.tobytes())
        return output_path

    @staticmethod
    def validate_dimensions(img1: np.ndarray, img2: np.ndarray) -> bool:
        """Check if two images have identical height, width, and channels."""
        return img1.shape == img2.shape

    @staticmethod
    def align_dimensions(img1: np.ndarray, img2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        If dimensions differ slightly due to viewport scrollbars, resize or pad to match the larger dimensions.
        Preserves original aspect ratio and fills background with white.
        """
        h1, w1 = img1.shape[:2]
        h2, w2 = img2.shape[:2]
        if (h1, w1) == (h2, w2):
            return img1, img2

        max_h = max(h1, h2)
        max_w = max(w1, w2)

        # Pad img1 if needed
        canvas1 = np.full((max_h, max_w, 3), 255, dtype=np.uint8)
        canvas1[:h1, :w1] = img1

        # Pad img2 if needed
        canvas2 = np.full((max_h, max_w, 3), 255, dtype=np.uint8)
        canvas2[:h2, :w2] = img2

        return canvas1, canvas2

    @staticmethod
    def to_grayscale(img: np.ndarray) -> np.ndarray:
        """Convert BGR image to grayscale."""
        if len(img.shape) == 2:
            return img
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

