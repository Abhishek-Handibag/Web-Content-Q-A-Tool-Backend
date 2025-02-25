# Web Content Q&A Tool Backend

A Flask-based backend service that intelligently extracts web content and provides AI-powered question answering using Google's Gemini 1.5 Flash 8B model.

## Features

- Advanced web content scraping:
  - Intelligent main content detection
  - Automatic removal of boilerplate content
  - Clean text processing with special character handling
  - Related link extraction
- AI-powered question answering:
  - Context-aware responses using Gemini 1.5 Flash 8B
  - Structured answers with evidence-based reasoning
  - Source attribution and quote highlighting
  - Automatic markdown-to-HTML formatting
- Robust error handling and logging:
  - Detailed timestamp-based logging
  - Request/response tracking
  - Performance metrics
  - Error tracing
- Production-ready setup:
  - CORS support
  - Environment-based configuration
  - Timeout handling
  - User-Agent spoofing

## Prerequisites

- Python 3.8+
- Google API Key for Gemini AI
- pip package manager

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Abhishek-Handibag/Web-Content-Q-A-Tool-Backend.git
cd Web-Content-Q-A-Tool-Backend
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
# .env file
GOOGLE_API_KEY=your_google_api_key_here
```

