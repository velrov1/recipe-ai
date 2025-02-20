# AI Recipe Generator

A modern web application that generates recipes using AI, complete with ingredients selection, dietary preferences, and PDF download capabilities.

## Features

- 🥘 AI-powered recipe generation
- 🍳 Ingredient selection with emoji support
- 🥗 Dietary preference filters
- 📊 Nutritional information
- 📝 Step-by-step cooking instructions
- 💾 PDF download functionality
- 🎨 Modern, responsive UI

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Groq API key:
```
GROQ_API_KEY=your_api_key_here
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Select ingredients from the dropdown menus
2. Choose any dietary preferences
3. Click "Generate Recipe"
4. View the generated recipe with complete instructions and nutritional information
5. Download the recipe as a PDF file

## Technology Stack

- Backend: Flask (Python)
- Frontend: HTML, JavaScript, Tailwind CSS
- AI: Groq API
- PDF Generation: ReportLab
