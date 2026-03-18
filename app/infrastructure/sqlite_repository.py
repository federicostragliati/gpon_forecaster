import sqlite3
import pandas as pd
from datetime import datetime
from ..domain.models import TrafficMetric

class SQLiteTrafficRepository:
    def __init__(self, db_path: str = "gpon_monitoring.db"):
        self.db_path = db_path
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traffic_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    port_id TEXT,
                    timestamp DATETIME,
                    downstream REAL,
                    upstream REAL
                )
            """)
            # Índice para que las consultas por puerto sean rápidas
            conn.execute("CREATE INDEX IF NOT EXISTS idx_port ON traffic_history(port_id)")

    def save_metric(self, port_id: str, down: float, up: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO traffic_history (port_id, timestamp, downstream, upstream) VALUES (?, ?, ?, ?)",
                (port_id, datetime.now(), down, up)
            )

    def get_history_for_prophet(self, port_id: str):
        """Devuelve los datos en el formato que Prophet necesita (ds, y)"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT timestamp as ds, downstream, upstream 
                FROM traffic_history 
                WHERE port_id = ? 
                ORDER BY timestamp ASC
            """
            return pd.read_sql_query(query, conn, params=(port_id,))