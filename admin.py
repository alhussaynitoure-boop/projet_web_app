"""
admin.py — Blueprint de modération (espace admin)
==================================================
Ce Blueprint regroupe les routes réservées aux administrateurs :
  - /admin → Liste les annonces en attente de validation
  - /admin/valider/<id> → Passe le statut à 'PUBLIEE'
  - /admin/rejeter/<id> → Passe le statut à 'REJETEE'

SÉCURITÉ :
  - Chaque route vérifie que l'utilisateur est connecté ET qu'il a le rôle 'ADMIN'
  - Un décorateur personnalisé @admin_required est créé pour factoriser cette logique
"""

# ── Imports ────────────────────────────────────────────────────────────────────

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    g
)

from functools import wraps
# Nécessaire pour créer le décorateur @admin_required proprement

from auth import login_required
# On réutilise @login_required comme base, puis on ajoute la vérif admin

from IA_Analise import analyser_image
#importation pour l'utilisation de la fonction analyser_image




# ── Création du Blueprint ──────────────────────────────────────────────────────

admin = Blueprint('admin', __name__)


# ── Fonction utilitaire : accès à la BDD ──────────────────────────────────────

def get_db():
    """
    Récupère la connexion à la base de données.
    Même principe que dans auth.py et annonces.py.
    """
    db = getattr(g, '_database', None)
    if db is None:
        from app import get_db as app_get_db
        db = app_get_db()
    return db


# ── Décorateur @admin_required ─────────────────────────────────────────────────

def admin_required(f):
    """
    Décorateur de sécurité : protège une route contre les accès non-admin.
    
    COMBINAISON avec @login_required :
    On place @login_required AVANT @admin_required pour que :
      1. D'abord, on vérifie que l'utilisateur est connecté
      2. Ensuite, on vérifie qu'il est admin
    
    UTILISATION :
        @admin.route('/admin')
        @login_required
        @admin_required
        def panel():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        
        # Vérification du rôle admin
        if session.get('role') != 'ADMIN':
            # L'utilisateur est connecté mais n'est PAS admin
            flash("Accès refusé. Cette page est réservée aux administrateurs.", "danger")
            return redirect(url_for('index'))
            # On redirige vers l'accueil (pas vers /connexion car il est déjà connecté)
        
        # L'utilisateur est bien admin → on exécute la route normalement
        return f(*args, **kwargs)
    
    return decorated_function


# ── Route : Panel d'administration (/admin) ───────────────────────────────────

@admin.route('/admin')
@login_required
@admin_required
# Ordre des décorateurs (de bas en haut dans le code) :
#   1. @admin_required vérifie le rôle ADMIN
#   2. @login_required vérifie que l'utilisateur est connecté
# Flask les applique de BAS en HAUT, donc d'abord login_required, puis admin_required.
# C'est l'ordre correct : on vérifie d'abord la connexion, puis le rôle.
def panel():
    """
    Affiche le tableau de bord de modération.
    
    LISTE les annonces en statut 'EN_ATTENTE' avec :
      - Titre, prix, description
      - Nom du vendeur
      - Photos associées
      - Date de publication
    
    Permet de valider ou rejeter chaque annonce.
    """
    
    db = get_db()
    
    # ── Récupération des annonces en attente ────────────────────────────────
    # On fait une jointure entre ANNONCE, UTILISATEUR (via VENDEUR) et BIEN_IMMOBILIER
    # pour avoir toutes les infos nécessaires en UNE requête.
    
    annonces_en_attente = db.execute(
        """
        SELECT 
            a.id,
            a.titre,
            a.description,
            a.prix,
            a.statut,
            a.datePubli,
            u.nom as vendeur_nom,
            u.email as vendeur_email,
            b.adresse,
            b.surface,
            b.type as type_bien
        FROM ANNONCE a
        JOIN VENDEUR v ON a.id_vendeur = v.id_utilisateur
        JOIN UTILISATEUR u ON v.id_utilisateur = u.id
        JOIN BIEN_IMMOBILIER b ON a.id_bien = b.id
        WHERE a.statut = 'EN_ATTENTE'
        ORDER BY a.datePubli ASC
        """
        # JOIN VENDEUR v ON a.id_vendeur = v.id_utilisateur
        #   → On relie l'annonce au vendeur via la clé étrangère
        # JOIN UTILISATEUR u ON v.id_utilisateur = u.id
        #   → On relie le vendeur à l'utilisateur pour avoir son nom
        # JOIN BIEN_IMMOBILIER b ON a.id_bien = b.id
        #   → On relie l'annonce au bien pour avoir l'adresse, surface, type
        # WHERE a.statut = 'EN_ATTENTE'
        #   → On ne veut QUE les annonces en attente de validation
        # ORDER BY a.datePubli ASC
        #   → Du plus ancien au plus récent (les plus vieilles d'abord)
    ).fetchall()
    
    # ── Récupération des photos pour chaque annonce ─────────────────────────
    # On ne peut pas faire de sous-requête facilement avec SQLite + fetchall,
    # donc on récupère toutes les photos des annonces en attente en une requête.
    
    if annonces_en_attente:
        # On extrait tous les IDs des annonces en attente
        ids_annonces = [a['id'] for a in annonces_en_attente]
        
        # On construit une chaîne de placeholders (?, ?, ?) pour la clause IN
        placeholders = ', '.join('?' * len(ids_annonces))
        
        photos = db.execute(
            f"""
            SELECT id_annonce, url, ordre
            FROM MEDIA
            WHERE id_annonce IN ({placeholders})
            ORDER BY ordre ASC
            """,
            tuple(ids_annonces)
            # La requête devient : WHERE id_annonce IN (1, 5, 12, ...)
        ).fetchall()
        
        # On organise les photos par annonce pour faciliter l'affichage dans le template
        photos_par_annonce = {}
        for photo in photos:
            id_ann = photo['id_annonce']
            if id_ann not in photos_par_annonce:
                photos_par_annonce[id_ann] = []
            photos_par_annonce[id_ann].append(photo['url'])
        
    else:
        photos_par_annonce = {}
    
    # ── Affichage du template ───────────────────────────────────────────────
    return render_template(
        'admin.html',
        annonces=annonces_en_attente,
        photos=photos_par_annonce,
        total=len(annonces_en_attente)
        # 'total' permet d'afficher "X annonces en attente" dans le template
    )


# ── Route : Valider une annonce (/admin/valider/<id>) ─────────────────────────

@admin.route('/admin/valider/<int:annonce_id>', methods=['POST'])
@login_required
@admin_required
def valider(annonce_id):
    """
    Passe le statut d'une annonce de 'EN_ATTENTE' à 'PUBLIEE'.
    
    PARAMÈTRE URL : annonce_id → ID de l'annonce à valider
    
    MÉTHODE POST uniquement : évite les validations accidentelles par simple
    clic sur un lien ou un rafraîchissement de page.
    
    TRACE : On enregistre aussi la décision dans SIGNAL_DECISION pour l'historique.
    """
    
    db = get_db()
    id_admin = session.get('user_id')
    
    # ── 1. Vérification que l'annonce existe et est bien en attente ─────────
    annonce = db.execute(
        "SELECT id, statut FROM ANNONCE WHERE id = ?",
        (annonce_id,)
    ).fetchone()
    
    if annonce is None:
        flash("Annonce introuvable.", "danger")
        return redirect(url_for('admin.panel'))
    
    if annonce['statut'] != 'EN_ATTENTE':
        flash(f"Cette annonce n'est pas en attente (statut actuel : {annonce['statut']}).", "warning")
        return redirect(url_for('admin.panel'))
    
    # ── 2. Mise à jour du statut ────────────────────────────────────────────
    db.execute(
        """
        UPDATE ANNONCE
        SET statut = 'PUBLIEE'
        WHERE id = ?
        """,
        (annonce_id,)
    )
    
    # ── 3. Enregistrement de la décision dans SIGNAL_DECISION ───────────────
    # Cela permet de tracer QUI a validé QUOI et QUAND.
    # C'est important pour la transparence et l'audit de la modération.
    
    db.execute(
        """
        INSERT INTO SIGNAL_DECISION (id_annonce, id_admin, decision, motif)
        VALUES (?, ?, ?, ?)
        """,
        (annonce_id, id_admin, 'APPROUVEE', 'Annonce conforme aux règles de la plateforme')
    )
    
    # ── 4. Validation et redirection ────────────────────────────────────────
    db.commit()
    flash("Annonce validée avec succès ! Elle est maintenant visible sur l'accueil.", "success")
    return redirect(url_for('admin.panel'))


# ── Route : Rejeter une annonce (/admin/rejeter/<id>) ─────────────────────────

@admin.route('/admin/rejeter/<int:annonce_id>', methods=['POST'])
@login_required
@admin_required
def rejeter(annonce_id):
    """
    Passe le statut d'une annonce de 'EN_ATTENTE' à 'REJETEE'.
    
    PARAMÈTRE URL : annonce_id → ID de l'annonce à rejeter
    
    MÉTHODE POST uniquement : même raison que pour valider.
    
    Le motif de rejet est récupéré depuis un champ <textarea> du formulaire.
    """
    
    db = get_db()
    id_admin = session.get('user_id')
    
    # ── 1. Vérification que l'annonce existe et est bien en attente ─────────
    annonce = db.execute(
        "SELECT id, statut FROM ANNONCE WHERE id = ?",
        (annonce_id,)
    ).fetchone()
    
    if annonce is None:
        flash("Annonce introuvable.", "danger")
        return redirect(url_for('admin.panel'))
    
    if annonce['statut'] != 'EN_ATTENTE':
        flash(f"Cette annonce n'est pas en attente (statut actuel : {annonce['statut']}).", "warning")
        return redirect(url_for('admin.panel'))
    
    # ── 2. Récupération du motif de rejet ───────────────────────────────────
    # Le motif est envoyé via un champ caché ou un textarea dans le formulaire
    motif = request.form.get('motif', '').strip()
    
    if not motif:
        # Si aucun motif n'est fourni, on met un motif par défaut
        motif = "Annonce non conforme aux règles de la plateforme"
    
    # ── 3. Mise à jour du statut ────────────────────────────────────────────
    db.execute(
        """
        UPDATE ANNONCE
        SET statut = 'REJETEE'
        WHERE id = ?
        """,
        (annonce_id,)
    )
    
    # ── 4. Enregistrement de la décision ────────────────────────────────────
    db.execute(
        """
        INSERT INTO SIGNAL_DECISION (id_annonce, id_admin, decision, motif)
        VALUES (?, ?, ?, ?)
        """,
        (annonce_id, id_admin, 'REJETEE', motif)
    )
    
    # ── 5. Validation et redirection ────────────────────────────────────────
    db.commit()
    flash(f"Annonce rejetée. Motif : {motif}", "info")
    return redirect(url_for('admin.panel'))


# ── Route : Analyser une annonce avec l'IA (/admin/analyser/<id>) ────────────
# CHANGEMENT : on analyse maintenant le texte de l'annonce (titre, description,
# prix, type, surface, adresse) au lieu d'une image, car les modèles vision
# gratuits ne sont plus disponibles. La logique reste identique.

@admin.route('/admin/analyser/<int:annonce_id>', methods=['POST'])
@login_required
@admin_required
def analyser(annonce_id):
    db = get_db()

    # CHANGEMENT : la requête récupère maintenant aussi titre, description,
    # surface et adresse en plus de prix et type_bien
    annonce = db.execute(
        """
        SELECT a.titre, a.description, a.prix,
               b.type as type_bien, b.surface, b.adresse
        FROM ANNONCE a
        JOIN BIEN_IMMOBILIER b ON a.id_bien = b.id
        WHERE a.id = ?
        """,
        (annonce_id,)
    ).fetchone()

    if annonce is None:
        flash("Annonce introuvable.", "danger")
        return redirect(url_for('admin.panel'))

    # CHANGEMENT : on passe tous les champs textuels à analyser_image.
    # chemin_image=None car on n'analyse plus de photo.
    resultat = analyser_image(
        chemin_image=None,
        type_bien_declare=annonce['type_bien'],
        prix=annonce['prix'],
        titre=annonce['titre'],
        description=annonce['description'],
        surface=annonce['surface'],
        adresse=annonce['adresse']
    )

    if resultat['succes']:
        flash(f"🤖 Analyse IA :\n{resultat['analyse_brute']}", "info")
    else:
        flash(f"Erreur d'analyse : {resultat['erreur']}", "danger")

    return redirect(url_for('admin.panel'))