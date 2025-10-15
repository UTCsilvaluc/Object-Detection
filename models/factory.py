from .strategy import BaseModelStrategy
from .strategy import YOLOStrategy , SAMStrategy
from .pretrained_models import mask_generator

class ModelFactory:
    @staticmethod
    def get_model(strategy: str) -> BaseModelStrategy:
        if strategy == "yolo":
            return YOLOStrategy()
        elif strategy == "sam":
            return SAMStrategy(mask_generator=mask_generator)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")