"""
app.py — Point d'entrée principal de l'application Flask
=========================================================
Ce fichier configure l'application, gère les connexions à la base
de données, et définit les routes de base (les URLs) du projet.

Pour l'instant, ce fichier contient le SQUELETTE de l'application.
Les routes font de simples "render_template" pour que tes partenaires
P2 et P3 puissent voir et tester leurs fichiers HTML.
"""

from flask import Flask, render_template, g, request, redirect, url_for, flash
import sqlite3
import os

# On importe le chemin de la base de données depuis notre config
from config import DATABASE, SECRET_KEY, UPLOAD_FOLDER

# ── Initialisation de l'application Flask ──────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# On s'assure que le dossier d'upload existe sur le serveur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── Gestion de la Connexion Base de Données (SQLite) ──────────────────────────
# Dans Flask, on utilise l'objet spécial "g" (global context) pour stocker
# la connexion à la base de données pendant la durée d'une requête HTTP.
# Cela évite d'ouvrir/fermer la base de données à chaque fonction.

def get_db():
    """
    Ouvre une connexion à la base de données SQLite si elle n'existe pas encore
    pour la requête HTTP en cours.
    """
    db = getattr(g, '_database', None)
    if db is None:
        # sqlite3.connect(...) établit le lien avec le fichier app.db
        db = g._database = sqlite3.connect(DATABASE)
        
        # On configure la connexion pour retourner des dictionnaires
        # à la place de simples tuples. Exemple : au lieu de récupérer (1, "Ali"),
        # on récupère {"id": 1, "nom": "Ali"}. C'est beaucoup plus pratique !
        db.row_factory = sqlite3.Row
        
        # /!\ RAPPEL : Activer la vérification des clés étrangères à chaque connexion !
        db.execute("PRAGMA foreign_keys = ON;")
        
    return db


@app.teardown_appcontext
def close_connection(exception):
    """
    Ferme automatiquement la connexion à la base de données à la toute fin
    de chaque requête HTTP (qu'il y ait eu une erreur ou pas).
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# ── Routes de base pour la navigation (Squelette pour P2 et P3) ───────────────

@app.route('/')
def index():
    """
    Page d'accueil : Affiche la liste des annonces validées.
    (Tâche principale de P2)
    """
    # Pour l'instant, on envoie une liste vide pour ne pas faire planter le template
    annonces = []
    return render_template('index.html', annonces=annonces)


@app.route('/annonce/<int:annonce_id>')
def detail_annonce(annonce_id):
    """
    Page de détail d'une annonce spécifique.
    (Tâche principale de P2)
    """
    return render_template('annonce.html', annonce_id=annonce_id)


@app.route('/publier', methods=['GET', 'POST'])
def publier():
    """
    Formulaire et logique de publication d'une annonce.
    (Tâche partagée entre P1 pour le traitement et P2 pour le formulaire)
    """
    if request.method == 'POST':
        # Plus tard, on mettra ici ton code de traitement du formulaire
        flash("Annonce reçue (simulation) !", "success")
        return redirect(url_for('index'))
        
    return render_template('publier.html')


# ── Routes d'Authentification (Tâche 3 de P1) ─────────────────────────────────

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    """
    Page d'inscription pour créer un nouveau compte.
    """
    if request.method == 'POST':
        # Plus tard, traitement de l'inscription
        return redirect(url_for('connexion'))
    return render_template('inscription.html')


@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    """
    Page de connexion à l'espace membre.
    """
    if request.method == 'POST':
        # Plus tard, traitement de la connexion
        return redirect(url_for('index'))
    return render_template('connexion.html')


@app.route('/deconnexion')
def deconnexion():
    """
    Déconnexion de l'utilisateur (nettoyage de la session).
    """
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for('index'))


# ── Espace Personnel et Modération (P3 et P1) ─────────────────────────────────

@app.route('/mes-annonces')
def mes_annonces():
    """
    Espace personnel de l'utilisateur connecté contenant ses propres annonces.
    (Tâche de P3)
    """
    return render_template('mes_annonces.html')


@app.route('/admin')
def admin():
    """
    Espace de modération réservé aux administrateurs.
    (Tâche 5 de P1)
    """
    # Plus tard, on ajoutera une vérification de sécurité (session["role"] == "admin")
    return render_template('admin.html')


# ── Gestionnaire d'erreur 404 personnalisé (Tâche de P3) ──────────────────────

@app.errorhandler(404)
def page_not_found(e):
    """
    Affiche un message d'erreur 404 propre si l'URL saisie n'existe pas.
    """
    return render_template('404.html'), 404


# ── Démarrage du serveur de développement ──────────────────────────────────────
if __name__ == '__main__':
    # debug=True permet de recharger le serveur automatiquement à chaque modif de code
    # et d'afficher les erreurs directement dans le navigateur.
    app.run(debug=True, port=5000)
