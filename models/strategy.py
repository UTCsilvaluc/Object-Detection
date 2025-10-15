from abc import ABC, abstractmethod
import os
from .pretrained_models import yolo_model , mask_generator , segment_sam
from .process_detection import process_yolo_results , process_SAM
import cv2
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

class SAMStrategy(BaseModelStrategy):
    def __init__(self , save_dir="img/ModelGen/SAM" , mask_generator=mask_generator):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.mask_generator = mask_generator
    def run(self, image_path, mask_generator=None):
        mg = mask_generator if mask_generator else self.mask_generator
        masks , img , img_result = segment_sam(image_path=image_path , mask_generator=mg)
        return masks , img , img_result
    def process_results(self, masks , img , img_result):
        return process_SAM(masks , img , img_result)