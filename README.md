# Autonomous Quiz Solver API

A stateless FastAPI endpoint that autonomously solves data-related quizzes using headless browser automation, file processing, and LLM reasoning.

## Features

- **Headless Browser Automation**: JavaScript-rendered page extraction using Playwright
- **Multi-format File Processing**: CSV, PDF, JSON, Images (with OCR), Text files
- **LLM Reasoning Chain**: Gemini primary with fallback models
- **Autonomous Chaining**: Follows quiz URLs until completion or timeout
- **Stateless Operation**: No database required
- **3-minute Timeout**: Complete solution within time constraints

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd quiz-solver