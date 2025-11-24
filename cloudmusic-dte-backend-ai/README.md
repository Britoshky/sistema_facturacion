# CloudMusic DTE - Backend IA

**Backend especializado en Inteligencia Artificial para el sistema CloudMusic DTE**  
Implementa los requisitos RF010, RF011, RF012 del informe del proyecto.

## Características Principales

### 🤖 Chat IA Especializado
- Asistente conversacional experto en normativa DTE chilena
- Múltiples contextos especializados (técnico, contable, legal)
- Integración con Ollama para IA local (Llama 3.2 3B)
- Historial de conversaciones y búsqueda semántica

### 📊 Análisis Inteligente de Documentos
- **Detección de Fraudes**: Identificación automática de anomalías
- **Verificación de Cumplimiento**: Validación contra normativa SII
- **Análisis Financiero**: Evaluación de métricas y riesgos
- **Análisis de Patrones**: Detección de tendencias y comportamientos

### 🔗 Integración Microservicios
- Comunicación con backend Node.js via Redis Pub/Sub
- Notificaciones en tiempo real via WebSockets
- Arquitectura escalable y modular
- Base de datos compartida (MongoDB + PostgreSQL)

## Arquitectura Técnica

### Stack Tecnológico
- **Framework**: FastAPI 0.104+ (Python 3.11.6)
- **IA Local**: Ollama + Llama 3.2 3B
- **Base de Datos**: MongoDB 7.0 (documentos IA)
- **Cache/Messaging**: Redis 7.2
- **Validación**: Pydantic v2
- **Logging**: Loguru
- **Gestión Dependencias**: Poetry

### Arquitectura de Servicios
```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Next.js                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                Backend Node.js + tRPC                       │
│          (DTE Processing, SII Integration)                   │
└─────────────────────────┬───────────────────────────────────┘
                          │ Redis Pub/Sub
┌─────────────────────────┴───────────────────────────────────┐
│                Backend Python + FastAPI                     │
│            (IA Chat, Document Analysis)                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│  MongoDB (IA Data) + PostgreSQL (Business Data) + Redis    │
└─────────────────────────────────────────────────────────────┘
```

## Instalación y Configuración

### Prerrequisitos
1. **Python 3.11.6**
2. **Poetry** (gestión de dependencias)
3. **Ollama** con modelo Llama 3.2 3B
4. **MongoDB 7.0**
5. **Redis 7.2**

### Instalación

1. **Clonar repositorio y navegar al directorio IA**:
```bash
cd cloudmusic-dte-backend-ai
```

2. **Instalar dependencias con Poetry**:
```bash
poetry install
```

3. **Configurar variables de entorno**:
```bash
cp .env.example .env
# Editar .env con configuración local
```

4. **Instalar y configurar Ollama**:
```bash
# Descargar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelo Llama 3.2 3B
ollama pull llama3.2:3b
```

5. **Iniciar servicios**:
```bash
# MongoDB (si no está corriendo)
sudo systemctl start mongod

# Redis (si no está corriendo)  
sudo systemctl start redis

# Ollama
ollama serve
```

### Ejecución

**Desarrollo**:
```bash
poetry run python -m src.main
# o
poetry shell
python -m src.main
```

**Producción**:
```bash
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8001
```

## Configuración

### Variables de Entorno (.env)

```bash
# Aplicación
DEBUG=true
APP_NAME="CloudMusic DTE IA Backend"
APP_VERSION="1.0.0"
SECRET_KEY="your-secret-key-change-in-production"

# Base de datos
MONGODB_URL="mongodb://localhost:27017"
MONGODB_DATABASE="cloudmusic_dte_ai"

# Redis
REDIS_URL="redis://localhost:6379"
REDIS_CHANNEL_PREFIX="cloudmusic_dte"

# Ollama IA
OLLAMA_HOST="http://localhost:11434"
OLLAMA_MODEL="llama3.2:3b"
OLLAMA_TIMEOUT=30
OLLAMA_CONTEXT_SIZE=4096
OLLAMA_TEMPERATURE=0.7
OLLAMA_MAX_TOKENS=1000

# API
API_PREFIX="/api/v1"
CORS_ORIGINS="http://localhost:3000,http://localhost:3001"

# Performance  
MAX_CONCURRENT_ANALYSES=5
MAX_BATCH_SIZE=50
CACHE_TTL_SECONDS=3600
```

## API Endpoints

### Chat IA (`/api/v1/chat`)

- `POST /sessions` - Crear sesión de chat
- `POST /sessions/{id}/messages` - Enviar mensaje  
- `GET /sessions/{id}/messages` - Obtener historial
- `GET /sessions` - Listar sesiones
- `DELETE /sessions/{id}` - Cerrar sesión
- `GET /search` - Buscar conversaciones
- `GET /analytics` - Analíticas de chat

### Análisis de Documentos (`/api/v1/analysis`)

- `POST /analyze` - Analizar documento individual
- `POST /batch-analyze` - Análisis en lote
- `POST /validate` - Validar estructura
- `GET /documents/{id}/history` - Historial análisis
- `POST /upload-analyze` - Subir y analizar archivo
- `GET /types` - Tipos de análisis disponibles
- `GET /risk-levels` - Niveles de riesgo

### Sistema (`/api/v1/system`)

- `GET /health` - Estado del sistema
- `GET /ollama/status` - Estado de Ollama
- `POST /ollama/pull-model/{name}` - Descargar modelo
- `GET /metrics` - Métricas del sistema
- `GET /logs/recent` - Logs recientes
- `GET /config` - Configuración del sistema

## Tipos de Análisis IA

### 1. Detección de Fraudes (`fraud_detection`)
Identifica anomalías y posibles fraudes:
- Inconsistencias en cálculos
- Patrones sospechosos de facturación
- Validación de RUT y datos
- Análisis de comportamiento atípico

### 2. Verificación de Cumplimiento (`compliance_check`)
Valida cumplimiento normativo SII:
- Esquemas XML correctos
- Campos obligatorios
- Rangos de folios válidos
- Certificación digital
- Plazos de emisión

### 3. Análisis Financiero (`financial_analysis`)
Evaluación financiera y tributaria:
- Cálculos de impuestos
- Márgenes y rentabilidad
- Flujo de caja proyectado
- Clasificación contable

### 4. Análisis de Patrones (`pattern_analysis`)
Identificación de tendencias:
- Patrones de consumo
- Estacionalidad
- Predicciones futuras
- Comparación histórica

## Contextos de Chat IA

### General (`general`)
Consultas generales sobre DTE y normativa SII.

### Técnico (`technical`) 
Soporte para implementación e integración técnica.

### Contable (`accounting`)
Aspectos contables, tributarios y cálculos.

### Legal (`legal`)
Normativa, resoluciones SII y cumplimiento legal.

## Integración con Sistema Principal

### Comunicación Redis
- **Canal WebSocket**: `cloudmusic_dte:websocket`
- **Canal Sistema**: `cloudmusic_dte:system` 
- **Canal Documentos**: `cloudmusic_dte:documents`
- **Canal Notificaciones**: `cloudmusic_dte:notifications`

### Eventos Publicados
- Respuestas de chat IA
- Completación de análisis
- Cambios de estado del sistema
- Notificaciones de usuario

### Eventos Suscritos  
- Solicitudes de análisis desde Node.js
- Eventos de documentos
- Notificaciones de usuario
- Cambios de estado del sistema

## Desarrollo y Testing

### Estructura del Proyecto
```
src/
├── contracts/          # Tipos compartidos (Pydantic)
├── services/          # Lógica de negocio
├── api/              # Endpoints FastAPI
├── core/             # Configuración y dependencias
└── main.py           # Aplicación principal
```

### Testing
```bash
# Ejecutar tests
poetry run pytest

# Coverage
poetry run pytest --cov=src

# Tests específicos
poetry run pytest tests/test_chat_service.py
```

### Linting y Formato
```bash
# Black (formato)
poetry run black src/

# Flake8 (linting)
poetry run flake8 src/

# MyPy (type checking)
poetry run mypy src/
```

## Monitoring y Logs

### Logs
- **Consola**: Desarrollo (con colores)
- **Archivo**: Producción (`logs/ai_backend.log`)
- **Rotación**: 100MB, retención 30 días
- **Niveles**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Métricas
- Solicitudes de chat procesadas
- Análisis de documentos completados
- Tiempo de respuesta promedio
- Estado de servicios dependientes

### Health Checks
- MongoDB conectividad
- Redis disponibilidad  
- Ollama estado y modelos
- Memoria y recursos del sistema

## Contribución

### Workflow de Desarrollo
1. Crear rama feature desde `main`
2. Implementar cambios siguiendo estándares
3. Escribir tests apropiados
4. Ejecutar linting y tests
5. Crear Pull Request con descripción detallada

### Estándares de Código
- **Formato**: Black
- **Linting**: Flake8
- **Type Hints**: Obligatorios (MyPy)
- **Docstrings**: Google Style
- **Testing**: PyTest con coverage >90%

### Commits Semánticos
```
feat: nueva funcionalidad
fix: corrección de bug
docs: actualización documentación
refactor: refactorización sin cambios funcionales
test: agregar o modificar tests
perf: mejora de performance
```

## Licencia

Copyright © 2025 CloudMusic DTE - Proyecto de Título IPLACEX

Este proyecto es parte de un trabajo académico para el programa de Ingeniería en Informática de IPLACEX.

## Contacto y Soporte

Para consultas sobre implementación, configuración o desarrollo:

- **Documentación API**: http://localhost:8001/docs (desarrollo)
- **Health Check**: http://localhost:8001/health
- **Logs**: Consultar archivos en `logs/` o consola durante desarrollo

---

**Nota**: Este backend IA está específicamente diseñado para la normativa tributaria chilena del SII y optimizado para el procesamiento local con Ollama, garantizando privacidad y control total de los datos.