# Multi-Agent Architecture Analyzer with Azure AI Foundry Integration

## 📋 Scenario Summary

This project demonstrates a sophisticated **multi-agent architecture** for intelligent document analysis, specifically designed to analyze software architectures and Azure cloud solutions. The system processes documents (text and PDF) through a coordinated workflow of specialized AI agents, each with distinct responsibilities for comprehensive technical analysis.

The application addresses the challenge of analyzing complex technical documents by breaking down the analysis process into specialized domains:
- **Architecture Pattern Analysis**: Identifies design patterns, components, and architectural decisions
- **Azure Services Assessment**: Analyzes Azure cloud resources, configurations, and provides optimization recommendations

## 🤖 Multi-Agent Approach

This project implements a **sequential multi-agent workflow** using Azure AI Foundry agents orchestrated through Microsoft Semantic Kernel. The multi-agent approach offers several key advantages:

### Agent Specialization
- **Architecture Detail Extractor Agent**: Specialized in identifying architectural patterns, component relationships, and design decisions
- **Azure Resources Specialist Agent**: Focused on Azure services analysis, resource optimization, and cloud architecture recommendations

### Sequential Workflow Benefits
1. **Domain Expertise**: Each agent brings specialized knowledge to its specific analysis domain
2. **Contextual Continuity**: Agents share conversation context through a unified thread
3. **Comprehensive Coverage**: Sequential processing ensures thorough analysis across all domains
4. **Fallback Resilience**: Automatic fallback to traditional processing when agents are unavailable
5. **Scalable Architecture**: Easy to add new specialized agents for additional analysis domains

### Workflow Orchestration
The system uses Semantic Kernel's native orchestration capabilities to manage agent interactions:
- **Shared Thread Context**: Maintains conversation continuity across agent interactions
- **Sequential Processing**: Architecture analysis followed by Azure resources assessment
- **Result Aggregation**: Combines insights from multiple agents into comprehensive analysis reports

## 📁 Project Structure and File Responsibilities

### Core API and Entry Point
- **`main.py`** - Application entry point; configures logging and starts the FastAPI server using Uvicorn
- **`api.py`** - FastAPI application with all REST endpoints, request/response models, and PDF upload handling

### Multi-Agent System Components
- **`foundry_agent_factory.py`** - Factory pattern implementation for creating and managing Azure AI Foundry agents with specialized configurations
- **`sequential_workflow_manager.py`** - Orchestrates multi-agent workflows using Semantic Kernel's native agent coordination
- **`prompt_processor.py`** - Main processing engine that integrates Azure AI Foundry agents with fallback to traditional processing

### AI Integration and Plugins
- **`kernel.py`** - Semantic Kernel configuration and AI service provider injection (Azure OpenAI, Azure AI Foundry)
- **`pdf_reader_plugin.py`** - Semantic Kernel plugin for PDF text extraction using PyMuPDF library
- **`microsoft_learn_mcp_plugin.py`** - Model Context Protocol plugin for Microsoft Learn documentation integration

### Storage and Configuration
- **`blob_client.py`** - Azure Blob Storage client for retrieving prompt templates and configuration files
- **`local_template_client.py`** - Local file system client for template management in development environments

### Infrastructure and Deployment
- **`Dockerfile`** - Container configuration for production deployment with security best practices
- **`kubernetes/`** - Kubernetes deployment manifests and configuration files
  - **`deployment.yaml`** - Kubernetes deployment configuration
  - **`workload-identity.yaml`** - Azure Workload Identity configuration for secure authentication
- **`requirements.txt`** - Python dependencies including Semantic Kernel, Azure AI packages, and FastAPI

### Configuration and Testing
- **`pytest.ini`** - Testing configuration for the project test suite
- **`.env.template`** - Environment variable template for easy configuration setup
- **`modelosparaIA/`** - Directory containing AI model configurations and prompt templates

## 🔧 Prerequisites and Setup Instructions

### Local Development Prerequisites
- **Python 3.12+** (recommended) or Python 3.8+ (minimum)
- **Git** for cloning the repository
- **Azure CLI** (optional, for Azure authentication)
- **[Azurite](https://github.com/Azure/Azurite)** (optional, for local Blob Storage emulation if using storage features)

### Docker Development Prerequisites
- **Docker Desktop** or **Docker Engine** (for containerized deployment)
- **Docker Compose** (optional, for multi-service orchestration)

## 🚀 Local Setup Instructions (Python)

### 1. Clone the Repository
```bash
git clone https://github.com/deividfoggi/multi-agents-architecture-analyzer.git
cd multi-agents-architecture-analyzer
```

### 2. Create Python Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
# Copy the template file
cp .env.template .env

# Edit the .env file with your configuration
# Required variables:
# - MODEL_DEPLOYMENT_NAME=your-model-name
# - AI_API_KEY=your-api-key
# - AI_ENDPOINT=https://your-resource.openai.azure.com/
# - API_VERSION=2024-02-01
# 
# Optional Azure AI Foundry variables:
# - AZURE_AI_PROJECT_ENDPOINT=https://your-project.region.api.azureml.ms
# - ARCHITECTURE_EXTRACTOR_AGENT_ID=your-agent-id
# - AZURE_RESOURCES_SPECIALIST_AGENT_ID=your-specialist-agent-id
```

### 5. Run the Application
```bash
python main.py
```

The API will be available at `http://localhost:8080` with interactive documentation at `http://localhost:8080/docs`.

## 🐳 Docker Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/deividfoggi/multi-agents-architecture-analyzer.git
cd multi-agents-architecture-analyzer
```

### 2. Build the Docker Image
```bash
# Build the Docker image
docker build -t multi-agent-analyzer:latest .
```

### 3. Run with Docker
```bash
# Option 1: Run with environment file
docker run --env-file .env -p 8080:8080 multi-agent-analyzer:latest

# Option 2: Run with individual environment variables
docker run \
  -e MODEL_DEPLOYMENT_NAME="your-model-name" \
  -e AI_API_KEY="your-api-key" \
  -e AI_ENDPOINT="https://your-resource.openai.azure.com/" \
  -e API_VERSION="2024-02-01" \
  -p 8080:8080 \
  multi-agent-analyzer:latest
```

### Docker Image Features
- **Security-focused**: Runs as non-root user (UID/GID 1000)
- **Optimized**: Single-stage build with Python 3.12-slim base image
- **Health checks**: Built-in health monitoring endpoint
- **Clean build**: Excludes cache files and unnecessary artifacts
- **Production-ready**: Configured for Kubernetes deployment

## 📖 Usage Guide

### Starting the Application

#### Local Python Execution
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Start the application
python main.py
```

#### Docker Execution
```bash
# Run the containerized application
docker run --env-file .env -p 8080:8080 multi-agent-analyzer:latest
```

The API will be available at `http://localhost:8080` with interactive documentation at `http://localhost:8080/docs`.

### Local Storage Setup (Optional)
If you want to use blob storage features:
- Start Azurite using the VS Code extension or Docker
- Use Azure Storage Explorer to create a container named "templates"
- Upload prompt template files as needed

### Testing the Application
```bash
# Test the API endpoints using curl commands (see API Usage section)
# Or use the interactive Swagger UI at http://localhost:8080/docs
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

#### 3. Health Check
Check API status and configuration:

```bash
curl -X GET "http://localhost:8080/health"
```

#### 4. Status Information
Get detailed processor status and capabilities:

```bash
curl -X GET "http://localhost:8080/status"
```

#### 5. Interactive API Documentation
Access Swagger UI at: `http://localhost:8080/docs`

## 🧪 Development and Testing

### Running Tests
```bash
# Run the test suite
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Testing Tools
- **Swagger UI** - Interactive API testing at `http://localhost:8080/docs`
- **cURL Commands** - Direct HTTP API testing (see API Usage examples)
- **Pytest** - Run test suite with `pytest`

## 🔧 Key Technical Features

- **Multi-Agent Architecture**: Sequential workflow orchestration using Semantic Kernel
- **Automatic Fallback**: Graceful degradation when Azure AI Foundry agents are unavailable
- **Multiple AI Providers**: Support for Azure OpenAI, Azure AI Foundry, and Azure AI Inference
- **PDF Processing**: Native text extraction using PyMuPDF with Semantic Kernel integration
- **Interactive Documentation**: Swagger UI available at `/docs`
- **Health Monitoring**: Built-in health checks and comprehensive logging
- **Containerized Deployment**: Production-ready Docker configuration with Kubernetes support

---

For more details, see the source code and comments in each file.
