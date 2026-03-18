from abc import ABC, abstractmethod
import pandas as pd

class ForecastEngine(ABC):
    @abstractmethod
    def predict(self, history_file: str, horizon_days: int) -> pd.DataFrame:
        """
        Contrato: Cualquier motor de predicción debe recibir un archivo
        y devolver un DataFrame de Pandas.
        """
        pass
