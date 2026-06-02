"""
app.py — Point d'entrée principal de l'application Flask
=========================================================
MODIFICATIONS par rapport à la version précédente :
  1. Import des Blueprints 'annonces' et 'admin'
  2. Enregistrement des Blueprints dans l'application
  3. Mise à jour de la route / pour afficher les annonces PUBLIEE
  4. Mise à jour de la route /mes-annonces pour lister les annonces du vendeur
"""

from flask import Flask, render_template, g, request, redirect, url_for, flash
import sqlite3
import os

from config import DATABASE, SECRET_KEY, UPLOAD_FOLDER

# ── Imports des Blueprints ────────────────────────────────────────────────────
from auth import auth as auth_blueprint, login_required
from annonces import annonces as annonces_blueprint
from admin import admin as admin_blueprint


# ── Initialisation de l'application Flask ──────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# On stocke aussi ALLOWED_EXTENSIONS dans app.config pour que les Blueprints y accèdent
from config import ALLOWED_EXTENSIONS
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── Enregistrement des Blueprints ─────────────────────────────────────────────
app.register_blueprint(auth_blueprint)
app.register_blueprint(annonces_blueprint)
app.register_blueprint(admin_blueprint)


# ── Gestion de la Connexion Base de Données (SQLite) ──────────────────────────

def get_db():
    """
    Ouvre une connexion à la base de données SQLite si elle n'existe pas encore
    pour la requête HTTP en cours.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON;")
    return db


@app.teardown_appcontext
def close_connection(exception):
    """
    Ferme automatiquement la connexion à la base de données à la fin
    de chaque requête HTTP.
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# ── Route : Page d'accueil (/) ────────────────────────────────────────────────
@app.route('/')
def index():
    """
    Page d'accueil : Affiche la liste des annonces validées (PUBLIEE).
    
    FILTRES disponibles via URL :
        ?prix_min=1000000     → Annonces à partir de 1M DA
        ?prix_max=5000000     → Annonces jusqu'à 5M DA
        ?tri=date             → Plus récentes d'abord (défaut)
        ?tri=prix_asc         → Moins chères d'abord
        ?tri=prix_desc        → Plus chères d'abord
    
    EXEMPLES :
        /?prix_min=2000000&prix_max=8000000&tri=prix_asc
        /?tri=prix_desc
        /?prix_min=1000000
    """
    db = get_db()
    
    # ── 1. Récupération des paramètres de filtre ───────────────────────────
    # request.args.get('cle', type=float) :
    #   - Lit le paramètre URL ?cle=valeur
    #   - Convertit automatiquement en float (nombre décimal)
    #   - Retourne None si le paramètre est absent
    
    prix_min = request.args.get('prix_min', type=float)
    # Ex: /?prix_min=1000000 → prix_min = 1000000.0
    # Ex: / (sans paramètre) → prix_min = None
    
    prix_max = request.args.get('prix_max', type=float)
    # Même principe pour le prix maximum
    
    tri = request.args.get('tri', 'date')
    # Valeur par défaut : 'date' si aucun tri spécifié
    # Valeurs acceptées : 'date', 'prix_asc', 'prix_desc'
    
    # ── 2. Validation du paramètre de tri ──────────────────────────────────
    # Sécurité : si l'utilisateur met ?tri=hacker, on force 'date'
    if tri not in ('date', 'prix_asc', 'prix_desc'):
        tri = 'date'
    
    # ── 3. Construction dynamique de la requête SQL ────────────────────────
    # On construit la clause WHERE et les paramètres petit à petit
    
    conditions = ["a.statut = 'PUBLIEE'"]
    # Liste des conditions WHERE. On commence toujours par le statut PUBLIEE
    
    params = []
    # Liste des valeurs à substituer aux '?' (protection injection SQL)
    
    # ── 3a. Filtre prix minimum ────────────────────────────────────────────
    if prix_min is not None:
        # Si l'utilisateur a spécifié un prix minimum
        conditions.append("a.prix >= ?")
        # On ajoute la condition SQL : prix doit être >= ?
        params.append(prix_min)
        # On ajoute la valeur dans la liste des paramètres
    
    # ── 3b. Filtre prix maximum ────────────────────────────────────────────
    if prix_max is not None:
        conditions.append("a.prix <= ?")
        params.append(prix_max)
        # Même principe pour le prix max
    
    # ── 3c. Assemblage de la clause WHERE ──────────────────────────────────
    where_clause = " AND ".join(conditions)
    # "a.statut = 'PUBLIEE'" 
    #   → si prix_min ajouté : "a.statut = 'PUBLIEE' AND a.prix >= ?"
    #   → si les deux : "a.statut = 'PUBLIEE' AND a.prix >= ? AND a.prix <= ?"
    
    # ── 3d. Clause ORDER BY (tri) ─────────────────────────────────────────
    if tri == 'prix_asc':
        order_clause = "a.prix ASC"
        # ASC = Ascending = croissant (moins cher → plus cher)
    elif tri == 'prix_desc':
        order_clause = "a.prix DESC"
        # DESC = Descending = décroissant (plus cher → moins cher)
    else:
        order_clause = "a.datePubli DESC"
        # Par défaut : date décroissante (plus récent d'abord)
    
    # ── 4. Exécution de la requête SQL ─────────────────────────────────────
    # f-string pour injecter where_clause et order_clause (ce sont sûrs,
    # construits par nous, pas par l'utilisateur)
    # Les '?' dans params sont protégés contre l'injection SQL
    
    annonces = db.execute(
        f"""
        SELECT 
            a.id,
            a.titre,
            a.description,
            a.prix,
            a.datePubli,
            b.adresse,
            b.surface,
            b.type as type_bien,
            u.nom as vendeur_nom
        FROM ANNONCE a
        JOIN BIEN_IMMOBILIER b ON a.id_bien = b.id
        JOIN VENDEUR v ON a.id_vendeur = v.id_utilisateur
        JOIN UTILISATEUR u ON v.id_utilisateur = u.id
        WHERE {where_clause}
        ORDER BY {order_clause}
        """,
        tuple(params)
    ).fetchall()
    
    # ── 5. Récupération des photos principales ─────────────────────────────
    # (identique à avant, mais on ne récupère que pour les annonces filtrées)
    photos = {}
    if annonces:
        ids = [a['id'] for a in annonces]
        placeholders = ', '.join('?' * len(ids))
        
        resultats_photos = db.execute(
            f"""
            SELECT id_annonce, url
            FROM MEDIA
            WHERE id_annonce IN ({placeholders})
            AND ordre = 0
            """,
            tuple(ids)
        ).fetchall()
        
        for p in resultats_photos:
            photos[p['id_annonce']] = p['url']
    
    # ── 6. Passage des filtres actuels au template ─────────────────────────
    # Pour que le template puisse :
    #   - Afficher les valeurs actuelles dans les champs de formulaire
    #   - Construire les liens de tri (ex: lien "Trier par prix" garde le filtre prix_min)
    
    return render_template(
        'index.html',
        annonces=annonces,
        photos=photos,
        prix_min=prix_min,      # ← Nouveau : pour afficher la valeur dans le formulaire
        prix_max=prix_max,      # ← Nouveau
        tri=tri                 # ← Nouveau : pour savoir quel tri est actif
    )


# ── Route : Détail d'une annonce ──────────────────────────────────────────────

@app.route('/annonce/<int:annonce_id>')
def detail_annonce(annonce_id):
    """
    Page de détail d'une annonce spécifique.
    Affiche toutes les infos + photos + historique du vendeur.
    """
    db = get_db()
    
    # Récupération de l'annonce avec ses infos liées
    annonce = db.execute(
        """
        SELECT 
            a.*,
            b.adresse, b.surface, b.type as type_bien,
            u.nom as vendeur_nom, u.email as vendeur_email, u.telephone
        FROM ANNONCE a
        JOIN BIEN_IMMOBILIER b ON a.id_bien = b.id
        JOIN VENDEUR v ON a.id_vendeur = v.id_utilisateur
        JOIN UTILISATEUR u ON v.id_utilisateur = u.id
        WHERE a.id = ? AND a.statut = 'PUBLIEE'
        """,
        (annonce_id,)
    ).fetchone()
    
    if annonce is None:
        flash("Annonce introuvable ou non publiée.", "warning")
        return redirect(url_for('index'))
    
    # Photos de l'annonce
    medias = db.execute(
        "SELECT url, ordre FROM MEDIA WHERE id_annonce = ? ORDER BY ordre ASC",
        (annonce_id,)
    ).fetchall()
    
    # Autres annonces du même vendeur (historique)
    historique = db.execute(
        """
        SELECT a.id, a.titre, a.prix, a.statut, a.datePubli
        FROM ANNONCE a
        WHERE a.id_vendeur = ? AND a.id != ? AND a.statut = 'PUBLIEE'
        ORDER BY a.datePubli DESC
        LIMIT 5
        """,
        (annonce['id_vendeur'], annonce_id)
    ).fetchall()
    
    return render_template('annonce.html', 
                           annonce=annonce, 
                           medias=medias, 
                           historique=historique)


# ── Route : Mes annonces (espace personnel) ───────────────────────────────────

@app.route('/mes-annonces')
@login_required
def mes_annonces():
    """
    Espace personnel : liste les annonces de l'utilisateur connecté.
    Accessible uniquement aux vendeurs (les acheteurs n'ont pas d'annonces).
    """
    db = get_db()
    user_id = session.get('user_id')
    
    # Vérification que c'est bien un vendeur
    if session.get('role') != 'VENDEUR':
        flash("Cette page est réservée aux vendeurs.", "warning")
        return redirect(url_for('index'))
    
    # Récupération de toutes les annonces du vendeur (tous statuts)
    annonces = db.execute(
        """
        SELECT 
            a.id,
            a.titre,
            a.prix,
            a.statut,
            a.datePubli,
            b.adresse,
            b.surface
        FROM ANNONCE a
        JOIN BIEN_IMMOBILIER b ON a.id_bien = b.id
        WHERE a.id_vendeur = ?
        ORDER BY 
            CASE a.statut
                WHEN 'EN_ATTENTE' THEN 1
                WHEN 'PUBLIEE' THEN 2
                WHEN 'REJETEE' THEN 3
                WHEN 'ARCHIVEE' THEN 4
                ELSE 5
            END,
            a.datePubli DESC
        """,
        (user_id,)
        # CASE ... END = tri personnalisé : EN_ATTENTE d'abord, puis PUBLIEE, etc.
    ).fetchall()
    
    return render_template('mes_annonces.html', annonces=annonces)


# ── Gestionnaire d'erreur 404 personnalisé ────────────────────────────────────

@app.errorhandler(404)
def page_not_found(e):
    """
    Affiche un message d'erreur 404 propre si l'URL saisie n'existe pas.
    """
    return render_template('404.html'), 404


# ── Démarrage du serveur de développement ──────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)