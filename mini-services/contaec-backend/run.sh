#!/bin/bash
cd "$(dirname "$0")/../../backend"
exec python3 -c "import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')"
