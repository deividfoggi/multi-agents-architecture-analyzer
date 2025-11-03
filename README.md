# Enhanced Document Analysis API with Azure AI Foundry Integration

This project demonstrates an advanced Python-based **RESTful API** that integrates **Azure AI Foundry Agents** using Semantic Kernel for intelligent document analysis and essay evaluation. The application features a hybrid architecture that automatically falls back to traditional processing when Azure AI Foundry agents are unavailable.

## 🚀 Key Features

### Core Functionality
- **RESTful API:** FastAPI-based API with automatic documentation, validation, and OpenAPI specification
- **Azure Blob Storage:** Retrieves prompt templates securely from cloud or local storage (optional)
- **Environment-based Configuration:** Secure configuration management through environment variables
- **Robust Error Handling:** Comprehensive error handling and graceful fallback mechanisms

### 🤖 Azure AI Foundry Integration (New!)
- **Sequential Agent Workflows:** Native Semantic Kernel orchestration of Azure AI Foundry agents
- **Specialized Agents:**
  - **Architecture Detail Extractor:** Identifies architectural patterns, components, and design decisions
  - **Azure Resources Specialist:** Analyzes Azure services, configurations, and provides recommendations
- **Shared Thread Context:** Maintains conversation continuity across agent interactions
- **Automatic Fallback:** Seamlessly falls back to traditional processing when agents are unavailable

### 🔧 Flexible AI Service Architecture
The application uses a sophisticated factory pattern to inject AI services into Semantic Kernel:

- **Multiple Provider Support:** Azure OpenAI, Azure AI Inference, and Azure AI Foundry
- **Agent Factory Pattern:** Creates and manages specialized agents with independent kernels
- **Plugin System:** Each agent can have specialized plugins for different use cases
- **Conversation Continuity:** Supports continuing analysis conversations in the same thread context
- Use different AI services for different use cases

### 📄 PDF Processing Capabilities
The architecture_extractor agent now includes native PDF processing through a custom Semantic Kernel plugin:

- **PDFReaderPlugin:** Native Python function plugin for PDF text extraction using PyMuPDF
- **Multiple Input Formats:** Supports both file uploads and base64-encoded PDF data
- **Comprehensive Metadata:** Extracts page count, file size, and processing information
- **Error Handling:** Robust error handling with detailed feedback for debugging
- **API Integration:** Seamlessly integrated into the `/analyze-pdf` endpoint

The PDF reader plugin uses PyMuPDF (fitz) for reliable text extraction and is designed as a Semantic Kernel plugin with `@kernel_function` decorators for easy integration with AI agents.

See `pdf_reader_plugin.py` and `foundry_agent_factory.py` for details on how the PDF processing is implemented and integrated with the architecture_extractor agent.

## Prerequisites

### Local Development
- Python 3.8+
- [Azurite](https://github.com/Azure/Azurite) (optional, for local Blob Storage emulation if using storage features)
- Install dependencies:
  ```sh
  pip install -r requirements.txt
  ```

### Docker Development
- Docker (for containerized deployment)
- Docker Compose (optional, for multi-service orchestration)

The project includes:
- `Dockerfile` - Single-stage build optimized for Linux x64
- `.dockerignore` - Excludes unnecessary files from the Docker build context
- Environment-based configuration for both local and containerized deployments

## Environment Variables
Set the following environment variables before running the project:

### Required Variables
- `MODEL_DEPLOYMENT_NAME` (AI model deployment name)
- `AI_API_KEY` (AI API key)  
- `AI_ENDPOINT` (AI endpoint)
- `API_VERSION` (AI API version)

### Optional Azure AI Foundry Variables (for enhanced processing)
- `AZURE_AI_PROJECT_ENDPOINT` (Azure AI Foundry project endpoint)
- `ARCHITECTURE_EXTRACTOR_AGENT_ID` (Architecture Detail Extractor agent ID)
- `AZURE_RESOURCES_SPECIALIST_AGENT_ID` (Azure Resources Specialist agent ID)

### Optional Storage Variables (if using blob storage features)
- `AZURE_STORAGE_CONNECTION_STRING` (for local Blob Storage)
- `AZURE_STORAGE_ACCOUNT_URL` (for managed identity/Azure)
- `STORAGE_CONTAINER_NAME` (Blob container name)

### Optional Configuration
- `HOST` (API host, default: 0.0.0.0)
- `PORT` (API port, default: 8080)
- `LOG_LEVEL` (Logging level, default: INFO)

## Usage

### Option 1: API Server

#### 1. Configure Environment
Create a `.env` file based on `.env.template`:
```bash
cp .env.template .env
# Edit .env with your configuration
```

#### 2. Start the API Server
```bash
python api.py
```

The API will be available at `http://localhost:8080` with interactive documentation at `http://localhost:8080/docs`.

#### 3. Test with CLI Tool
Use the built-in CLI testing tool:
```bash
python cli_test.py
```

### Option 2: Local Storage Setup (Optional)
If you want to use blob storage features:
- Start Azurite using the VS Code extension or Docker
- Use Azure Storage Explorer to create a container named "templates"
- Upload prompt template files as needed

Example prompt template (essay.yaml):

```yaml
name: EvaluateEssay
template: |
  <message role="system">
    Você é um avaliador de redações especialista. Sua tarefa é avaliar a qualidade de uma redação com base nos critérios fornecidos.
  </message>
  <message role="user">
    Avalie a seguinte redação com base em cada uma das habilidades fornecidas:
      {{ skills_list }}
    Para cada habilidade, forneça um resultado no formato:
    {
      "habilidade": "<nome_da_habilidade>",
      "comentários": "<resultado_da_avaliação>",
      "nota": "<nota>"
    }
    Esta é a redação a ser avaliada:
      {{ essay }}

    SEMPRE SOMENTE AO FINAL da avaliação, você deve usar os resultados de cada habilidade avaliada na função evaluate_skills, e então adicione o resultado da avaliação ao resultado final exatamente como ele é retornado.
  </message>
template_format: handlebars
description: An essay evaluation prompt.
input_variables:
  - name: skills_list
    description: The list of skills.
    is_required: true
  - name: essay
    description: The essay to evaluate.
    is_required: true
output_variable:
  evaluation: The evaluation result.
execution_settings:
  service1:
    model_id: gpt-4o
    temperature: 0.6
  default:
    temperature: 0.5
```

### Option 3: Docker Deployment

#### 1. Build the Docker Image
```bash
docker build -t enhanced-document-analysis-api:latest .
```

#### 2. Run with Docker
```bash
# Run with environment file
docker run --env-file .env -p 8080:8080 enhanced-document-analysis-api:latest

# Or run with environment variables
docker run -e MODEL_DEPLOYMENT_NAME="gpt-4" \
           -e AI_API_KEY="your-api-key" \
           -e AI_ENDPOINT="https://your-resource.openai.azure.com/" \
           -e API_VERSION="2024-02-01" \
           -p 8080:8080 \
           enhanced-document-analysis-api:latest
```

## API Usage

### Available Endpoints

#### 1. Document Analysis (Text Input)
Analyze text documents using Azure AI Foundry agents (with automatic fallback):

```bash
# General document analysis  
curl -X POST "http://localhost:8080/analyze-document" \
     -H "Content-Type: application/json" \
     -d '{
       "document_text": "This document describes a cloud architecture using Azure services...",
       "analysis_parameters": {
         "focus_areas": ["architecture", "azure_resources"],
         "detail_level": "comprehensive"
       }
     }'
```

#### 2. PDF Document Analysis
Analyze PDF documents with automatic text extraction and AI processing:

```bash
# Upload and analyze PDF file
curl -X POST "http://localhost:8080/analyze-pdf" \
     -F "file=@/path/to/your/document.pdf" \
     -F "analysis_parameters={\"focus_areas\": [\"architecture\", \"azure_resources\"], \"detail_level\": \"comprehensive\"}"
```

#### 3. Essay Evaluation
Evaluate essays based on specific skills criteria:

```bash
curl -X POST "http://localhost:8080/evaluate" \
     -H "Content-Type: application/json" \
     -d '{
       "essay": "Your essay content here",
       "skills_list": ["Writing clarity", "Grammar", "Content analysis"]
     }'
```

#### 4. Health Check
Check API status and configuration:

```bash
curl -X GET "http://localhost:8080/status"
```

#### 3. Interactive API Documentation
Access Swagger UI at: `http://localhost:8080/docs`

### CLI Testing
For development and testing, use the CLI tool:

```bash
python cli_test.py
```

This provides interactive testing for:
- Essay evaluation scenarios
- Document analysis workflows  
- Configuration validation
- Error handling verification

## Project Structure
- `main.py` — Entry point; runs the FastAPI server
- `api.py` — FastAPI endpoints and request/response models including PDF upload support
- `prompt_processor.py` — Main processor integrating Azure AI Foundry agents with fallback
- `foundry_agent_factory.py` — Factory for retrieving existing Azure AI Foundry agents
- `sequential_workflow_manager.py` — Manages sequential agent workflows in Semantic Kernel
- `kernel.py` — Handles AI provider injection and Semantic Kernel configuration via KernelFactory
- `pdf_reader_plugin.py` — Semantic Kernel plugin for PDF text extraction using PyMuPDF
- `blob_client.py` — Handles Blob Storage access for prompt templates
- `test_pdf_cli.py` — CLI testing tool for PDF analysis functionality
- `post_evaluation.py` — Plugin for essay evaluation, scoring, and approval/rejection logic
- `cli_test.py` — CLI testing tool for development and validation
- `tests/` — Unit tests for all modules
- `essay.yaml` — Sample prompt template (in Portuguese) with evaluation logic

## Configuration Options

The application supports multiple AI provider configurations:

1. **AZURE_AI_FOUNDRY**: Azure AI Foundry agents with Semantic Kernel fallback
2. **AZURE_OPENAI**: Direct Azure OpenAI service integration  
3. **AZURE_AI_INFERENCE**: Azure AI Inference endpoint integration

## Error Handling & Features

- **Automatic Fallback**: From Azure AI Foundry to traditional processing
- **Sequential Workflows**: Native Semantic Kernel orchestration
- **Agent Factory Pattern**: Separation of concerns for agent management
- **Comprehensive Logging**: For debugging and monitoring
- **Interactive Documentation**: Swagger UI available at `/docs`
- **Health Checks**: Status endpoint for monitoring
- **CLI Testing**: Development and validation tool

---

For more details, see the source code and comments in each file.
