from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    def profile(self, title: str, description: str): ...
    @abstractmethod
    def follow_up(self, title: str, transcript: str, question_type: str): ...
