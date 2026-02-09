# Medusa Store Chatbot Backend

An AI-powered conversational chatbot for Medusa e-commerce stores with RAG (Retrieval-Augmented Generation) capabilities, conversation memory, and cart management.

## 🏗️ Architecture

This backend integrates with [Medusa JS](https://medusajs.com/) e-commerce platform and uses:

- **FastAPI** - Modern Python web framework
- **LangChain/LangGraph** - AI agent orchestration
- **OpenAI GPT-4** - Language model
- **Qdrant** - Vector database for RAG
- **Meilisearch** - Product search engine
- **Redis** - Session & conversation memory

## 📋 Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Medusa JS backend running
- OpenAI API key

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd bot-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
- `OPENAI_API_KEY` - Your OpenAI API key
- `MEILISEARCH_API_KEY` - Meilisearch master key (if using authentication)

### 3. Start External Services

Start Qdrant, Meilisearch, and Redis using Docker Compose:

```bash
docker-compose up -d
```

Verify services are running:
```bash
docker-compose ps
```

### 4. Index Products in Meilisearch

**Important:** Follow the [Medusa Meilisearch Integration Guide](https://docs.medusajs.com/resources/integrations/guides/meilisearch) to set up product indexing.

This integration automatically indexes all your Medusa products into Meilisearch, enabling fast product search in the chatbot.

Key steps:
1. Install Meilisearch plugin in your Medusa backend
2. Configure Meilisearch host and API key
3. Products will be automatically indexed on creation/update

### 5. Start the Application

```bash
uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 External Services

### Qdrant (Vector Database)
- **Purpose**: Stores product embeddings for RAG-based search
- **Port**: 6333 (REST API), 6334 (gRPC)
- **Dashboard**: http://localhost:6333/dashboard

### Meilisearch (Search Engine)
- **Purpose**: Fast product search and filtering
- **Port**: 7700
- **Documentation**: https://docs.medusajs.com/resources/integrations/guides/meilisearch
- **Dashboard**: http://localhost:7700

### Redis (Cache & Session Store)
- **Purpose**: Conversation memory and session management
- **Port**: 6379

## 🛠️ Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
flake8 .
```

### Stop Services
```bash
docker-compose down
```

### Reset All Data (⚠️ Warning: Deletes all data)
```bash
docker-compose down -v
```

## 📁 Project Structure

```
bot-backend/
├── app.py                 # Main FastAPI application
├── tools/                 # LangChain tools
│   ├── orders.py         # Order management tools
│   ├── search.py         # Product search tools
│   └── cart.py           # Cart management tools
├── docker-compose.yml    # External services configuration
├── .env.example          # Environment variables template
└── requirements.txt      # Python dependencies
```

## 🔗 Integration with Medusa

This chatbot integrates with your Medusa JS backend via REST APIs. Ensure your Medusa backend is running and accessible.

For Meilisearch product indexing, follow the official guide:
**https://docs.medusajs.com/resources/integrations/guides/meilisearch**

## 📝 License

MIT
