"""
photo_scan.py
------------------------------------

Handles food image loading and preprocessing.

Author:
    Hadassah Abigail

Project:
    Smart Lishe AI
"""

from PIL import Image
import os


class PhotoScanner:
    """
    Handles loading and preparing food images
    for future AI analysis.
    """

    def __init__(self):
        """
        Initialize the photo scanner.
        """
        print("Photo Scanner initialized.")

    def load_image(self, image_path):
        """
        Load an image from disk.

        Parameters:
            image_path (str): Path to the image.

        Returns:
            PIL.Image object
        """

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        image = Image.open(image_path)

        return image

    def resize_image(self, image, size=(224, 224)):
        """
        Resize image for AI models.

        Parameters:
            image
            size

        Returns:
            Resized image
        """

        return image.resize(size)

    def show_image_info(self, image):
        """
        Display image information.
        """

        print(f"Width : {image.width}")
        print(f"Height: {image.height}")
        print(f"Mode  : {image.mode}")

    def preprocess_image(self, image_path):
        """
        Complete preprocessing pipeline.

        Returns:
            Processed image.
        """

        image = self.load_image(image_path)

        self.show_image_info(image)

        image = self.resize_image(image)

        return image