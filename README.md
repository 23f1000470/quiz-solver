---
title: Quiz Solver API
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
app_file: app.py
pinned: false
---

# Quiz Solver API

An autonomous quiz solver that can process various file formats, perform data analysis, and solve complex quiz questions automatically.

## Features

- ✅ JavaScript-rendered webpage scraping
- ✅ Multi-format file processing (CSV, PDF, Excel, JSON, Images)
- ✅ Data analysis and visualization
- ✅ OCR with pytesseract
- ✅ LLM reasoning with Gemini
- ✅ Autonomous URL following

## API Usage

Send POST requests to `/solve` endpoint:

```json
{
  "email": "your-email@example.com",
  "secret": "your-secret",
  "url": "https://quiz-url.example.com"
}