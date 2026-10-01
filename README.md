# AI Support Crew

AI Support Crew is a multi-agent system built with **Python, CrewAI and LLMs** to automate the analysis of IT support incidents.

The system receives a technical incident, gathers contextual information, retrieves similar historical incidents from memory, performs AI-powered triage and log analysis, determines severity, and dynamically routes the incident toward a standard resolution or an engineering escalation.

The project is designed as a practical example of how **agentic AI systems can support real-world IT operations and incident management workflows**.

## Key Features

- Multi-agent architecture with specialized AI agents
- Automated incident triage
- AI-powered log analysis
- Structured outputs validated with Pydantic
- Dynamic severity-based routing
- Automatic escalation for HIGH/CRITICAL incidents
- Historical incident memory with CrewAI Memory
- Concurrent context collection with asyncio
- LLM retry strategy with exponential backoff
- Gemini integration through LiteLLM
- Optional Amazon Bedrock provider support
- Automated tests with pytest
- Dockerized execution
- Secure environment-variable configuration

## Architecture

The system follows this workflow:

```text
                    ┌──────────────────────┐
                    │      Incident        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Load Incident     │
                    └──────────┬───────────┘
                               │
                     Historical Memory
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Gather Context     │
                    │ logs / metrics / svc │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Triage Agent      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Log Analyst Agent    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Severity Router     │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
          LOW / MEDIUM                 HIGH / CRITICAL
                 │                           │
                 ▼                           ▼
       Standard Resolution          Escalated Resolution
                 │                           │
                 └─────────────┬─────────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Final Resolution    │
                    └──────────────────────┘
```

The workflow is orchestrated using **CrewAI Flow**, including typed state and severity-based routing.

## AI Agents

### Triage Agent

Analyzes the incident and determines:

- severity
- affected service or area
- incident summary
- whether immediate action is required

Output is validated using the `TriageResult` Pydantic model.

### Log Analyst Agent

Analyzes logs, current incident context and relevant historical incidents.

It produces:

- relevant errors
- probable causes
- confidence score

Historical incidents are treated as supporting hypotheses rather than authoritative answers. Current logs and context remain the primary evidence.

### Solution Agent

Generates the final incident resolution using the results from triage and log analysis.

The resolution includes:

- probable root cause
- recommended remediation steps
- escalation decision
- escalation reason

HIGH and CRITICAL incidents are dynamically routed through the escalation path.

## Example

One of the included sample incidents represents a payment API returning HTTP 500 errors immediately after a deployment.

Input:

```text
INC-001 - HTTP 500 after deployment

ERROR Internal Server Error:
missing environment variable PAYMENT_GATEWAY_URL
```

The system identifies:

```json
{
  "severity": "HIGH",
  "affected_area": "payments-api",
  "requires_immediate_action": true
}
```

Log analysis determines that the deployment omitted the required environment variable with a high confidence score.

The Flow then routes the incident through:

```text
HIGH → escalated_resolution
```

The generated resolution recommends verifying the deployment configuration, restoring the missing environment variable, redeploying the service and validating the API with a test request.

Because the incident is HIGH severity, the system also recommends escalation to Development/Engineering.

## Incident Memory

The project uses **CrewAI Memory** to retrieve similar historical incidents.

When an incident is loaded:

1. Historical resolved incidents are stored in local memory.
2. The current incident is used as a search query.
3. Similar incidents are retrieved.
4. Relevant historical context is provided to the Log Analyst.
5. The agent validates historical hypotheses against the current incident evidence.
6. The final resolution can be stored for future analysis.

Memory is persisted locally under:

```text
data/memory/
```

The implementation intentionally uses local storage for development and demonstration purposes.

A production implementation could replace this with a managed vector database or persistent knowledge platform.

## Async Context Collection

Incident context is gathered from multiple simulated sources:

- application logs
- service metrics
- service status

These operations are executed concurrently using:

```python
asyncio.gather()
```

This simulates the behavior of a support system querying multiple observability sources without waiting for each operation sequentially.

## LLM Integration

The project currently uses **Gemini through LiteLLM**.

Example configuration:

```env
LLM_PROVIDER=litellm
LLM_MODEL=gemini/gemini-3.5-flash-lite
GEMINI_API_KEY=your_api_key
```

The LLM provider is isolated from the agent and workflow logic, allowing alternative providers to be integrated without redesigning the complete system.

### Amazon Bedrock

Amazon Bedrock is supported as an alternative provider through configuration.

```env
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=your-model-id
```

Bedrock is never activated automatically. This prevents an unavailable Gemini model from unexpectedly generating AWS usage or costs.

AWS credentials are resolved through the standard AWS/boto3 credential chain rather than being stored in source code.

## Retry Strategy

Transient LLM failures are handled by a centralized retry service.

Retryable failures include common temporary errors such as:

```text
429
500
502
503
504
```

The strategy uses:

- configurable maximum attempts
- exponential backoff
- jitter
- provider-aware error handling
- logging for individual retry attempts

Permanent errors such as invalid credentials or invalid model configuration are not repeatedly retried.

Example:

```env
LLM_MAX_RETRIES=5
LLM_RETRY_BASE_DELAY=2
```

This keeps retry behavior centralized instead of allowing multiple framework layers to perform overlapping retries.

## Project Structure

```text
ai-support-crew/
├── src/
│   ├── main.py
│   ├── config.py
│   │
│   ├── agents/
│   │   └── incident_agents.py
│   │
│   ├── flows/
│   │   └── incident_flow.py
│   │
│   ├── models/
│   │   └── domain.py
│   │
│   ├── services/
│   │   ├── incident_crew_service.py
│   │   ├── incident_data_service.py
│   │   ├── incident_memory_service.py
│   │   ├── llm_error_service.py
│   │   ├── llm_retry_service.py
│   │   └── sample_incident_service.py
│   │
│   ├── tasks/
│   │   └── incident_tasks.py
│   │
│   └── tools/
│       └── incident_tools.py
│
├── tests/
├── Dockerfile
├── requirements.txt
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

## Tech Stack

**Language**

- Python 3.11+

**AI / Agentic AI**

- CrewAI
- CrewAI Flows
- LiteLLM
- Google Gemini
- Amazon Bedrock compatible architecture

**Data & Validation**

- Pydantic
- JSON
- CrewAI Memory / LanceDB

**Concurrency**

- asyncio

**Testing**

- pytest
- pytest-asyncio

**Infrastructure**

- Docker

## Local Installation

Clone the repository:

```bash
git clone https://github.com/FrancoLavi/ai-support-crew.git
cd ai-support-crew
```

Create a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Configure the LLM provider and API key inside `.env`.

Run the application:

```bash
python -m src.main
```

The CLI will display the available sample incidents:

```text
Available incidents:
1. INC-001 - HTTP 500 after deployment
2. INC-002 - Database timeout
3. INC-003 - Service without cloud connectivity

Select an incident [1-3]:
```

## Running with Docker

Build the image:

```bash
docker build -t ai-support-crew .
```

Run the container:

```bash
docker run --name ai-support-crew-app --env-file .env -it ai-support-crew
```

The `.env` file is not copied into the Docker image.

Secrets are injected only when the container starts.

## Tests

Run the automated test suite with:

```bash
python -m pytest -q
```

The project includes tests for agents, configuration, models, Flow behavior, incident data services, memory, tools and LLM retry/error handling.

## Security

Sensitive configuration is never committed to the repository.

The project uses:

```text
.env          → local secrets
.env.example  → configuration template
.gitignore    → prevents secrets from being committed
.dockerignore → prevents secrets from entering Docker builds
```

API keys and cloud credentials should never be hardcoded in the application.

## Current Scope

AI Support Crew currently operates against simulated incidents and local observability data.

This allows the agent architecture, routing, memory, retry behavior and structured outputs to be tested without requiring paid infrastructure.

A production-oriented evolution could integrate real systems such as:

- Datadog
- Kibana / Elasticsearch
- CloudWatch
- Jira
- Freshdesk
- PagerDuty
- production APIs and databases

The current architecture separates data access, agent logic and orchestration so these integrations can be introduced without redesigning the complete workflow.

## What This Project Demonstrates

This project focuses on practical concepts involved in building agentic AI applications:

- multi-agent orchestration
- specialized agent responsibilities
- structured LLM outputs
- typed state management
- dynamic workflow routing
- tool usage
- incident memory
- asynchronous operations
- LLM provider abstraction
- resilient retry strategies
- secret management
- automated testing
- containerization

## Author

**Franco Lavirgen**

Systems Analyst & Full Stack Developer focused on AI-powered applications and agentic systems.
