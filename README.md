# 📚 Academic Q&A Generator

A Python web app that reads your academic documents and instantly generates study questions & answers using AI.

Upload a PDF, DOCX, or TXT file → get categorized Q&A pairs in seconds, powered by Meta's LLaMA 3.3 70B model running on Groq's ultra-fast inference API.

## Tech Stack
- **Streamlit** — interactive web UI
- **Groq API** — free, high-speed LLM inference
- **LLaMA 3.3 70B** — question & answer generation
- **pypdf + python-docx** — multi-format document parsing

## How it works
1. Upload a document (PDF / DOCX / TXT)
2. Choose difficulty (Easy / Medium / Hard) and number of questions
3. The app extracts the text and sends it to Groq's API
4. LLaMA 3.3 70B generates structured Q&A pairs as JSON
5. Results are displayed by category and available to download

## Why Groq?
Groq's inference API is free to use and significantly faster than most cloud LLM providers, making it ideal for real-time document processing without any cost.

> Built with Python · Streamlit · Groq API · LLaMA 3.3 70B
