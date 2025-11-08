# Multi-Niche Content Idea Scraper

A Python script that uses Google's Gemini AI to generate viral content ideas for three specific niches:
- Make Money Online / Personal Finance
- AI/Tech Tutorials  
- Faceless Theme Pages

## Features

- **Secure API Key Management**: Reads Gemini API key from environment variables
- **Structured JSON Output**: Uses Gemini's structured output capabilities for consistent formatting
- **Multi-Niche Content Generation**: Generates targeted ideas for three different content niches
- **Error Handling**: Comprehensive error handling for API and configuration issues
- **Professional Output**: Clean, formatted JSON output suitable for automation

## Setup

1. **Install Dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Set Environment Variable**
   ```powershell
   $env:GEMINI_API_KEY = "your_gemini_api_key_here"
   ```

   For permanent setup, add it to your system environment variables.

3. **Get Gemini API Key**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Copy the key and set it as the environment variable

## Usage

Run the script directly:

```powershell
python content_idea_scraper.py
```

## Output Format

The script outputs a JSON array with content ideas for each niche:

```json
[
    {
        "niche": "Make Money Online / Personal Finance",
        "title": "5-Minute Portfolio Check That Saves $1000s",
        "caption_hook": "Most beginners lose money because they skip this simple 5-minute check. Here's how to protect your investments...",
        "visual_concept": "Split-screen showing a messy vs organized investment portfolio with clear profit/loss indicators"
    },
    {
        "niche": "AI/Tech Tutorials",
        "title": "Free Gemini Feature That Beats ChatGPT Plus",
        "caption_hook": "Google just dropped this game-changing feature for FREE. Here's how to access it before everyone else finds out...",
        "visual_concept": "Modern tech interface showing Gemini vs ChatGPT comparison with highlighting new features"
    },
    {
        "niche": "Faceless Theme Page",
        "title": "The 2AM Rule That Changed My Productivity",
        "caption_hook": "When you master this simple rule, procrastination becomes impossible. Here's what successful people do differently...",
        "visual_concept": "Minimalist clock showing 2AM with motivational text overlay and warm, focused lighting"
    }
]
```

## Error Handling

The script includes comprehensive error handling for:
- Missing API key environment variable
- API connection issues
- JSON parsing errors
- General execution errors

## Requirements

- Python 3.7+
- google-generativeai library
- Valid Gemini API key

## File Structure

```
Content generation/
├── content_idea_scraper.py    # Main script
├── requirements.txt           # Dependencies
└── README.md                 # This file
```