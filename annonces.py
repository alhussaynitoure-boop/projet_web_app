"""
annonces.py — Blueprint de gestion des annonces
================================================
Ce Blueprint regroupe toutes les routes liées aux annonces :
  - /publier      → Créer une nouvelle annonce (VENDEUR uniquement)
  - /modifier/<id> → Modifier une annonce existante (propriétaire uniquement)
  - /supprimer/<id> → Supprimer une annonce (propriétaire uniquement)

DÉPENDANCES :
  - auth.py      → @login_required (vérifie que l'utilisateur est connecté)
  - config.py    → UPLOAD_FOLDER, ALLOWED_EXTENSIONS
  - models.py    → Schéma de la BDD (tables ANNONCE, BIEN_IMMOBILIER, MEDIA)
"""

# ── Imports ────────────────────────────────────────────────────────────────────

from flask import (
    Blueprint,           # Création du sous-module de routes
    render_template,     # Afficher un template HTML
    request,             # Lire les données du formulaire (POST) et les fichiers
    redirect,            # Rediriger vers une autre URL
    url_for,             # Générer une URL depuis le nom d'une fonction
    flash,               # Envoyer un message temporaire à l'utilisateur
    session,             # Accéder aux données de session (user_id, role...)
    g,                   # Contexte global Flask (pour get_db)
    current_app          # Permet d'accéder à app.config (ex: UPLOAD_FOLDER)
)

from werkzeug.utils import secure_filename
# secure_filename("mon fichier.jpg") → "mon_fichier.jpg"
# Nettoie le nom du fichier pour éviter les caractères dangereux
# et les tentatives d'attaque (ex: "../../../etc/passwd.jpg")

import os
# Pour construire les chemins de fichiers et vérifier l'existence de dossiers

import uuid
# Pour générer des noms de fichiers uniques (évite les collisions de noms)

from auth import login_required
# On importe le décorateur depuis auth.py pour protéger nos routes


# ── Création du Blueprint ──────────────────────────────────────────────────────

annonces = Blueprint('annonces', __name__)
# 'annonces' = nom interne du blueprint
# On l'utilisera dans url_for('annonces.publier') par exemple


# ── Fonction utilitaire : accès à la BDD ──────────────────────────────────────

def get_db():
    """
    Récupère la connexion à la base de données depuis le contexte Flask 'g'.
    Même principe que dans auth.py : on réutilise la connexion ouverte par app.py.
    """
    db = getattr(g, '_database', None)
    if db is None:
        from app import get_db as app_get_db
        db = app_get_db()
    return db


# ── Fonction utilitaire : vérifier l'extension d'un fichier ───────────────────

def allowed_file(filename):
    """
    Vérifie si le fichier a une extension autorisée (image).
    
    PARAMÈTRE : filename → nom du fichier uploadé (ex: "photo.jpg")
    RETOURNE  : True si l'extension est dans ALLOWED_EXTENSIONS, False sinon
    
    EXEMPLE :
      allowed_file("maison.jpg")  → True  ✅
      allowed_file("virus.exe")   → False ❌
    """
    # filename.rsplit('.', 1) coupe le nom au dernier point :
    #   "ma.photo.jpg" → ["ma.photo", "jpg"]
    # [1] prend la partie après le dernier point → l'extension
    # .lower() met en minuscules pour comparer de façon insensible à la casse
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    # On vérifie si cette extension est dans le set ALLOWED_EXTENSIONS défini dans config.py
    return extension in current_app.config.get('ALLOWED_EXTENSIONS', set())


# ── Fonction utilitaire : vérifier que l'utilisateur est propriétaire ─────────

def verifier_proprietaire(annonce_id):
    """
    Vérifie que l'annonce appartient bien à l'utilisateur connecté.
    
    PARAMÈTRE : annonce_id → ID de l'annonce à vérifier
    RETOURNE  : True si c'est bien l'annonce du vendeur connecté, False sinon
    
    SÉCURITÉ : Empêche un utilisateur de modifier/supprimer les annonces
    des autres vendeurs en manipulant l'URL (/modifier/42 alors que 42 n'est pas à lui).
    """
    db = get_db()
    
    # On récupère l'ID du vendeur qui a créé cette annonce
    resultat = db.execute(
        "SELECT id_vendeur FROM ANNONCE WHERE id = ?",
        (annonce_id,)
    ).fetchone()
    
    if resultat is None:
        # L'annonce n'existe pas dans la base de données
        return False
    
    # resultat['id_vendeur'] = ID du vendeur propriétaire
    # session['user_id']     = ID de l'utilisateur actuellement connecté
    # On compare les deux : ils doivent être identiques
    return resultat['id_vendeur'] == session.get('user_id')


# ── Route : Publier une annonce (/publier) ────────────────────────────────────

@annonces.route('/publier', methods=['GET', 'POST'])
@login_required
# @login_required (défini dans auth.py) :
#   - Vérifie que 'user_id' est dans la session
#   - Si non → redirige vers /connexion avec un message flash
#   - Si oui → exécute la fonction publier() normalement
def publier():
    """
    Permet à un VENDEUR de publier une nouvelle annonce.
    
    GET  → Affiche le formulaire de publication vide
    POST → Traite les données du formulaire, crée le bien + l'annonce + les médias
    """
    
    # ── VÉRIFICATION : l'utilisateur doit être un VENDEUR ───────────────────
    # Seuls les vendeurs peuvent publier des annonces.
    # Les acheteurs et les admins ne peuvent pas (même si l'admin pourrait
    # théoriquement, dans ce projet on garde la séparation des rôles).
    if session.get('role') != 'VENDEUR':
        flash("Seuls les vendeurs peuvent publier des annonces.", "warning")
        return redirect(url_for('index'))
        # On redirige vers l'accueil avec un message d'avertissement.
    
    # ── TRAITEMENT DU FORMULAIRE (méthode POST) ─────────────────────────────
    if request.method == 'POST':
        
        # ── 1. Récupération des données du formulaire ─────────────────────────
        # request.form est un dictionnaire-like contenant les champs texte
        # du formulaire HTML (<input name="titre">, <textarea name="description">...)
        
        titre       = request.form.get('titre', '').strip()
        # .strip() enlève les espaces au début et à la fin
        # Ex: "  Belle maison  " → "Belle maison"
        
        description = request.form.get('description', '').strip()
        
        prix_str    = request.form.get('prix', '').strip()
        # On récupère en STRING d'abord car on doit vérifier que c'est un nombre
        
        surface_str = request.form.get('surface', '').strip()
        
        wilaya      = request.form.get('wilaya', '').strip()
        # La wilaya est stockée dans BIEN_IMMOBILIER.adresse (on met juste la wilaya ici)
        
        type_bien   = request.form.get('type', '').strip().upper()
        # .upper() force en majuscules pour matcher les valeurs du CHECK() SQL
        # Les valeurs autorisées : APPARTEMENT, MAISON, TERRAIN, COMMERCIAL
        
        adresse     = request.form.get('adresse', '').strip()
        # Adresse complète du bien (rue, ville, wilaya)
        
        # ── 2. Validation des champs obligatoires ─────────────────────────────
        # On vérifie que les champs essentiels ne sont pas vides
        
        erreurs = []
        # Liste qui va accumuler tous les messages d'erreur
        
        if not titre:
            erreurs.append("Le titre est obligatoire.")
        
        if not prix_str:
            erreurs.append("Le prix est obligatoire.")
        else:
            # On essaie de convertir le prix en nombre décimal (float)
            try:
                prix = float(prix_str)
                # float("1500000") → 1500000.0
                if prix <= 0:
                    erreurs.append("Le prix doit être supérieur à 0.")
            except ValueError:
                # float("abc") → lève une exception ValueError
                erreurs.append("Le prix doit être un nombre valide.")
                prix = 0  # Valeur par défaut pour éviter une erreur plus tard
        
        if not surface_str:
            erreurs.append("La surface est obligatoire.")
        else:
            try:
                surface = float(surface_str)
                if surface <= 0:
                    erreurs.append("La surface doit être supérieure à 0.")
            except ValueError:
                erreurs.append("La surface doit être un nombre valide.")
                surface = 0
        
        if not adresse:
            erreurs.append("L'adresse est obligatoire.")
        
        if type_bien not in ('APPARTEMENT', 'MAISON', 'TERRAIN', 'COMMERCIAL'):
            erreurs.append("Le type de bien est invalide.")
        
        # S'il y a des erreurs, on réaffiche le formulaire avec les messages
        if erreurs:
            for err in erreurs:
                flash(err, "danger")
            # On passe les valeurs saisies au template pour qu'il les réaffiche
            # (l'utilisateur n'a pas à tout retaper)
            return render_template('publier.html', 
                                   titre=titre, description=description,
                                   prix=prix_str, surface=surface_str,
                                   wilaya=wilaya, type_bien=type_bien,
                                   adresse=adresse)
        
        # ── 3. Conversion finale des valeurs numériques ───────────────────────
        # On reconvertit car les variables 'prix' et 'surface' ne sont définies
        # que dans le bloc try, pas en dehors. On les reconvertit proprement ici.
        prix = float(prix_str)
        surface = float(surface_str)
        
        # ── 4. Insertion dans BIEN_IMMOBILIER ─────────────────────────────────
        # D'abord, on crée le bien physique (indépendamment de l'annonce).
        # C'est la table "racine" qui ne dépend de personne.
        
        db = get_db()
        
        curseur_bien = db.execute(
            """
            INSERT INTO BIEN_IMMOBILIER (adresse, surface, type)
            VALUES (?, ?, ?)
            """,
            (adresse, surface, type_bien)
            # Les '?' sont remplacés par les valeurs de façon sécurisée
            # (protection contre l'injection SQL)
        )
        
        id_bien = curseur_bien.lastrowid
        # lastrowid récupère l'ID auto-généré par SQLite pour cette insertion
        # Cet ID sera utilisé comme clé étrangère dans ANNONCE
        
        # ── 5. Insertion dans ANNONCE ─────────────────────────────────────────
        # L'annonce lie le vendeur (utilisateur connecté) au bien qu'il vient de créer.
        # Le statut par défaut est 'EN_ATTENTE' (défini dans models.py).
        
        id_vendeur = session.get('user_id')
        # L'ID du vendeur connecté, stocké dans la session lors de la connexion
        
        curseur_annonce = db.execute(
            """
            INSERT INTO ANNONCE (id_vendeur, id_bien, titre, description, prix)
            VALUES (?, ?, ?, ?, ?)
            """,
            (id_vendeur, id_bien, titre, description, prix)
            # 'statut' et 'datePubli' ne sont pas précisés → SQLite utilise les DEFAULT
            #   statut DEFAULT 'EN_ATTENTE'
            #   datePubli DEFAULT date('now')
        )
        
        id_annonce = curseur_annonce.lastrowid
        # ID de l'annonce fraîchement créée → nécessaire pour lier les photos
        
        # ── 6. Gestion des photos uploadées ───────────────────────────────────
        # request.files est un dictionnaire-like contenant les fichiers uploadés
        # via les champs <input type="file" name="photos" multiple>
        
        fichiers = request.files.getlist('photos')
        # .getlist() récupère TOUS les fichiers d'un champ "multiple"
        # Si l'utilisateur upload 3 photos, on obtient une liste de 3 objets FileStorage
        
        # On compte combien de photos valides ont été uploadées
        photos_uploades = 0
        
        for fichier in fichiers:
            # 'fichier' est un objet FileStorage de Flask (wrapper autour du fichier)
            
            # On ignore les entrées vides (l'utilisateur n'a pas sélectionné de fichier)
            if not fichier or fichier.filename == '':
                continue
            
            # Vérification de l'extension du fichier
            if not allowed_file(fichier.filename):
                # Le fichier n'est pas une image autorisée
                flash(f"Fichier ignoré (format non autorisé) : {fichier.filename}", "warning")
                continue
            
            # ── Sécurisation du nom de fichier ────────────────────────────────
            # secure_filename nettoie le nom pour éviter les attaques :
            #   "../../../etc/passwd.jpg" → "etc_passwd.jpg"
            #   "mon fichier.jpg" → "mon_fichier.jpg"
            nom_original = secure_filename(fichier.filename)
            
            # On génère un nom unique pour éviter les collisions
            # (deux utilisateurs uploadent "photo.jpg" → pas de conflit)
            extension = nom_original.rsplit('.', 1)[1].lower()
            nom_unique = f"{uuid.uuid4().hex}.{extension}"
            # uuid.uuid4() génère un identifiant universel unique (très long, aléatoire)
            # .hex le convertit en chaîne hexadécimale sans tirets
            
            # ── Construction du chemin complet ────────────────────────────────
            # current_app.config['UPLOAD_FOLDER'] = /projet/static/uploads/
            chemin_complet = os.path.join(current_app.config['UPLOAD_FOLDER'], nom_unique)
            
            # Chemin relatif pour stocker en BDD (pour l'affichage dans les templates)
            # On stocke "static/uploads/abc123.jpg" pas le chemin absolu complet
            chemin_relatif = os.path.join('static', 'uploads', nom_unique)
            
            # ── Sauvegarde du fichier sur le disque ───────────────────────────
            fichier.save(chemin_complet)
            # .save() écrit le fichier sur le disque dur à l'emplacement indiqué
            
            # ── Insertion dans la table MEDIA ─────────────────────────────────
            db.execute(
                """
                INSERT INTO MEDIA (id_annonce, url, type, ordre)
                VALUES (?, ?, ?, ?)
                """,
                (id_annonce, chemin_relatif, 'image', photos_uploades)
                # 'image' = type de média
                # ordre = photos_uploades → 0 = première photo, 1 = deuxième...
            )
            
            photos_uploades += 1
        
        # ── 7. Validation finale de la transaction ────────────────────────────
        db.commit()
        # .commit() sauvegarde définitivement TOUTES les modifications :
        #   - Le bien immobilier
        #   - L'annonce
        #   - Toutes les photos
        # Sans commit(), tout serait perdu à la fermeture de la connexion !
        
        # ── 8. Message de confirmation et redirection ─────────────────────────
        if photos_uploades > 0:
            flash(f"Annonce publiée avec succès ! {photos_uploades} photo(s) ajoutée(s). "
                  f"Elle est en attente de validation par un administrateur.", "success")
        else:
            flash("Annonce publiée avec succès (sans photo). "
                  "Elle est en attente de validation par un administrateur.", "success")
        
        return redirect(url_for('mes_annonces'))
        # On redirige vers l'espace personnel pour que le vendeur voie son annonce
        # en statut "EN_ATTENTE"
    
    # ── AFFICHAGE DU FORMULAIRE (méthode GET) ───────────────────────────────
    # Premier affichage : on montre le formulaire vide
    return render_template('publier.html')


# ── Route : Modifier une annonce (/modifier/<id>) ─────────────────────────────

@annonces.route('/modifier/<int:annonce_id>', methods=['GET', 'POST'])
@login_required
def modifier(annonce_id):
    """
    Permet au propriétaire d'une annonce de la modifier.
    
    PARAMÈTRE URL : annonce_id → ID de l'annonce à modifier (ex: /modifier/42)
    
    SÉCURITÉ :
      - Vérifie que l'utilisateur est connecté (@login_required)
      - Vérifie que l'annonce appartient bien au vendeur connecté
      - Seules les annonces EN_ATTENTE ou BROUILLON peuvent être modifiées
        (une annonce PUBLIEE ne doit pas être modifiée sans re-validation)
    """
    
    db = get_db()
    
    # ── 1. Vérification de propriété ────────────────────────────────────────
    if not verifier_proprietaire(annonce_id):
        # L'annonce n'existe pas ou n'appartient pas au vendeur connecté
        flash("Vous n'avez pas le droit de modifier cette annonce.", "danger")
        return redirect(url_for('mes_annonces'))
    
    # ── 2. Récupération de l'annonce et du bien associé ─────────────────────
    # On fait une jointure (JOIN) pour récupérer les infos des deux tables en UNE requête
    annonce = db.execute(
        """
        SELECT 
            a.id, a.titre, a.description, a.prix, a.statut,
            b.id as bien_id, b.adresse, b.surface, b.type
        FROM ANNONCE a
        JOIN BIEN_IMMOBILIER b ON a.id_bien = b.id
        WHERE a.id = ?
        """,
        (annonce_id,)
        # JOIN = on relie ANNONCE et BIEN_IMMOBILIER via la clé étrangère id_bien
        # WHERE a.id = ? → on ne veut QUE l'annonce spécifiée dans l'URL
    ).fetchone()
    
    if annonce is None:
        flash("Annonce introuvable.", "danger")
        return redirect(url_for('mes_annonces'))
    
    # ── 3. Vérification du statut ───────────────────────────────────────────
    # On empêche la modification des annonces déjà validées ou rejetées
    # pour éviter qu'un vendeur ne modifie une annonce après approbation.
    if annonce['statut'] not in ('EN_ATTENTE', 'BROUILLON'):
        flash("Vous ne pouvez modifier que les annonces en attente ou en brouillon.", "warning")
        return redirect(url_for('mes_annonces'))
    
    # ── 4. Traitement du formulaire (POST) ──────────────────────────────────
    if request.method == 'POST':
        
        # ── 4a. Récupération des nouvelles valeurs ──────────────────────────
        nouveau_titre       = request.form.get('titre', '').strip()
        nouvelle_desc       = request.form.get('description', '').strip()
        nouveau_prix_str    = request.form.get('prix', '').strip()
        nouvelle_surface_str = request.form.get('surface', '').strip()
        nouvelle_adresse    = request.form.get('adresse', '').strip()
        nouveau_type        = request.form.get('type', '').strip().upper()
        
        # ── 4b. Validation ──────────────────────────────────────────────────
        erreurs = []
        
        if not nouveau_titre:
            erreurs.append("Le titre est obligatoire.")
        
        if not nouveau_prix_str:
            erreurs.append("Le prix est obligatoire.")
        else:
            try:
                nouveau_prix = float(nouveau_prix_str)
                if nouveau_prix <= 0:
                    erreurs.append("Le prix doit être supérieur à 0.")
            except ValueError:
                erreurs.append("Le prix doit être un nombre valide.")
                nouveau_prix = 0
        
        if not nouvelle_surface_str:
            erreurs.append("La surface est obligatoire.")
        else:
            try:
                nouvelle_surface = float(nouvelle_surface_str)
                if nouvelle_surface <= 0:
                    erreurs.append("La surface doit être supérieure à 0.")
            except ValueError:
                erreurs.append("La surface doit être un nombre valide.")
                nouvelle_surface = 0
        
        if not nouvelle_adresse:
            erreurs.append("L'adresse est obligatoire.")
        
        if nouveau_type not in ('APPARTEMENT', 'MAISON', 'TERRAIN', 'COMMERCIAL'):
            erreurs.append("Le type de bien est invalide.")
        
        if erreurs:
            for err in erreurs:
                flash(err, "danger")
            # On réaffiche le formulaire avec les valeurs saisies
            return render_template('modifier.html', annonce=annonce,
                                   titre=nouveau_titre, description=nouvelle_desc,
                                   prix=nouveau_prix_str, surface=nouvelle_surface_str,
                                   adresse=nouvelle_adresse, type_bien=nouveau_type)
        
        # ── 4c. Mise à jour de l'annonce ────────────────────────────────────
        # On met à jour les deux tables : ANNONCE et BIEN_IMMOBILIER
        
        nouveau_prix = float(nouveau_prix_str)
        nouvelle_surface = float(nouvelle_surface_str)
        
        # Mise à jour de l'annonce
        db.execute(
            """
            UPDATE ANNONCE
            SET titre = ?, description = ?, prix = ?
            WHERE id = ?
            """,
            (nouveau_titre, nouvelle_desc, nouveau_prix, annonce_id)
            # WHERE id = ? → très important ! Sinon on modifierait TOUTES les annonces !
        )
        
        # Mise à jour du bien immobilier
        db.execute(
            """
            UPDATE BIEN_IMMOBILIER
            SET adresse = ?, surface = ?, type = ?
            WHERE id = ?
            """,
            (nouvelle_adresse, nouvelle_surface, nouveau_type, annonce['bien_id'])
        )
        
        # ── 4d. Gestion des nouvelles photos (optionnel) ────────────────────
        # L'utilisateur peut ajouter des photos supplémentaires
        fichiers = request.files.getlist('photos')
        
        # On compte combien de photos existent déjà pour l'ordre
        compteur_photos = db.execute(
            "SELECT COUNT(*) as total FROM MEDIA WHERE id_annonce = ?",
            (annonce_id,)
        ).fetchone()['total']
        
        for fichier in fichiers:
            if not fichier or fichier.filename == '':
                continue
            
            if not allowed_file(fichier.filename):
                flash(f"Fichier ignoré (format non autorisé) : {fichier.filename}", "warning")
                continue
            
            nom_original = secure_filename(fichier.filename)
            extension = nom_original.rsplit('.', 1)[1].lower()
            nom_unique = f"{uuid.uuid4().hex}.{extension}"
            
            chemin_complet = os.path.join(current_app.config['UPLOAD_FOLDER'], nom_unique)
            chemin_relatif = os.path.join('static', 'uploads', nom_unique)
            
            fichier.save(chemin_complet)
            
            db.execute(
                """
                INSERT INTO MEDIA (id_annonce, url, type, ordre)
                VALUES (?, ?, ?, ?)
                """,
                (annonce_id, chemin_relatif, 'image', compteur_photos)
            )
            
            compteur_photos += 1
        
        # ── 4e. Validation et redirection ───────────────────────────────────
        db.commit()
        flash("Annonce modifiée avec succès !", "success")
        return redirect(url_for('mes_annonces'))
    
    # ── 5. Affichage du formulaire pré-rempli (GET) ─────────────────────────
    # On passe l'objet 'annonce' au template pour qu'il pré-remplisse les champs
    return render_template('modifier.html', annonce=annonce)


# ── Route : Supprimer une annonce (/supprimer/<id>) ───────────────────────────

@annonces.route('/supprimer/<int:annonce_id>', methods=['POST'])
@login_required
def supprimer(annonce_id):
    """
    Supprime une annonce et TOUT ce qui lui est lié (bien, photos).
    
    PARAMÈTRE URL : annonce_id → ID de l'annonce à supprimer
    
    SÉCURITÉ :
      - Vérifie que l'utilisateur est connecté
      - Vérifie que l'annonce appartient bien au vendeur connecté
      - Méthode POST uniquement (pas de suppression par simple clic sur un lien)
        → évite les suppressions accidentelles ou malveillantes (CSRF)
    
    CASCADE :
      Grâce aux ON DELETE CASCADE dans models.py, la suppression de l'annonce
      supprime automatiquement :
        - Les entrées dans MEDIA (photos)
        - Les entrées dans COMPTEUR (statistiques)
        - Les entrées dans SIGNAL_DECISION (décisions de modération)
      Mais ATTENTION : le bien immobilier (BIEN_IMMOBILIER) n'est PAS supprimé
      automatiquement car il pourrait être réutilisé. On le supprime manuellement.
    """
    
    db = get_db()
    
    # ── 1. Vérification de propriété ────────────────────────────────────────
    if not verifier_proprietaire(annonce_id):
        flash("Vous n'avez pas le droit de supprimer cette annonce.", "danger")
        return redirect(url_for('mes_annonces'))
    
    # ── 2. Récupération de l'ID du bien lié (pour le supprimer aussi) ───────
    resultat = db.execute(
        "SELECT id_bien FROM ANNONCE WHERE id = ?",
        (annonce_id,)
    ).fetchone()
    
    if resultat is None:
        flash("Annonce introuvable.", "danger")
        return redirect(url_for('mes_annonces'))
    
    id_bien = resultat['id_bien']
    
    # ── 3. Suppression des fichiers photos sur le disque ────────────────────
    # Avant de supprimer l'annonce en BDD, on supprime les fichiers physiques
    # pour ne pas laisser d'images orphelines sur le serveur.
    
    photos = db.execute(
        "SELECT url FROM MEDIA WHERE id_annonce = ?",
        (annonce_id,)
    ).fetchall()
    
    for photo in photos:
        chemin_fichier = photo['url']
        # photo['url'] contient "static/uploads/abc123.jpg"
        
        chemin_complet = os.path.join(current_app.root_path, chemin_fichier)
        # current_app.root_path = dossier racine du projet (où est app.py)
        # os.path.join combine pour donner : /projet/static/uploads/abc123.jpg
        
        try:
            if os.path.exists(chemin_complet):
                os.remove(chemin_complet)
                # os.remove() supprime le fichier du disque dur
        except OSError as e:
            # Si la suppression échoue (fichier verrouillé, permissions...),
            # on logge l'erreur mais on continue (ne pas bloquer la suppression BDD)
            flash(f"Impossible de supprimer le fichier {chemin_fichier} : {e}", "warning")
    
    # ── 4. Suppression en base de données ───────────────────────────────────
    # Ordre IMPORTANT : on supprime d'abord l'annonce (qui a des FK en cascade),
    # puis le bien immobilier (qui n'a pas de cascade vers l'annonce).
    
    db.execute("DELETE FROM ANNONCE WHERE id = ?", (annonce_id,))
    # CASCADE supprime automatiquement : MEDIA, COMPTEUR, SIGNAL_DECISION
    
    db.execute("DELETE FROM BIEN_IMMOBILIER WHERE id = ?", (id_bien,))
    # On supprime aussi le bien car il n'est plus lié à aucune annonce
    
    # ── 5. Validation et redirection ────────────────────────────────────────
    db.commit()
    flash("Annonce supprimée avec succès.", "success")
    return redirect(url_for('mes_annonces'))