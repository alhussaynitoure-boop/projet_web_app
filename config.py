import os
# "os" est un module Python intégré (pas besoin de l'installer).
# Il permet d'interagir avec le système de fichiers :
# naviguer dans les dossiers, construire des chemins, etc.


# ── Dossier racine du projet ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# On lit cette ligne de l'intérieur vers l'extérieur :
#   __file__              → chemin du fichier actuel  ex: /home/al/projet_web/config.py
#   os.path.abspath(...)  → s'assure que c'est un chemin absolu complet
#   os.path.dirname(...)  → remonte d'un niveau pour prendre le DOSSIER parent
# Résultat : BASE_DIR = /home/al/projet_web
#
# Pourquoi ? Pour ne pas écrire le chemin en dur ("C:/Users/al/...").
# Comme ça, le projet fonctionne sur n'importe quelle machine sans rien changer.


# ── Clé secrète Flask ─────────────────────────────────────────────────────────
SECRET_KEY = "remplace_ceci_par_une_vraie_cle_secrete_2024"
# Flask utilise cette clé pour SIGNER les sessions utilisateur.
# Concrètement : quand quelqu'un se connecte, Flask crée un cookie chiffré
# dans son navigateur qui dit "cet utilisateur est connecté".
# La SECRET_KEY sert à signer ce cookie pour que personne ne puisse le falsifier.
#
# ⚠️  Si quelqu'un connaît ta clé, il peut se faire passer pour n'importe quel
#     utilisateur. En production : on met une longue chaîne aléatoire.
#     Pour le développement : n'importe quelle chaîne suffit.


# ── Chemin vers la base de données ───────────────────────────────────────────
DATABASE = os.path.join(BASE_DIR, "app.db")
# os.path.join construit un chemin proprement selon le système
# (slash "/" sur Linux/Mac, antislash "\" sur Windows).
# Résultat : /home/al/projet_web/app.db
#
# SQLite est une base de données qui tient dans UN SEUL FICHIER (.db).
# Pas besoin d'installer MySQL ou PostgreSQL — parfait pour un projet universitaire.


# ── Dossier de sauvegarde des photos uploadées ────────────────────────────────
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
# Résultat : /home/al/projet_web/static/uploads/
#
# On met les photos dans "static/" car Flask sert automatiquement
# les fichiers de ce dossier (images, CSS, JS) sans qu'on ait besoin
# d'écrire une route pour chacun.


# ── Extensions de fichiers autorisées pour les uploads ───────────────────────
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
# C'est un SET Python (ensemble) — comme une liste mais sans doublons.
# On s'en sert pour vérifier qu'un utilisateur envoie bien une image
# et non un fichier dangereux (.exe, .php, etc.).
#
# Exemple d'utilisation plus tard dans le code :
#   "jpg" in ALLOWED_EXTENSIONS  → True  ✅ accepté
#   "pdf" in ALLOWED_EXTENSIONS  → False ❌ refusé