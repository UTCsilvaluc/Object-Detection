from .strategy import BaseModelStrategy
from .strategy import YOLOStrategy , SAMStrategy

class ModelFactory:
    @staticmethod
    def get_model(strategy: str) -> BaseModelStrategy:
        if strategy == "yolo":
            return YOLOStrategy()
        elif strategy == "sam":
            return SAMStrategy()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")