# Intelligent Audit Tool

An intelligent financial audit tool based on Mistral-7B 4-bit model, featuring rule engine, statistical anomaly detection, and LLM-powered deep analysis.

## Features

### 1. Data Preprocessing
- Date merging and cleaning
- Account hierarchy splitting
- Auxiliary field parsing
- Voucher balance calculation
- Anomaly pre-marking

### 2. Rule Engine (17 Rules)
- **Voucher-level Rules**: Balance check, sequence check, one-to-many anomaly
- **Account Compliance Rules**: Summary-account matching, project account validation, tax logic, bank account validation
- **Amount Reasonableness Rules**: Large transactions, integer amounts, frequent small amounts, split transactions
- **Auxiliary Field Rules**: Missing fields, contract format validation
- **Duplicate Transaction Rules**: Complete duplicates, near-duplicates
- **Time Anomaly Rules**: Holiday transactions, month-end rush, year-end adjustments

### 3. Statistical Anomaly Detection
- Benford's Law analysis
- Monthly trend analysis
- Isolation Forest detection
- Transaction graph analysis

### 4. LLM Integration
- Summary classification
- Voucher analysis
- Question answering
- Audit memo generation

## Architecture

```
[Frontend: React + Ant Design]
          |
          v
[Backend: FastAPI] --- [Celery Worker] --- [Data Processing: Pandas/NumPy/Scikit-learn]
          |
          +--- [Ollama Service] (Mistral-7B 4-bit)
          |
          +--- [Database: DuckDB]
```

## Installation

### Prerequisites
- Python 3.10+
- Node.js 16+
- Redis (for Celery)
- Ollama (for LLM features)

### Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start Redis (required for Celery)
redis-server

# Start Celery worker
celery -A tasks worker --loglevel=info

# Start FastAPI server
python main.py
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

### LLM Setup

```bash
# Install Ollama
# See: https://ollama.ai/

# Pull Mistral model
ollama pull mistral

# Start Ollama service
ollama serve
```

## Usage

1. Open browser and navigate to `http://localhost:3000`
2. Upload your financial data file (Excel or CSV)
3. Configure audit rules in the "Rules Configuration" page
4. View audit results in the "Results" page
5. Use the "AI Assistant" for questions about audit procedures

## Data Format

### Required Fields
- Year (年)
- Month (月)
- Day (日)
- Voucher Number (凭证号)
- Summary (摘要)
- Account Code (科目编码)
- Account Name (科目名称)
- Debit Amount (借方本币)
- Credit Amount (贷方本币)

### Optional Fields
- Ledger Name (核算账簿名称)
- Entry Number (分录号)
- Auxiliary Fields (辅助项) - Format: 【Key：Value】
- Currency (币种)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload audit data file |
| `/api/task/{task_id}` | GET | Get task status |
| `/api/llm/analyze` | POST | LLM analysis |
| `/api/llm/health` | GET | Check LLM service health |
| `/api/rules` | POST | Configure rules |
| `/health` | GET | Health check |

## Project Structure

```
audata/
├── main.py                 # FastAPI main application
├── tasks.py                # Celery tasks
├── rules_engine.py         # Rule engine implementation
├── statistical_detection.py # Statistical anomaly detection
├── llm_service.py          # LLM service integration
├── requirements.txt        # Python dependencies
├── start.bat              # Windows startup script
├── frontend/              # React frontend
│   ├── src/
│   │   ├── App.js         # Main application component
│   │   ├── index.js       # Entry point
│   │   └── index.css      # Styles
│   ├── package.json       # Node dependencies
│   └── index.html         # HTML template
└── tests/                 # Test files
    ├── test_preprocess.py
    ├── test_rules.py
    ├── test_statistical.py
    └── test_llm.py
```

## Testing

```bash
# Test data preprocessing
python test_preprocess.py

# Test rule engine
python test_rules.py

# Test statistical detection
python test_statistical.py

# Test LLM service
python test_llm.py
```

## License

MIT License

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting a pull request.
