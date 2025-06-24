# DQX - Database Query Explorer

A FastAPI application for exploring and querying databases with a web interface.

## Features

- Browse database tables
- Execute SQL queries
- Save and manage SQL scripts
- Schedule SQL scripts to run at specific intervals
- Web interface for interacting with databases
- Chat logging functionality to record user-assistant interactions

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python -m app.main`

## Chat Logging

The application includes a comprehensive chat logging system that allows you to record and analyze conversations between users and assistants.

### Logging Methods

1. **Web UI**: Access the user-friendly interface at `/chat_logger`
2. **REST API**: Use the endpoint at `/api/log_chat` for programmatic logging
3. **Command-line Tool**: Run `python utils/log_chat_cli.py --user "User message" --assistant "Assistant response"`
4. **Python API**: Import directly in your code with `from utils.logger import log_chat`

### Advanced Features

- **Custom Timestamps**: Backdate logs when needed
- **Log Retrieval**: Fetch recent logs or filter by date
- **Log Management**: Functions for clearing logs and getting log file paths

### Examples

```python
# Basic logging
from utils.logger import log_chat
log_chat("How do I use this?", "It's easy! Just follow the documentation.")

# Read recent logs
from utils.logger import read_chat_logs
recent_logs = read_chat_logs(num_entries=5)

# Filter logs by date
from datetime import datetime
from utils.logger import read_chat_logs
yesterday = datetime(2025, 6, 23)
filtered_logs = read_chat_logs(from_date=yesterday)
```

For more examples, see the `utils/logger_examples.py` file.

Chat logs are stored in the project root directory in the `chat_log.txt` file.

## Technologies Used

- FastAPI
- psycopg2
- uvicorn
- HTML/CSS/JavaScript
