import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

print("🔍 Modèles disponibles avec ta clé API :\n")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"  ✅ {m.name}")

print("\nUtilise l'un de ces noms dans gemini_vision.py")