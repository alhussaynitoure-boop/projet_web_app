"""
auth.py — Module d'authentification de l'application
=====================================================
Ce fichier est un BLUEPRINT Flask. Un Blueprint, c'est comme un "sous-module"
de l'application principale : il regroupe des routes et une logique qui ont
un thème commun (ici : l'authentification).

AVANTAGE : app.py reste propre et lisible. Tout ce qui concerne
"se connecter / s'inscrire / se déconnecter" est isolé ici.

FONCTIONNEMENT :
  1. On crée un Blueprint nommé 'auth'
  2. On y attache des routes (@auth.route(...))
  3. Dans app.py, on "enregistre" ce Blueprint → Flask découvre ces routes
"""

# ── Imports ────────────────────────────────────────────────────────────────────

from flask import (
    Blueprint,       # Pour créer le sous-module de routes
    render_template, # Pour afficher un fichier HTML
    request,         # Pour lire les données du formulaire (POST)
    redirect,        # Pour rediriger l'utilisateur vers une autre URL
    url_for,         # Pour générer une URL à partir du nom d'une fonction
    flash,           # Pour envoyer un message temporaire à l'utilisateur
    session,         # Pour stocker des données de l'utilisateur entre les requêtes
    g                # Objet "global context" de Flask → on y accède à la BDD
)

from functools import wraps
# 'wraps' est nécessaire pour créer des décorateurs correctement.
# Il "copie" les métadonnées de la fonction originale (son nom, sa doc...)
# vers la fonction enveloppante. Sans lui, Flask peut se mélanger entre les routes.

from werkzeug.security import generate_password_hash, check_password_hash
# werkzeug est une bibliothèque incluse avec Flask.
# generate_password_hash("monmotdepasse") → "pbkdf2:sha256:260000$..."
#   transforme un mot de passe lisible en une chaîne illisible (hachée).
#   On ne JAMAIS stocker un mot de passe en clair en base de données.
# check_password_hash(hash_stocké, mot_de_passe_saisi) → True ou False
#   compare le mot de passe tapé par l'utilisateur avec le haché stocké en BDD.


# ── Création du Blueprint ──────────────────────────────────────────────────────

# Blueprint('auth', __name__) crée un Blueprint :
#   - 'auth' : le nom interne du blueprint (utilisé dans url_for('auth.connexion'))
#   - __name__ : indique à Flask où chercher les templates/static de CE blueprint
auth = Blueprint('auth', __name__)


# ── Fonction utilitaire : accès à la base de données ──────────────────────────

def get_db():
    """
    Récupère la connexion à la base de données depuis le contexte Flask 'g'.
    Cette connexion a été ouverte dans app.py pour la requête en cours.
    On réutilise la MÊME connexion plutôt que d'en ouvrir une nouvelle.
    """
    # getattr(g, '_database', None) :
    #   - essaie de lire l'attribut '_database' depuis g
    #   - si '_database' n'existe pas encore, retourne None
    db = getattr(g, '_database', None)

    if db is None:
        # Ce cas ne devrait pas arriver si app.py est bien configuré,
        # mais on l'ajoute par sécurité.
        from app import get_db as app_get_db
        db = app_get_db()

    return db


# ── Décorateur @login_required ─────────────────────────────────────────────────

def login_required(f):
    """
    Décorateur de sécurité : protège une route contre les accès non connectés.

    COMMENT ÇA MARCHE ?
    Un décorateur est une fonction qui "enveloppe" une autre fonction.
    @login_required sur une route signifie :
      "Avant d'exécuter cette route, vérifie d'abord que l'utilisateur est connecté."

    UTILISATION (dans app.py ou n'importe quel blueprint) :
        @app.route('/publier')
        @login_required          ← on ajoute juste cette ligne
        def publier():
            ...

    Si l'utilisateur N'EST PAS connecté → redirigé vers /connexion
    Si l'utilisateur EST connecté → la vraie fonction s'exécute normalement
    """
    @wraps(f)
    # @wraps(f) copie le nom et la docstring de la fonction 'f' (la vraie route)
    # vers 'decorated_function'. C'est CRUCIAL pour Flask qui identifie
    # les routes par leur nom de fonction.

    def decorated_function(*args, **kwargs):
        # *args et **kwargs → on accepte N'IMPORTE QUELS arguments
        # car chaque route peut avoir des paramètres différents
        # (ex: /annonce/<int:id> passe 'id' en argument)

        if 'user_id' not in session:
            # session est un dictionnaire Flask qui persiste entre les requêtes
            # du MÊME utilisateur (grâce à un cookie chiffré côté navigateur).
            # Si 'user_id' n'est pas dans la session → l'utilisateur n'est pas connecté.

            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            # flash() enregistre un message temporaire qui sera affiché
            # UNE SEULE FOIS sur la prochaine page affichée.
            # "warning" est la catégorie CSS du message (pour le style Bootstrap, etc.)

            return redirect(url_for('auth.connexion'))
            # url_for('auth.connexion') génère l'URL de la route 'connexion'
            # dans le blueprint 'auth' → donne '/connexion'
            # On redirige l'utilisateur vers la page de connexion.

        # Si on arrive ici, l'utilisateur EST connecté.
        # On exécute la vraie fonction de la route avec ses arguments.
        return f(*args, **kwargs)

    return decorated_function
    # On retourne la fonction "enveloppante" qui remplace la vraie fonction.


# ── Route : Inscription (/inscription) ────────────────────────────────────────

@auth.route('/inscription', methods=['GET', 'POST'])
def inscription():
    """
    Gère l'inscription d'un nouvel utilisateur.

    GET  → affiche le formulaire d'inscription vide
    POST → traite les données soumises par le formulaire
    """

    if request.method == 'POST':
        # ── 1. Récupération des données du formulaire ──────────────────────────
        # request.form est un dictionnaire contenant toutes les valeurs
        # des champs <input> du formulaire HTML (attribut 'name').
        # .get('cle') retourne None si le champ est absent (plus sûr que ['cle']).

        nom       = request.form.get('nom', '').strip()
        # .strip() supprime les espaces en début et fin de chaîne
        # Ex: "  Ali  " → "Ali"

        email     = request.form.get('email', '').strip().lower()
        # .lower() met en minuscules → "Ali@Gmail.COM" devient "ali@gmail.com"
        # Important pour la cohérence des emails en base de données.

        telephone = request.form.get('telephone', '').strip()
        # Numéro de téléphone (optionnel selon le formulaire)

        mdp       = request.form.get('motDePasse', '')
        # Mot de passe en clair → on ne le .strip() PAS car un espace
        # pourrait être intentionnel dans le mot de passe.

        mdp_confirm = request.form.get('confirmerMotDePasse', '')
        # Confirmation du mot de passe → doit être identique à mdp

        role      = request.form.get('role', 'ACHETEUR').upper()
        # .upper() met en majuscules → "vendeur" devient "VENDEUR"
        # On force la valeur par défaut à 'ACHETEUR' si non fourni.

        # ── 2. Validation des données ──────────────────────────────────────────
        # On vérifie que les données sont correctes AVANT d'écrire en base.

        if not nom or not email or not mdp:
            # Si un champ obligatoire est vide (chaîne vide = False en Python)
            flash("Nom, email et mot de passe sont obligatoires.", "danger")
            return render_template('inscription.html')
            # On ré-affiche le formulaire avec le message d'erreur.

        if mdp != mdp_confirm:
            # Les deux mots de passe ne correspondent pas
            flash("Les mots de passe ne correspondent pas.", "danger")
            return render_template('inscription.html')

        if len(mdp) < 6:
            # Règle de sécurité minimale : mot de passe d'au moins 6 caractères
            flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
            return render_template('inscription.html')

        if role not in ('ACHETEUR', 'VENDEUR'):
            # On n'accepte que ces deux rôles via le formulaire public.
            # ADMIN ne peut être créé que manuellement en base de données.
            flash("Rôle invalide.", "danger")
            return render_template('inscription.html')

        # ── 3. Vérification que l'email n'existe pas déjà ─────────────────────
        db = get_db()

        utilisateur_existant = db.execute(
            "SELECT id FROM UTILISATEUR WHERE email = ?",
            (email,)
            # Le tuple (email,) est crucial : c'est une REQUÊTE PARAMÉTRÉE.
            # SQLite remplace le '?' par la valeur de 'email' de façon sécurisée.
            # Sans ça, on serait vulnérable aux attaques SQL injection.
            # Ex d'injection : email = "'; DROP TABLE UTILISATEUR; --"
        ).fetchone()
        # .fetchone() récupère LA PREMIÈRE ligne du résultat, ou None si vide.

        if utilisateur_existant:
            # Un utilisateur avec cet email existe déjà
            flash("Un compte avec cet email existe déjà.", "warning")
            return render_template('inscription.html')

        # ── 4. Hachage du mot de passe ─────────────────────────────────────────
        mdp_hache = generate_password_hash(mdp)
        # generate_password_hash("secret123") produit quelque chose comme :
        # "pbkdf2:sha256:260000$abc123$def456..."
        # C'est une chaîne illisible qu'on stocke en base.
        # Si la base de données est compromise, les mots de passe restent secrets.

        # ── 5. Insertion dans la table UTILISATEUR ─────────────────────────────
        # CORRECTION : 'telephone' est maintenant inclus dans l'INSERT.
        # Auparavant, la variable était récupérée du formulaire (ligne 152)
        # mais jamais sauvegardée car la colonne n'existait pas dans le schéma.
        # ────────────────────────────────────────────────────────────────────
        curseur = db.execute(
            """
            INSERT INTO UTILISATEUR (nom, email, motDePasse, role, telephone)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nom, email, mdp_hache, role, telephone or None)
            # telephone or None : si le champ est vide (""), on stocke NULL
            # plutôt qu'une chaîne vide, ce qui est plus propre en base de données.
            # 'dateInscription' n'est pas précisé → SQLite utilise DEFAULT datetime('now')
        )
        # 'curseur' est l'objet résultat de la requête INSERT.

        nouvel_id = curseur.lastrowid
        # .lastrowid récupère l'ID auto-généré par SQLite (AUTOINCREMENT)
        # pour la ligne qu'on vient d'insérer. On en aura besoin pour les FK.

        # ── 6. Insertion dans la table de spécialisation ───────────────────────
        # Selon le rôle, on insère dans ACHETEUR ou VENDEUR.
        # C'est le principe d'héritage Merise : UTILISATEUR + table spécialisée.

        if role == 'ACHETEUR':
            db.execute(
                "INSERT INTO ACHETEUR (id_utilisateur, budget) VALUES (?, ?)",
                (nouvel_id, None)
                # budget = None → NULL en SQL → l'acheteur n'a pas encore
                # renseigné son budget, il pourra le faire plus tard dans son profil.
            )

        elif role == 'VENDEUR':
            db.execute(
                "INSERT INTO VENDEUR (id_utilisateur, agence, SIRET) VALUES (?, ?, ?)",
                (nouvel_id, None, None)
                # agence et SIRET = NULL → le vendeur les renseignera dans son profil.
                # C'est conforme au plan P1 : "infos vendeur gérées ultérieurement".
            )

        # ── 7. Validation de la transaction ───────────────────────────────────
        db.commit()
        # .commit() SAUVEGARDE définitivement toutes les modifications en base.
        # SANS commit(), les INSERT sont annulés à la fermeture de la connexion !
        # C'est comme "Ctrl+S" pour la base de données.

        # ── 8. Message de succès et redirection ───────────────────────────────
        flash(f"Compte créé avec succès ! Bienvenue, {nom}. Connectez-vous.", "success")
        # f-string : f"..." permet d'insérer des variables dans la chaîne.
        # {nom} sera remplacé par la valeur de la variable 'nom'.

        return redirect(url_for('auth.connexion'))
        # Après inscription réussie, on redirige vers la page de connexion.
        # url_for('auth.connexion') → génère '/connexion'

    # Si la méthode est GET (premier affichage de la page) :
    # On affiche simplement le formulaire vide.
    return render_template('inscription.html')


# ── Route : Connexion (/connexion) ─────────────────────────────────────────────

@auth.route('/connexion', methods=['GET', 'POST'])
def connexion():
    """
    Gère la connexion d'un utilisateur existant.

    GET  → affiche le formulaire de connexion
    POST → vérifie les identifiants et ouvre la session
    """

    # Si l'utilisateur est DÉJÀ connecté, pas besoin de se reconnecter.
    if 'user_id' in session:
        return redirect(url_for('index'))
        # url_for('index') → route définie dans app.py, génère '/'

    if request.method == 'POST':
        # ── 1. Récupération des identifiants saisis ────────────────────────────
        email = request.form.get('email', '').strip().lower()
        mdp   = request.form.get('motDePasse', '')

        # ── 2. Recherche de l'utilisateur en base de données ──────────────────
        db = get_db()

        utilisateur = db.execute(
            "SELECT * FROM UTILISATEUR WHERE email = ?",
            (email,)
        ).fetchone()
        # SELECT * → récupère toutes les colonnes de la ligne.
        # Grâce à db.row_factory = sqlite3.Row dans app.py, on peut
        # accéder aux colonnes par nom : utilisateur['nom'], utilisateur['role']...

        # ── 3. Vérification des identifiants ──────────────────────────────────
        if utilisateur is None:
            # Aucun utilisateur trouvé avec cet email.
            # IMPORTANT : on affiche un message VAGUE intentionnellement.
            # Dire "email incorrect" ou "mot de passe incorrect" séparément
            # aide un attaquant à deviner les emails enregistrés.
            flash("Email ou mot de passe incorrect.", "danger")
            return render_template('connexion.html')

        if not check_password_hash(utilisateur['motDePasse'], mdp):
            # check_password_hash(hash_stocké, mdp_saisi) :
            #   - recalcule le hash du mdp saisi
            #   - compare avec le hash stocké
            #   - retourne True si identique, False sinon
            flash("Email ou mot de passe incorrect.", "danger")
            return render_template('connexion.html')

        # ── 4. Ouverture de la session Flask ───────────────────────────────────
        # Si on arrive ici, les identifiants sont CORRECTS.
        # On stocke les infos essentielles dans la session.

        session.clear()
        # On vide d'abord toute session existante pour éviter des conflits
        # (sécurité : empêche la "session fixation attack").

        session['user_id'] = utilisateur['id']
        # Stocke l'ID de l'utilisateur → sera utilisé pour les requêtes SQL
        # qui nécessitent de savoir QUI fait l'action.

        session['nom'] = utilisateur['nom']
        # Stocke le nom → pour afficher "Bonjour, Ali" dans le menu de navigation.

        session['role'] = utilisateur['role']
        # Stocke le rôle → pour vérifier les permissions (ACHETEUR vs VENDEUR vs ADMIN).

        # ── 5. Message de bienvenue et redirection ─────────────────────────────
        flash(f"Bienvenue, {utilisateur['nom']} !", "success")

        # Redirection intelligente : si l'utilisateur voulait accéder à une page
        # protégée avant d'être redirigé vers /connexion, on l'y renvoie.
        # request.args.get('next') lit le paramètre URL ?next=/publier
        next_page = request.args.get('next')

        if next_page:
            return redirect(next_page)
            # On redirige vers la page qu'il voulait atteindre initialement.
        else:
            return redirect(url_for('index'))
            # Sinon, on redirige vers l'accueil.

    # Si méthode GET : afficher le formulaire de connexion vide.
    return render_template('connexion.html')


# ── Route : Déconnexion (/deconnexion) ─────────────────────────────────────────

@auth.route('/deconnexion')
def deconnexion():
    """
    Déconnecte l'utilisateur en vidant sa session.
    Accessible uniquement par GET (pas de formulaire nécessaire).
    """
    session.clear()
    # session.clear() supprime TOUTES les données de la session :
    # user_id, nom, role... L'utilisateur redevient "anonyme".
    # Le cookie de session côté navigateur sera également invalidé.

    flash("Vous avez été déconnecté avec succès.", "info")
    # "info" = catégorie neutre (ni succès vert, ni erreur rouge)

    return redirect(url_for('index'))
    # Après déconnexion, on retourne à l'accueil.