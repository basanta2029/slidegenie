# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Presentation defaults
PRESENTATION_DEFAULTS = {
    "Lab Meeting": {"slides": 10},
    "Conference Talk": {"slides": 20},
    "Thesis Defense": {"slides": 35},
    "Lecture": {"slides": 15}
}

# Template styles
TEMPLATE_STYLES = [
    "Modern Research",
    "Classic Academic", 
    "Minimalist",
    "Data-Focused"
]
