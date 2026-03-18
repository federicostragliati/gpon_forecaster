import pandas as pd
from prophet import Prophet
from ..domain.ports import ForecastEngine


class ProphetForecaster(ForecastEngine):
    def predict(self, df_history: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
        """
        Recibe el historial desde la DB y devuelve la predicción.
        df_history debe tener columnas: ds (fecha), downstream, upstream.
        """
        if df_history.empty or len(df_history) < 2:
            return pd.DataFrame()  # No hay suficiente data todavía

        # --- MODELO DOWNSTREAM ---
        df_down = df_history[['ds', 'downstream']].rename(columns={'downstream': 'y'})
        model_down = Prophet(daily_seasonality=True)
        model_down.fit(df_down)

        # --- MODELO UPSTREAM ---
        df_up = df_history[['ds', 'upstream']].rename(columns={'upstream': 'y'})
        model_up = Prophet(daily_seasonality=True)
        model_up.fit(df_up)

        # Creamos el futuro (cada 15 min)
        future = model_down.make_future_dataframe(periods=horizon_days * 96, freq='15min')

        forecast_down = model_down.predict(future)
        forecast_up = model_up.predict(future)

        # Combinamos resultados
        results = pd.DataFrame({
            'ds': forecast_down['ds'],
            'down_yhat': forecast_down['yhat'],
            'down_upper': forecast_down['yhat_upper'],
            'up_yhat': forecast_up['yhat'],
            'up_upper': forecast_up['yhat_upper']
        })

        return results