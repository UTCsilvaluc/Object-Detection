from abc import ABC, abstractmethod
import os
from .helpers import segment_object_with_sam
from .pretrained_models import yolo_model , segment_sam 
from .process_detection import process_yolo_results , process_SAM
from utils.helper import save_temp_img , build_img_temp_path
import cv2
import numpy as np
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
    def process_results(self, raw_results, original_image, annotated_image=None):
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
    def generate_embedding(self, image_crop_path):
        """
        Generate embedding for a given image crop.
        :param image_crop_path: Path to the image crop.
        :return: Embedding vector.
        """
        from .object_embedding import generate_embedding_from_crop
        embedding = generate_embedding_from_crop(image_crop_path)
        return embedding    

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
        return process_yolo_results(self, results, img , img_result)
    def merge_objects(self, image , *objects):
        # Implémentation de la fusion des objets détectés
        pass
    def generate_embedding(self, img_rgb , bbox):
        """
        YOLO embedding generation using SAM for precise segmentation.
        Otherwise, backgrounds or other objects may interfere with the embedding.
        """
        crop_object , mask = segment_object_with_sam(img_rgb, bbox)
        _ , crop_path = save_temp_img(crop_object, "temp_embedding")
        from .object_embedding import generate_embedding_from_crop
        embedding = generate_embedding_from_crop(build_img_temp_path(crop_path))
        os.remove(build_img_temp_path(crop_path))  # Nettoyer le crop temporaire
        return embedding


class SAMStrategy(BaseModelStrategy):
    def __init__(self , save_dir="img/ModelGen/SAM"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
    def run(self, image_path, mask_generator=None):
        masks , img , img_result = segment_sam(image_path=image_path)
        return masks , img , img_result
    def process_results(self, masks , img):
        return process_SAM(self, masks , img)
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
        multiple_contours = False
        if (len(contours) > 1):
            #Dilate the mask to connect nearby contours
            kernel = np.ones((3, 3), np.uint8)
            merged_mask = cv2.dilate(merged_mask.astype(np.uint8), kernel, iterations=2)
            merged_mask = cv2.morphologyEx(merged_mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(merged_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if (len(contours) > 1):
                contours = [cnt.reshape(-1, 2).astype(int).tolist() for cnt in contours]
                return {"mask": merged_mask,
                        "bbox": bbox,
                        "contours": contours  
                        }
        else:
            contours = contours if contours else []
        
        if len(contours ) == 0:
            return None
        cnt = max(contours, key=cv2.contourArea)
        contour_points = cnt.reshape(-1, 2).astype(int).tolist() 
        return {
            "mask": merged_mask,
            "bbox": bbox,
            "contour": contour_points
        }
