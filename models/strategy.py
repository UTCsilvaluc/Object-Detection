from abc import ABC, abstractmethod
import os
from .pretrained_models import yolo_model , mask_generator , segment_sam
from .process_detection import process_yolo_results , process_SAM
import cv2
import numpy as np
from .helpers import handle_dimensions
class BaseModelStrategy(ABC):
    @abstractmethod
    def run(self, image_path, mask_generator=None):
        """
        Execute the segmentation or detection process.
        :param image_path: Path to the input image.
        :return: Results from the segment or detect method.
        """
        pass
    @abstractmethod
    def process_results(self, raw_results, original_image, annotated_image):
        """
        Process raw results into a structured format.
        :param raw_results: The raw results from the segmentation or detection model.
        :param original_image: The original input image.
        :param annotated_image: The annotated output image.
        :return: Processed results.
        """
        pass
    @abstractmethod
    def merge_objects(self, image, *objects):
        """
        Merge multiple detected objects into one.
        :param objects: Dicts representing detected objects. Please have (mask , bbox , class_id , score).
        :return: mask , bbox , contours of the merged object.
        """
        pass

class YOLOStrategy(BaseModelStrategy):
    def __init__(self , save_dir="img/ModelGen/YOLO"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.model = yolo_model
    def run(self, image_path):
        img = cv2.imread(image_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.model(img_rgb)
        img_result = results[0].plot()  # renvoie un np.array avec les
        save_path = os.path.join(self.save_dir, os.path.basename(image_path))
        cv2.imwrite(save_path, cv2.cvtColor(img_result, cv2.COLOR_RGB2BGR))
        return results , img , img_result 
    def process_results(self, results, img , img_result):
        return process_yolo_results(results, img , img_result)
    def merge_objects(self, image , *objects):
        # Implémentation de la fusion des objets détectés
        pass

class SAMStrategy(BaseModelStrategy):
    def __init__(self , save_dir="img/ModelGen/SAM"  , mask_generator=mask_generator):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.mask_generator = mask_generator
    def run(self, image_path, mask_generator=None):
        mg = mask_generator if mask_generator else self.mask_generator
        masks , img , img_result = segment_sam(image_path=image_path , mask_generator=mg)
        return masks , img , img_result
    def process_results(self, masks , img , img_result):
        return process_SAM(masks , img , img_result)
    def merge_objects(self, image, *objects):
        H, W = image.shape[:2]
        merged_mask = np.zeros((H, W), dtype=np.uint8)

        if len(objects) < 2:
            return None

        for obj in objects:
            obj_mask = np.zeros((H, W), dtype=np.uint8)
            # Si l’objet a un contour → remplir la zone du contour
            if "contour" in obj and obj["contour"]:
                contour = np.array(obj["contour"]).reshape((-1, 1, 2)).astype(np.int32)
                cv2.drawContours(obj_mask, [contour], -1, 255, -1)

            # Sinon utiliser la bbox (cas YOLO)
            elif "bbox" in obj:
                x1, y1, x2, y2 = map(int, obj["bbox"])
                cv2.rectangle(obj_mask, (x1, y1), (x2, y2), 255, -1)

            # Fusion logique du masque
            merged_mask = np.logical_or(merged_mask, obj_mask).astype(np.uint8)

        # Extraction des coordonnées de la zone fusionnée
        ys, xs = np.where(merged_mask > 0)
        if len(xs) == 0 or len(ys) == 0:
            bbox = [0, 0, 0, 0]
        else:
            x_min, x_max = xs.min(), xs.max()
            y_min, y_max = ys.min(), ys.max()
            bbox = [float(x_min), float(y_min), float(x_max), float(y_max)]

        # Extraction du contour final
        contours, _ = cv2.findContours(merged_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnt = max(contours, key=cv2.contourArea)
        contour_points = cnt.reshape(-1, 2).astype(int).tolist()

        return {
            "mask": merged_mask,
            "bbox": bbox,
            "contour": contour_points
        }
