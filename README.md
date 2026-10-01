# AI Support Crew

Sistema multiagente educativo para analizar incidentes técnicos de soporte con Python y CrewAI.

Esta versión incluye modelos de dominio Pydantic, Tools, Agents, Tasks y un Crew secuencial. AWS, Docker y cualquier integración externa quedan fuera del alcance actual.

## Arquitectura

```text
ai-support-crew/
├── src/
│   ├── main.py             # Punto de entrada de la pipeline
│   ├── config.py           # Configuración desde variables de entorno
│   ├── models/             # Modelos Pydantic compartidos
│   ├── agents/             # Agentes CrewAI
│   ├── tasks/              # Tareas CrewAI y contexto entre etapas
│   ├── tools/              # Herramientas de los agentes (futuro)
│   ├── services/           # Servicios de datos y construcción del Crew
│   └── flows/              # Flows y estado tipado de la pipeline
├── tests/                  # Pruebas automatizadas
├── data/                   # Datos locales simulados
├── .env.example            # Plantilla de configuración
├── .gitignore
├── requirements.txt
└── README.md
```

### Flujo de análisis

Cuando se implementen los agentes, el flujo será:

1. **Triage Agent**: clasifica severidad, área afectada y resumen.
2. **Log Analyst Agent**: analiza logs simulados y propone causas posibles.
3. **Solution Agent**: combina ambos resultados, propone causa raíz, pasos de resolución y escalamiento.

Los modelos Pydantic sirven como contratos explícitos entre etapas. `Incident`, `TriageResult`, `LogAnalysis` y `Resolution` validan la forma y los valores de los datos antes de que pasen al siguiente componente. La orquestación será asíncrona con `asyncio`.

## Requisitos

- Python 3.11 o superior
- pip

## Configuración local

### 1. Crear el entorno virtual

Windows PowerShell:

```powershell
python -m venv .venv
```

Activarlo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, puede ejecutarse la política para el usuario actual:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 2. Instalar dependencias

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Crear la configuración local

```powershell
Copy-Item .env.example .env
```

El archivo `.env` es local y no debe subirse al repositorio.

### 4. Configurar el proveedor LLM

Para desarrollo local con Gemini, completa estas variables en `.env`:

```env
LLM_PROVIDER=litellm
LLM_MODEL=gemini/gemini-3.5-flash-lite
GEMINI_API_KEY=tu-api-key-de-gemini
```

La clave se lee desde `GEMINI_API_KEY` y nunca está escrita en el código fuente. El prefijo `gemini/` identifica el proveedor para LiteLLM; `LLM_PROVIDER=litellm` fuerza la ruta LiteLLM en la versión actual de CrewAI.

## Amazon Bedrock como backend alternativo

La creación del LLM está aislada en `src/agents/incident_agents.py`. Los Agents,
Tasks, Tools, modelos Pydantic, servicios asíncronos y Flow no dependen del proveedor.
Para usar Bedrock temporalmente, cambia solo estas variables en `.env`:

```env
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

El código transforma el model ID en la ruta LiteLLM `bedrock/<model-id>`. LiteLLM
utiliza `boto3`, que obtiene credenciales mediante la cadena estándar de AWS: perfil
local, AWS IAM Identity Center/SSO, variables de entorno, credenciales temporales o
rol asociado al entorno. No se configura `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
ni ningún secreto en el código o en `.env.example`.

### Qué debes configurar manualmente en AWS

Antes de ejecutar la aplicación con Bedrock debes:

1. Tener una cuenta AWS y seleccionar una región donde esté disponible el modelo.
2. Habilitar o solicitar acceso al modelo desde Amazon Bedrock, según corresponda.
3. Configurar una identidad AWS local, por ejemplo `aws configure sso` o un perfil
   compatible con boto3.
4. Conceder a esa identidad permisos mínimos para invocar el modelo.
5. Verificar cuotas, límites y costos de inferencia.

Como mínimo, la política IAM suele incluir `bedrock:InvokeModel` sobre el ARN del
modelo; si se utiliza streaming puede requerir también
`bedrock:InvokeModelWithResponseStream`. El ARN y los permisos exactos dependen del
tipo de modelo, región o inference profile. La aplicación traduce errores comunes de
credenciales ausentes, región inválida, acceso denegado y errores de servicio a
mensajes accionables, pero no modifica IAM ni crea recursos AWS.

## Errores y reintentos del LLM

`src/config.py` determina el proveedor concreto a partir de `LLM_PROVIDER` y del
prefijo del modelo. Un modelo `gemini/...` se trata como Gemini; un proveedor
`bedrock` o modelo `bedrock/...` se trata como Amazon Bedrock.

`src/services/llm_retry_service.py` envuelve el `LLM.call()` que reciben los Agents.
Por eso un fallo durante una completion, structured output o native tool call repite
solo esa operación; no reinicia el Flow ni vuelve a ejecutar Triage, Memory o Gather
Context. Los errores transitorios `429`, `500`, `502`, `503` y `504` se reintentan
como máximo `LLM_MAX_RETRIES` veces (5 por defecto) con backoff exponencial y un
jitter pequeño. `LLM_RETRY_BASE_DELAY` controla el delay inicial (2 segundos por
defecto), por lo que los delays nominales son 2, 4, 8 y 16 segundos.

CrewAI tiene un retry interno limitado para rate limits y LiteLLM acepta
`num_retries`; el proyecto desactiva el retry de LiteLLM por request (`num_retries=0`)
y centraliza la política provider-aware en el `LLM.call()` para evitar retries
duplicados y registrar cada intento. Los errores permanentes, como autenticación,
modelo inválido y validación de la aplicación, no se reintentan. Si Gemini falla
continuamente, el mensaje final es `Gemini remained unavailable after 5 attempts.`

Agrega estas variables a `.env` si quieres cambiar la política:

```env
LLM_MAX_RETRIES=5
LLM_RETRY_BASE_DELAY=2
```

No existe fallback automático entre proveedores. Bedrock solo se utiliza cuando se
configura explícitamente `LLM_PROVIDER=bedrock`, por lo que un fallo de Gemini no
puede generar consumo en AWS.

### 5. Ejecutar el análisis

Desde la raíz del proyecto:

```powershell
python -m src.main
```

El programa muestra los incidentes disponibles, solicita una selección y ejecuta la pipeline secuencial. La salida contiene:

```text
INCIDENT
TRIAGE RESULT
LOG ANALYSIS
FINAL RESOLUTION
```

### 6. Ejecutar las pruebas

```powershell
python -m pytest -q
```

## Dependencias

- **CrewAI**: framework para definir agentes, tareas y equipos multiagente.
- **LiteLLM**: adaptador de proveedor utilizado para enrutar CrewAI hacia Gemini y facilitar el futuro cambio a Bedrock.
- **Pydantic**: validación y serialización de modelos tipados; será el contrato entre agentes.
- **asyncio**: soporte de Python para ejecutar operaciones asíncronas y coordinar el flujo.
- **pytest**: framework de pruebas automatizadas.
- **pytest-asyncio**: permite probar funciones `async` con pytest.
- **python-dotenv**: carga variables de configuración desde un archivo `.env` durante el desarrollo local.

## Recolección asíncrona de contexto

`src/services/incident_data_service.py` simula tres consultas independientes: logs, métricas y estado del servicio. Cada una espera una latencia de red simulada con `asyncio.sleep()`.

`get_incident_context_sequential()` las ejecuta una después de otra. `gather_incident_context()` las inicia concurrentemente con `asyncio.gather()`, por lo que el tiempo total se aproxima a la consulta más lenta en lugar de la suma de las tres.

El resultado se valida como un modelo Pydantic `IncidentContext`, listo para ser consumido por los agentes en una etapa posterior.

## Próximas etapas

1. Añadir pruebas de integración con un proveedor LLM configurado.
2. Incorporar persistencia o datos externos solo cuando el flujo local esté validado.
3. Incorporar AWS y Docker en una etapa posterior.

## CrewAI Tools

Las herramientas en `src/tools/incident_tools.py` exponen operaciones pequeñas y específicas para un futuro Agent: logs, métricas, estado del servicio y búsqueda en la knowledge base local. Cada herramienta tiene un nombre y descripción para el LLM, un `args_schema` Pydantic para validar inputs y un resultado JSON-compatible.

Todavía no se implementaron Agents. Un Agent podrá elegir una Tool cuando su descripción indique que es adecuada para resolver la necesidad actual; CrewAI proporciona al LLM la lista de herramientas y el modelo decide cuál invocar, con qué argumentos y cuándo continuar razonando.

## Agents

`src/agents/incident_agents.py` define tres fábricas: `create_triage_agent()`, `create_log_analyst_agent()` y `create_solution_agent()`. Las fábricas no ejecutan el Crew ni llaman al LLM al importarse.

La API key se lee exclusivamente desde `GEMINI_API_KEY`. El proveedor y el modelo se configuran con `LLM_PROVIDER` y `LLM_MODEL`. Para cambiar posteriormente a Bedrock, se modifica esta capa de configuración/creación del LLM; los Agents y Tasks no necesitan cambios.

## Pipeline con Tasks y Crew

`src/tasks/incident_tasks.py` define tres Tasks con `description`, `expected_output`, Agent y `output_pydantic`:

1. Triage → `TriageResult`.
2. Log analysis → `LogAnalysis`, usando el resultado del triage como `context`.
3. Solution → `Resolution`, usando los resultados de las dos Tasks anteriores.

`src/services/incident_crew_service.py` construye un `Crew` con `Process.sequential`. El Crew ejecuta las Tasks en orden y CrewAI agrega los outputs previos al contexto de las siguientes. No se ejecuta nada al importar los módulos; la ejecución comienza únicamente desde `main.py`.

## Incident Flow

`src/flows/incident_flow.py` envuelve la pipeline en un Flow actual de CrewAI usando `@start()`, `@listen()` y `@router()`:

```text
START → Load Incident → Gather Context → Run Triage → Run Log Analysis
                                      → LOW/MEDIUM: Resolution
                                      → HIGH/CRITICAL: Resolution + Escalation
```

El estado `IncidentFlowState` es un modelo Pydantic tipado. Guarda el incidente, el contexto recolectado, `TriageResult`, `LogAnalysis`, la ruta elegida y `Resolution`. Cada etapa emite un log con el nombre de la etapa para facilitar el seguimiento.

## Memoria de incidentes

El proyecto usa la clase oficial `crewai.Memory` disponible en CrewAI 1.15.23. La
memoria se guarda localmente en `data/memory/` mediante el backend LanceDB incluido
por CrewAI; no se agrega una base vectorial externa.

`data/historical_incidents.json` contiene incidentes resueltos ficticios. En la etapa
**Load Incident**, `IncidentMemoryService` los incorpora una sola vez a Memory y luego
ejecuta una recuperación superficial (`recall(..., depth="shallow")`) usando como
consulta el título, descripción, servicio y logs del incidente actual. El resultado
se transforma en texto controlado y se pasa como `historical_context` al Log Analyst.
El agente debe tratarlo como una hipótesis y verificarlo con las Tools actuales.

También se guarda la resolución actual para que pueda servir como referencia en una
ejecución futura. La memoria conserva texto, identificador de incidente, servicio,
categorías, importancia y el embedding local. El embedding de este ejemplo es un
vector determinista de tokens; evita depender de otra API de embeddings y mantiene
el cambio futuro a Bedrock aislado en el servicio de memoria.

Esta es una memoria educativa: el ranking puede producir falsos positivos, no
entiende causalidad por sí mismo y no reemplaza la validación de logs, métricas ni
estado actual. La persistencia local tampoco ofrece alta disponibilidad, control de
acceso, retención ni escalabilidad multiinstancia. En producción habría que definir
esas políticas y probablemente migrar el backend a un almacén gestionado.

## Ejecución con Docker

La imagen usa `python:3.11-slim`, instala las dependencias del proyecto y copia
solamente el código de `src/` y los JSON locales necesarios para ejecutar la CLI.
`.env`, tests, caches, entornos virtuales y archivos de credenciales quedan fuera del
contexto de construcción mediante `.dockerignore`.

Construir la imagen desde la raíz del proyecto:

```powershell
docker build -t ai-support-crew .
```

Ejecutar usando las variables del archivo local:

```powershell
docker run --env-file .env -it ai-support-crew
```

El `-it` permite responder la selección interactiva del incidente. La API key no se
incluye en la imagen: Docker la inyecta solamente al iniciar el contenedor mediante
`--env-file`. Si se quiere conservar la memoria entre contenedores, puede montarse
un volumen sobre `/app/data/memory`.

### Conceptos básicos de Docker

- **Dockerfile**: receta declarativa con los pasos para construir la aplicación.
- **Docker image**: artefacto inmutable generado a partir del Dockerfile.
- **Docker container**: proceso aislado creado al ejecutar una imagen.
- **Docker registry**: servicio que almacena y distribuye imágenes, como Docker Hub
  o un registry privado.
