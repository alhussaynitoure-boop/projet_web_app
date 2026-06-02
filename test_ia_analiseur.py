"""
test_gemini.py — Script de test indépendant pour valider l'intégration IA
Lancer avec : python test_gemini.py
"""

from IA_Analise import analyser_image

# ── Données fictives pour simuler une annonce ────────────────────────────────
# CHANGEMENT : on n'a plus besoin d'une image, on simule les champs textuels
# d'une vraie annonce comme elle apparaîtrait dans la base de données.

TYPE_BIEN   = "APPARTEMENT"
PRIX        = 1230000000.0
TITRE       = "Bel appartement F3 ensoleillé à Alger Centre"
DESCRIPTION = "Appartement de 85 m² au 3ème étage, bien entretenu, double vitrage, cuisine équipée, proche de toutes commodités."
SURFACE     = 85.0
ADRESSE     = "Rue Didouche Mourad, Alger Centre, Alger"

# ── Appel direct à la fonction ───────────────────────────────────────────────
print("=" * 50)
print("Test de l'analyse IA en cours...")
print(f"Type déclaré : {TYPE_BIEN}")
print(f"Prix : {PRIX:,.0f} DA")
print(f"Titre : {TITRE}")
print(f"Surface : {SURFACE} m²")
print(f"Adresse : {ADRESSE}")
print("=" * 50)

# CHANGEMENT : on passe maintenant tous les paramètres textuels
resultat = analyser_image(
    chemin_image=None,
    type_bien_declare=TYPE_BIEN,
    prix=PRIX,
    titre=TITRE,
    description=DESCRIPTION,
    surface=SURFACE,
    adresse=ADRESSE
)

print("\nRésultat reçu :")
print("=" * 50)

if resultat['succes']:
    print(resultat['analyse_brute'])
else:
    print(f"ERREUR : {resultat['erreur']}")

print("=" * 50)