# Local AI Chat

A minimalist AI chat interface built with Python, featuring image/file support and real-time response streaming.

## Features
UI	Minimalist gray theme with history sidebar
Sessions	Create new chats and switch between sessions
Images	Base64 image support for Vision-capable models
Files	Text file processing and injection
Streaming	Real-time "typing" effect for AI responses
Metadata	Displays model and provider information for every response
Supported Models
```
AUTO | Gemini | GPT-4o | DeepSeek | Claude
```

Includes automatic provider fallback.

## Installation and Setup
* Go to the repository page. 
- Click the green Code button. 
- Select Download ZIP. 
- Extract the archive to any folder on your computer.
```bash
pip install -r requirements.txt
python app.py
```

**Access the interface at: http://127.0.0.1:5000**

## Usage Guide

- Select a model from the header.

- Use the "Photo" or "File" buttons to upload attachments.

- Send a message to initiate streaming.

- History is automatically saved; use "New Chat" to start a fresh session.

## Technical Details

Responsive Design: Mobile-friendly sidebar and layout.

Auto-scroll: Automatic scrolling with active typing indicators.

Library Updates: Run pip install -U g4f to resolve provider issues.

File Limits: Large files are truncated to a 2,000 character limit.

Vision: Best performance achieved using GPT-4o or Gemini models.
