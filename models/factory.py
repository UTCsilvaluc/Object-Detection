class ModelFactory:
    @staticmethod
    def get_model(strategy: str):
        from .strategy import YOLOStrategy, SAMStrategy
        if strategy == "yolo":
            return YOLOStrategy()
        elif strategy == "sam":
            return SAMStrategy()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
