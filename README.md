# GPON Forecaster

Sistema de monitoreo y predicción de tráfico para redes GPON/FTTH.
Consulta OLTs Huawei via SNMP, almacena el historial en SQLite, entrena un modelo
de forecasting con [Prophet](https://facebook.github.io/prophet/) y expone un
dashboard interactivo con predicción a 7 días.

---

## Arquitectura

```
OLT Huawei (SNMP)
      │
      ▼
poll_worker.py          ← corre continuamente, recolecta tráfico cada N segundos
      │
      ▼
gpon_monitoring.db      ← historial de tráfico (SQLite)
      │
      ├──▶ train_and_save.py     ← entrena modelos Prophet (correr 1×/día o manualmente)
      │         │
      │         ▼
      │    model_<OLT>_<puerto>_<dirección>.json
      │
      └──▶ visualize_forecast.py ← genera gráfico Plotly embebible en HTML
```

---

## Requisitos

- Python 3.10 o superior
- Acceso SNMP (UDP 161) a las OLTs desde el host donde corre el poller
- Las OLTs deben tener habilitado SNMP v2c con la community configurada

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/federicostragliati/gpon_forecaster.git
cd gpon_forecaster

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## Configuración

Copiá el archivo de ejemplo y completá con tus datos reales:

```bash
cp config.example.json config.json
```

```json
{
  "polling_interval": 60,
  "cap_mbps": 10000,
  "olts": [
    {
      "name": "OLT-SM03",
      "ip": "10.0.255.94",
      "community": "TU_COMMUNITY_SNMP",
      "ports": [
        {"id": "0/8/0", "index": "234946560"},
        {"id": "0/9/0", "index": "234954752"}
      ]
    }
  ]
}
```

| Campo             | Descripción                                                  |
|-------------------|--------------------------------------------------------------|
| `polling_interval`| Segundos entre cada consulta SNMP                            |
| `cap_mbps`        | Capacidad máxima del uplink en Mbps (límite del modelo)      |
| `name`            | Nombre identificador de la OLT (se usa en nombres de archivo)|
| `ip`              | IP de gestión de la OLT                                      |
| `community`       | Community string SNMP v2c (solo lectura)                     |
| `ports[].id`      | ID legible del puerto GPON (ej. `0/8/0`)                     |
| `ports[].index`   | OID numérico del puerto para la consulta SNMP                |

> **Importante:** `config.json` está en `.gitignore` y nunca debe commitearse.
> Usá `config.example.json` como plantilla versionada sin credenciales.

---

## Uso

### 1. Iniciar el poller (recolección continua)

```bash
python poll_worker.py
```

Corre indefinidamente. Se recomienda ejecutarlo como servicio systemd en Linux
o como tarea programada en Windows. Logs en consola con timestamp.

### 2. Entrenar los modelos

Ejecutar manualmente o via cron/Task Scheduler una vez por día con datos nuevos:

```bash
python train_and_save.py
```

Requiere al menos 10 puntos por puerto en la base de datos.
Genera un archivo `model_<OLT>_<puerto>_<dirección>.json` por cada combinación.

### 3. Ver el dashboard

```bash
# Si usás Flask
flask --app app run

# O desde Python directamente para prueba rápida
python -c "
from visualize_forecast import generate_interactive_graph
html = generate_interactive_graph('OLT-SM03', '0/8/0')
open('out.html', 'w').write(html)
"
# Abrir out.html en el navegador
```

---

## Obtener el OID (index) de un puerto GPON

Desde la CLI de la OLT Huawei (MA5600/MA5800):

```
display ont info 0 8 all
```

O via SNMP walk:

```bash
snmpwalk -v2c -c <community> <ip-olt> ifDescr | grep "GPON 0/8"
```

El número del `ifIndex` correspondiente es el valor a usar en `ports[].index`.

---

## Estructura del proyecto

```
gpon_forecaster/
├── app/
│   └── infrastructure/
│       ├── snmp_adapter.py        # Consulta SNMP a OLTs Huawei
│       └── sqlite_repository.py   # Persistencia en SQLite
├── static/                        # Assets del dashboard web
├── poll_worker.py                 # Proceso de recolección continua
├── train_and_save.py              # Entrenamiento de modelos Prophet
├── visualize_forecast.py          # Generación de gráficos Plotly
├── config.example.json            # Plantilla de configuración (sin credenciales)
├── requirements.txt
└── README.md
```

---

## Archivos ignorados (no se versionan)

```
config.json          # credenciales SNMP
*.db                 # base de datos con tráfico de producción
model_*.json         # modelos entrenados (se regeneran)
.idea/               # configuración de PyCharm
__pycache__/
.venv/
```

---

## Troubleshooting

**El poller muestra "Lectura ignorada (Timeout)"**
- Verificar conectividad UDP 161 hacia la OLT: `snmpget -v2c -c <community> <ip> sysDescr.0`
- Confirmar que el `index` del puerto es correcto

**`train_and_save.py` dice "Datos insuficientes"**
- El poller necesita haber recolectado al menos 10 puntos para ese puerto
- Verificar que la tabla `traffic_history` tiene filas: `sqlite3 gpon_monitoring.db "SELECT COUNT(*) FROM traffic_history"`

**El gráfico no muestra predicción futura**
- Verificar que existen los archivos `model_*.json` para esa OLT y puerto
- Re-ejecutar `train_and_save.py`

---

## Tecnologías

| Librería   | Uso                                          |
|------------|----------------------------------------------|
| Prophet    | Forecasting de series temporales con estacionalidad diaria |
| Plotly     | Gráficos interactivos con zoom y rangeslider |
| pandas     | Manipulación de datos y consultas a SQLite   |
| pysnmp     | Consultas SNMP v2c a OLTs Huawei             |
| SQLite     | Almacenamiento local del historial de tráfico|

---

## Licencia

Uso interno. Todos los derechos reservados.
