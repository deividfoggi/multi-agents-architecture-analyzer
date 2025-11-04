# Multi-Agent Architecture Analyzer

A production-ready Python application that integrates **Azure AI Foundry Agents** using Semantic Kernel for intelligent document analysis and architecture evaluation. Built with modern Python best practices, featuring a modular package structure, comprehensive error handling, and flexible deployment options.

## 🚀 Key Features

### Core Functionality
- **RESTful API:** FastAPI-based API with automatic documentation, validation, and OpenAPI specification
- **Modular Architecture:** Well-organized package structure following Python best practices
- **Azure AI Foundry Integration:** Native Semantic Kernel orchestration with specialized agents
- **PDF Processing:** Advanced PDF text extraction and analysis capabilities
- **Robust Error Handling:** Comprehensive error handling with graceful fallback mechanisms
- **Environment-based Configuration:** Secure configuration management through environment variables

### 🤖 Multi-Agent System
- **Sequential Agent Workflows:** Coordinated multi-agent processing with shared context
- **Specialized Agents:**
  - **Architecture Detail Extractor:** Identifies architectural patterns, components, and design decisions
  - **Azure Resources Specialist:** Analyzes Azure services, configurations, and provides recommendations
- **Conversation Continuity:** Maintains context across agent interactions
- **Automatic Fallback:** Seamlessly handles agent unavailability

### 🏗️ Modern Architecture
- **SOLID Principles:** Clean separation of concerns with delegated responsibilities
- **Factory Pattern:** Dynamic agent creation and management
- **Plugin System:** Extensible architecture with custom Semantic Kernel plugins
- **Package Structure:** Installable Python package with proper namespace organization
- **Type Safety:** Type hints throughout the codebase

### 📄 PDF Processing Capabilities
- **Native PDF Plugin:** Custom Semantic Kernel plugin for PDF text extraction using PyMuPDF
- **Multiple Input Formats:** Supports file uploads and base64-encoded PDF data
- **Comprehensive Metadata:** Extracts page count, file size, and processing information
- **Seamless Integration:** Integrated with AI agents for intelligent document analysis

## 📁 Project Structure

```
demo/
├── src/                                    # Source code package
│   └── analyzer/                          # Main application package
│       ├── api.py                         # FastAPI application & endpoints
│       ├── agents/                        # Agent management
│       │   ├── agent_initialization_manager.py
│       │   └── foundry_agent_factory.py
│       ├── workflows/                     # Workflow execution
│       │   ├── sequential_workflow_manager.py
│       │   └── payload_processor.py
│       ├── processors/                    # Data processing
│       │   ├── prompt_processor.py
│       │   └── result_formatter.py
│       ├── extractors/                    # Data extraction
│       │   └── insights_extractor.py
│       └── plugins/                       # Plugin system
│           ├── microsoft_learn_mcp_plugin.py
│           └── pdf_reader_plugin.py
├── kubernetes/                            # Kubernetes deployment configs
├── main.py                               # Application entry point
├── requirements.txt                      # Python dependencies
├── pyproject.toml                        # Package configuration
├── Dockerfile                            # Container definition
├── setup.sh                              # Automated setup script
└── README.md                             # This file
```

For detailed project structure information, see [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md).

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Docker (optional, for containerized deployment)

### Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./setup.sh

# Activate the virtual environment
source .venv/bin/activate

# Configure your environment
cp .env.template .env
# Edit .env with your configuration

# Run the application
python main.py
```

### Option 2: Manual Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or .venv\Scripts\activate on Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install package in editable mode
pip install -e .

# Configure environment
cp .env.template .env
# Edit .env with your configuration

# Run the application
python main.py
```

### Option 3: Docker Deployment

```bash
# Build the Docker image
docker build -t analyzer:latest .

# Run with environment file
docker run --env-file .env -p 8080:8080 analyzer:latest

# Or run with explicit environment variables
docker run -e MODEL_DEPLOYMENT_NAME="gpt-4" \
           -e AI_API_KEY="your-api-key" \
           -e AI_ENDPOINT="https://your-resource.openai.azure.com/" \
           -e API_VERSION="2024-02-01" \
           -p 8080:8080 \
           analyzer:latest
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `.env.template`:

```bash
cp .env.template .env
```

#### Required Variables
- `MODEL_DEPLOYMENT_NAME` - AI model deployment name
- `AI_API_KEY` - Azure AI API key
- `AI_ENDPOINT` - Azure AI endpoint URL
- `API_VERSION` - Azure AI API version

#### Azure AI Foundry (Optional - for enhanced agent processing)
- `AZURE_AI_PROJECT_ENDPOINT` - Azure AI Foundry project endpoint
- `ARCHITECTURE_EXTRACTOR_AGENT_ID` - Architecture analysis agent ID
- `AZURE_RESOURCES_SPECIALIST_AGENT_ID` - Azure resources specialist agent ID

#### Application Configuration (Optional)
- `HOST` - API host address (default: 0.0.0.0)
- `PORT` - API port (default: 8080)
- `LOG_LEVEL` - Logging level (default: INFO)
- `RELOAD` - Enable auto-reload for development (default: false)

### AI Provider Configuration

The application supports multiple AI provider configurations:

1. **Azure AI Foundry**: Multi-agent workflows with Semantic Kernel
2. **Azure OpenAI**: Direct Azure OpenAI service integration
3. **Azure AI Inference**: Azure AI Inference endpoint integration

The system automatically detects available providers and falls back gracefully when agents are unavailable.

## 📚 API Reference

### Available Endpoints

#### 1. Health Check
Check API status and configuration:

```bash
curl http://localhost:8080/health
```

#### 2. Document Analysis (Text Input)
Analyze text documents using AI agents:

```bash
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

#### 3. PDF Document Analysis
Upload and analyze PDF documents:

```bash
curl -X POST "http://localhost:8080/analyze-pdf" \
     -F "file=@/path/to/document.pdf" \
     -F "analysis_parameters={\"focus_areas\": [\"architecture\"], \"detail_level\": \"comprehensive\"}"
```

#### 4. Interactive API Documentation
Access comprehensive API documentation at:
- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`

## 🏗️ Architecture

### Package Organization

The application follows a modular architecture with clear separation of concerns:

- **`analyzer/`** - Main application package
  - **`api.py`** - FastAPI application with all REST endpoints
  - **`agents/`** - Agent initialization and factory pattern implementation
  - **`workflows/`** - Sequential workflow management and orchestration
  - **`processors/`** - Data processing, prompt handling, and result formatting
  - **`extractors/`** - Insight extraction and data analysis utilities
  - **`plugins/`** - Custom Semantic Kernel plugins for extended functionality

### Design Patterns

- **Factory Pattern**: Dynamic agent creation and configuration
- **Facade Pattern**: Simplified interface for complex subsystems
- **Strategy Pattern**: Pluggable AI provider implementations
- **Plugin Architecture**: Extensible functionality through Semantic Kernel plugins

### Key Components

#### Agent Management
- **FoundryAgentFactory**: Creates and configures Azure AI Foundry agents
- **AgentInitializationManager**: Handles agent lifecycle and initialization
- Supports multiple specialized agents with independent kernels

#### Workflow Processing
- **SequentialWorkflowManager**: Orchestrates multi-agent workflows
- **PayloadProcessor**: Prepares and validates workflow inputs
- Maintains conversation context across agent interactions

#### Data Processing
- **PromptProcessor**: Main facade for AI processing
- **ResultFormatter**: Formats and structures agent responses
- **InsightsExtractor**: Extracts structured data from analysis results

#### Plugin System
- **PDFReaderPlugin**: PDF text extraction using PyMuPDF
- **MicrosoftLearnMcpPlugin**: Integration with Microsoft documentation
- Extensible architecture for custom plugins

## 🧪 Testing

### Manual Testing

```bash
# Test health endpoint
curl http://localhost:8080/health

# Test PDF analysis
curl -X POST "http://localhost:8080/analyze-pdf" \
     -F "file=@test_document.pdf"

# View API documentation
open http://localhost:8080/docs
```

### Running Tests (if available)

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
pytest

# Run with coverage
pytest --cov=src/analyzer --cov-report=html
```

## 🚢 Deployment

### Docker

The application is containerized and ready for production deployment:

```bash
# Build optimized image
docker build -t analyzer:latest .

# Run in production mode
docker run -d \
  --name analyzer \
  --env-file .env \
  -p 8080:8080 \
  --restart unless-stopped \
  analyzer:latest
```

### Kubernetes

Kubernetes deployment configurations are available in the `kubernetes/` directory:

```bash
# Deploy to Kubernetes
kubectl apply -f kubernetes/deployment.yaml

# Check deployment status
kubectl get pods -l app=analyzer

# View logs
kubectl logs -f deployment/analyzer
```

For detailed Kubernetes setup, see [kubernetes/README.md](kubernetes/README.md).

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide with all setup options
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Detailed development guidelines
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Project reorganization details
- **API Docs** - Interactive documentation at `/docs` when running

## 🤝 Contributing

This project follows Python best practices:

1. **Code Style**: Follow PEP 8 guidelines
2. **Type Hints**: Use type annotations throughout
3. **Documentation**: Add docstrings to all public functions/classes
4. **Testing**: Write tests for new features
5. **Git**: Use meaningful commit messages

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes and test
source .venv/bin/activate
pytest

# Format code (if using black)
black src/

# Commit and push
git add .
git commit -m "feat: add your feature"
git push origin feature/your-feature
```

## 📝 License

[Add your license information here]

## 🆘 Troubleshooting

### Import Errors
If you encounter import errors:
```bash
# Ensure package is installed
pip install -e .

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Reload VS Code Python extension
```

### Agent Connection Issues
If agents fail to connect:
- Verify Azure AI Foundry credentials in `.env`
- Check agent IDs are correct
- Ensure network connectivity to Azure endpoints
- Review logs for detailed error messages

### Docker Issues
```bash
# Clean rebuild
docker build --no-cache -t analyzer:latest .

# Check logs
docker logs analyzer

# Access container shell
docker exec -it analyzer bash
```

For more help, see [QUICKSTART.md](QUICKSTART.md) or check the logs.

---

**Built with ❤️ using Azure AI Foundry, Semantic Kernel, and FastAPI**
