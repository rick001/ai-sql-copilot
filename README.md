# AI SQL Copilot

An AI-powered analytics copilot that generates SQL queries from natural language using LLMs (Ollama/Bedrock) and executes them on ClickHouse or DuckDB. Features conversational query interface, automatic SQL generation with retry mechanisms, validation, and interactive data visualization.

**Note**: This project uses hypothetical/example retail sales data to demonstrate the system. The CVS-branded frontend is part of a proof-of-concept, but the actual data is synthetic and not associated with any real company.

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Frontend   │──────│   Backend    │──────│  ClickHouse │
│  Next.js    │      │   FastAPI    │      │   /DuckDB  │
│  Port 3000  │      │   Port 8000  │      │   Port 8123│
└─────────────┘      └──────┬───────┘      └─────────────┘
                            │
                     ┌──────▼───────┐
                     │    Ollama    │
                     │  Port 11434  │
                     │  (Optional)  │
                     └──────────────┘
```

**Tech Stack:**
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS, Recharts
- **Backend**: Python 3.11, FastAPI, Pydantic
- **LLM**: Ollama (Llama 3.1:8b) or AWS Bedrock (Claude 3.5 Sonnet)
- **Database**: ClickHouse (default) or DuckDB
- **Infrastructure**: Docker Compose

## 📋 Prerequisites

Before you begin, ensure you have:

1. **Docker Desktop** or **Docker Engine** with Docker Compose installed
2. **Node.js 20+** and **pnpm** (for local frontend development)
3. **Python 3.11+** (for local backend development)
4. **Ollama** (if using local LLM):
   ```bash
   # Install Ollama
   brew install ollama  # macOS
   # or visit https://ollama.ai
   
   # Start Ollama service
   ollama serve
   
   # Pull the model
   ollama pull llama3.1:8b
   ```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone and navigate to the project:**
   ```bash
   cd <project-directory>
   ```

2. **Create environment file:**
   ```bash
   cp infra/env.example .env
   ```

3. **Edit `.env` file with your configuration:**
   ```bash
   # For Ollama (recommended for local development)
   USE_OLLAMA=1
   OLLAMA_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1:8b
   
   # Database (ClickHouse recommended)
   DB_DRIVER=clickhouse
   CLICKHOUSE_URL=http://clickhouse:8123
   ```

4. **Start all services:**
   ```bash
   docker compose -f infra/docker-compose.yml up --build
   ```

5. **Seed the database:**
   ```bash
   # In a new terminal
   docker compose -f infra/docker-compose.yml exec backend python -m app.seed
   ```

6. **Access the application:**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **Health Check**: http://localhost:8000/healthz
   - **ClickHouse**: http://localhost:8123 (if using ClickHouse)

   **Note**: The frontend displays CVS branding as part of the POC demonstration, but the underlying data is synthetic and hypothetical. The system can be adapted to work with any SQL database and data schema.

### Option 2: Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export USE_OLLAMA=1
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1:8b
export DB_DRIVER=clickhouse
export CLICKHOUSE_URL=http://localhost:8123

# Run the server
make run
# or
uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Set environment variable (optional)
export NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Run development server
pnpm dev
```

#### Database Setup

**For ClickHouse:**
```bash
# Start ClickHouse with Docker
docker run -d -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server:24.8

# Then run backend as shown above
```

**For DuckDB:**
```bash
# DuckDB runs in-process, no separate service needed
# Just set DB_DRIVER=duckdb in your .env
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# ============================================
# LLM Configuration
# ============================================

# Use Ollama (1) or Bedrock (0)
USE_OLLAMA=1

# Ollama Settings (if USE_OLLAMA=1)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# AWS Bedrock Settings (if USE_OLLAMA=0)
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
BEDROCK_MOCK=0  # Set to 1 to use mock mode (for testing)

# ============================================
# Database Configuration
# ============================================

# Database driver: "clickhouse" or "duckdb"
DB_DRIVER=clickhouse

# ClickHouse settings (if DB_DRIVER=clickhouse)
CLICKHOUSE_URL=http://clickhouse:8123  # Use http://localhost:8123 for local dev

# ============================================
# Service Ports
# ============================================

FRONTEND_PORT=3000
BACKEND_PORT=8000
CLICKHOUSE_HTTP_PORT=8123
```

### Common Configuration Scenarios

#### Scenario 1: Local Development with Ollama + ClickHouse (Recommended)

```bash
USE_OLLAMA=1
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
DB_DRIVER=clickhouse
CLICKHOUSE_URL=http://clickhouse:8123
```

**Requirements:**
- Ollama running locally (`ollama serve`)
- ClickHouse running in Docker (via docker-compose)

#### Scenario 2: Local Development with Ollama + DuckDB (Simplest)

```bash
USE_OLLAMA=1
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
DB_DRIVER=duckdb
```

**Requirements:**
- Ollama running locally (`ollama serve`)
- No additional database setup needed

#### Scenario 3: AWS Bedrock + ClickHouse (Production-like)

```bash
USE_OLLAMA=0
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
BEDROCK_MOCK=0
DB_DRIVER=clickhouse
CLICKHOUSE_URL=http://clickhouse:8123
```

**Requirements:**
- AWS credentials with `bedrock:InvokeModel` permission
- Model access enabled in AWS Bedrock console

## 🗂️ Project Structure

```
project/
├── frontend/                 # Next.js frontend application
│   ├── app/
│   │   ├── page.tsx         # Main chat interface
│   │   ├── layout.tsx       # Root layout
│   │   └── globals.css       # Global styles
│   ├── package.json
│   └── Dockerfile
│
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── main.py          # FastAPI app and routes
│   │   ├── ollama_client.py # Ollama integration
│   │   ├── bedrock_client.py # AWS Bedrock integration
│   │   ├── tool_runner.py   # SQL execution
│   │   ├── sql_translator.py # SQL translation for ClickHouse
│   │   ├── sql_validator.py # SQL security validation
│   │   ├── db/              # Database drivers
│   │   │   ├── repository.py
│   │   │   ├── clickhouse_driver_impl.py
│   │   │   └── duckdb_driver.py
│   │   ├── prompts/
│   │   │   └── system_prompt.txt
│   │   └── seed.py          # Data seeding script
│   ├── tests/               # Unit and E2E tests
│   ├── requirements.txt
│   ├── Makefile
│   └── Dockerfile
│
├── infra/                   # Infrastructure as Code
│   ├── docker-compose.yml   # Local development orchestration
│   └── env.example          # Environment variable template
│
└── README.md                # This file
```

## 📊 Data Model

**Important**: The data in this project is **hypothetical and synthetic**. It is designed as an example use case for demonstrating the AI SQL copilot capabilities. The application uses a single table `retail_sales` with the following schema:

```sql
CREATE TABLE retail_sales (
  date DATE,
  store_id VARCHAR,
  store_name VARCHAR,
  region VARCHAR,
  category VARCHAR,
  sku VARCHAR,
  units INTEGER,
  net_sales DECIMAL(12,2)
);
```

**Sample Data (Hypothetical/Example):**
- ~1,080 rows of synthetic retail sales data
- 12 months of historical data
- 4 regions: North, South, East, West
- 4 categories: Beverages, Snacks, Household, Personal Care
- Multiple stores and SKUs

**Note**: This data is entirely fictional and created for demonstration purposes. It does not represent actual sales data from any company. The CVS branding in the frontend is part of the POC demonstration but does not imply any association with the actual CVS company.

## 🔧 Usage

### Starting the Application

1. **Ensure Ollama is running** (if using Ollama):
   ```bash
   ollama serve
   ```

2. **Start Docker services:**
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```

3. **Seed the database:**
   ```bash
   docker compose -f infra/docker-compose.yml exec backend python -m app.seed
   ```

4. **Open the frontend:**
   - Navigate to http://localhost:3000
   - Start asking questions!

### Example Questions

- "What are the top 3 categories by net sales each month?"
- "Show total net sales by date for the last 6 months"
- "What is the top product (sku) by net sales last quarter?"
- "What are the bottom 5 categories by units in the last 90 days?"
- "Compare net sales across regions"

### Stopping the Application

```bash
# Stop all services
docker compose -f infra/docker-compose.yml down

# Stop and remove volumes (clean slate)
docker compose -f infra/docker-compose.yml down -v
```

## 🧪 Testing

Run backend tests:

```bash
# Unit tests
docker compose -f infra/docker-compose.yml exec backend make test

# Or locally
cd backend
python -m pytest tests/
```

Test coverage includes:
- SQL validator (security checks)
- JSON response schema validation
- End-to-end happy path

## 🐛 Troubleshooting

### Issue: "Ollama error: connection refused"

**Solution:**
- Ensure Ollama is running: `ollama serve`
- Check `OLLAMA_URL` in `.env` matches your Ollama service
- For Docker, use `http://host.docker.internal:11434` instead of `localhost`

### Issue: "Unknown expression or function identifier 'CURRENT_DATE'"

**Solution:**
- The SQL translator should handle this automatically
- If it persists, check that `sql_translator.py` is being called in `tool_runner.py`

### Issue: "Database error" or "Unknown table"

**Solution:**
- Ensure you've seeded the database: `docker compose exec backend python -m app.seed`
- Check `DB_DRIVER` in `.env` matches your database choice
- Verify ClickHouse is running if using ClickHouse: `docker compose ps clickhouse`

### Issue: Frontend shows "undefined" values in charts

**Solution:**
- The code now includes smart key matching
- Check browser console for errors
- Verify backend is returning data correctly: `curl http://localhost:8000/healthz`

### Issue: Charts are cut off

**Solution:**
- Use the "Full Screen" button in the chat interface
- Charts are now larger and more readable in full-screen mode

### Issue: Docker Compose can't find `.env` file

**Solution:**
- Ensure `.env` is in the project root (same level as `infra/`)
- Check file name is exactly `.env` (not `.env.txt`)

## 🔐 Security

- **SQL Validation**: All SQL queries are validated against an allowlist
- **Table Access**: Only `retail_sales` table is accessible
- **Query Restrictions**: Only SELECT statements are allowed
- **No DDL/DML**: CREATE, DROP, INSERT, UPDATE, DELETE are blocked
- **Parameterized Queries**: Prepared statements where possible

## 📝 API Endpoints

### `POST /chat`

Send a natural language question and get a response with SQL and visualization.

**Request:**
```json
{
  "message": "What are the top 3 categories by net sales each month?"
}
```

**Response:**
```json
{
  "answer": "The top 3 categories...",
  "sql": "SELECT date, category, SUM(net_sales)...",
  "viz": {
    "type": "bar",
    "x": "date",
    "y": ["total_net_sales"],
    "groupBy": ["category"]
  },
  "rows": [...],
  "schema": [...]
}
```

### `GET /healthz`

Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

## 🛠️ Development

### Backend Commands

```bash
cd backend

# Run server
make run

# Seed database
make seed

# Run tests
make test
```

### Frontend Commands

```bash
cd frontend

# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build
```

## 📚 Key Features

- ✅ **Natural Language Queries**: Ask questions in plain English
- ✅ **Automatic SQL Generation**: LLM generates and executes SQL
- ✅ **Smart SQL Translation**: Converts standard SQL to ClickHouse syntax
- ✅ **Interactive Charts**: Visualize data with line/bar charts
- ✅ **Modern Chat UI**: Clean, chat-style interface
- ✅ **Full-Screen Charts**: Expand charts for better viewing
- ✅ **Security**: SQL validation prevents malicious queries
- ✅ **Flexible Backend**: Switch between Ollama and Bedrock
- ✅ **Multiple Databases**: Support for ClickHouse and DuckDB

## 🤝 Contributing

This is a POC project. Key areas for improvement:
- Enhanced error handling
- More sophisticated SQL validation
- Additional visualization types
- Performance optimizations
- More comprehensive tests

## 📄 License

Internal POC - AI SQL Generation System
