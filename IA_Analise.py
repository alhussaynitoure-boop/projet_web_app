"""
gemini_vision.py — Module d'analyse d'annonces via OpenRouter
(analyse textuelle : titre, description, prix, type, surface, adresse)
"""

import requests
from config import OPENROUTER_API_KEY


def analyser_image(chemin_image, type_bien_declare, prix,
                   titre="", description="", surface=None, adresse=""):
    """
    Analyse une annonce immobilière par IA.
    
    CHANGEMENT PAR RAPPORT À LA VERSION GEMINI :
    - Avant : on analysait une image avec Gemini Vision
    - Maintenant : on analyse le texte de l'annonce (titre, description,
      prix, type, surface, adresse) car les modèles vision gratuits
      ne sont plus disponibles sur OpenRouter.
    - Le nom de la fonction reste 'analyser_image' pour ne pas avoir
      à modifier admin.py.
    """

    prompt = f"""
    Tu es un expert immobilier assistant un administrateur de plateforme algérienne.
    Analyse cette annonce et réponds en français de façon structurée.

    Informations de l'annonce :
    - Titre : {titre if titre else 'Non renseigné'}
    - Type de bien déclaré : {type_bien_declare}
    - Prix demandé : {prix:,.0f} DA
    - Surface : {str(surface) + ' m²' if surface else 'Non renseignée'}
    - Adresse : {adresse if adresse else 'Non renseignée'}
    - Description : {description if description else 'Non renseignée'}

    Réponds UNIQUEMENT avec ce format exact :
    TYPE DÉTECTÉ: [cohérent avec le titre/description ou non]
    COHÉRENCE TYPE: [OUI ou NON] - [explication courte]
    ÉTAT DU BIEN: [Excellent / Bon / Moyen / Mauvais] - [basé sur la description]
    COHÉRENCE PRIX: [OUI ou NON] - [est-ce que le prix semble cohérent pour ce type de bien en Algérie ?]
    AVIS GLOBAL: [2-3 phrases résumant ton analyse pour l'admin]
    """

    try:
        reponse = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-oss-20b:free",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        )

        data = reponse.json()
        
        print("DEBUG:", data)  # ← ajoute ça
        texte_reponse = data["choices"][0]["message"]["content"]

        return {
            "succes": True,
            "analyse_brute": texte_reponse,
            "erreur": None
        }

    except FileNotFoundError:
        return {
            "succes": False,
            "analyse_brute": None,
            "erreur": "Image introuvable sur le serveur."
        }

    except Exception as e:
        return {
            "succes": False,
            "analyse_brute": None,
            "erreur": f"Erreur lors de l'analyse : {str(e)}"
        }