import os
import glob # Find all files matching a specified pattern like extensions
import cv2
import numpy as np
def get_images_from_folder(folder_path, extensions=['.jpg', '.jpeg', '.png']):
    """
    Get a list of image file paths from the specified folder with given extensions.
    Args:
        folder_path (str): Path to the folder containing images.
        extensions (list): List of file extensions to look for.
    Returns:
        list: List of image file paths.
    """
    images = []
    for ext in extensions:
        images.extend(glob.glob(os.path.join(folder_path, f'*{ext}')))
    return sorted(images)

def rename_image_in_folder(folder_path , extensions=['.jpg', '.jpeg', '.png']):
    """
    Rename images in the specified folder to a sequential format (e.g., img_1.jpg, img_2.jpg).
    Args:
        folder_path (str): Path to the folder containing images.
        extensions (list): List of file extensions to look for.
    """
    images = get_images_from_folder(folder_path, extensions)
    for idx, img_path in enumerate(images):
        ext = os.path.splitext(img_path)[1]
        new_name = f'img_{idx + 1}{ext}'
        new_path = os.path.join(folder_path, new_name)
        os.rename(img_path, new_path)
    print(f"{len(images)} images renommées avec succès.")

def denoise_image(image, h=10, hColor=10, templateWindowSize=7, searchWindowSize=21):
    """
    Denoise an image using OpenCV's fastNlMeansDenoisingColored function.
    Args:
        image (numpy.ndarray): Input image to be denoised.
        h (int): Parameter regulating filter strength for luminance component.
        hColor (int): Parameter regulating filter strength for color components.
        templateWindowSize (int): Size in pixels of the template patch.
        searchWindowSize (int): Size in pixels of the window that is used to compute weighted average.
    Returns:
        numpy.ndarray: Denoised image.
    """
    if image is None:
        raise ValueError("Image not loaded correctly!")

    # Si l'image est en niveaux de gris (1 canal), on la convertit en BGR
    if len(image.shape) == 2 or image.shape[2] == 1:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    # Vérification du type
    if image.dtype != np.uint8:
        image = (255 * (image / image.max())).astype(np.uint8)

    denoised_image = cv2.fastNlMeansDenoisingColored(
        image, None, h, hColor, templateWindowSize, searchWindowSize
    )
    return denoised_image


rename_image_in_folder('img/Images')