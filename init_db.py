"""
init_db.py — Script d'initialisation de la base de données
===========================================================
CE FICHIER NE S'EXECUTE QU'UNE SEULE FOIS au démarrage du projet
(ou quand on veut repartir de zéro).

Il fait 3 choses :
  1. Se connecte au fichier app.db (le crée s'il n'existe pas)
  2. Lit le schéma SQL depuis models.py
  3. Exécute le SQL pour créer toutes les tables

COMMENT L'UTILISER :
  --> Dans le terminal : python init_db.py
  --> Une seule fois suffit. Si tu le relances, rien ne se passe
      car toutes les tables ont IF NOT EXISTS (sécurité intégrée).
"""

import sqlite3
# sqlite3 est un module Python INTEGRE (pas besoin de pip install).
# Il permet de créer et manipuler des bases de données SQLite
# directement depuis Python, sans serveur externe.

import os
# os permet de naviguer dans les dossiers et construire des chemins.

from models import get_schema
# On importe la fonction get_schema() depuis notre fichier models.py.
# Elle retourne tout le SQL de création des tables sous forme de texte.

from config import DATABASE
# On importe le chemin vers la base de données depuis config.py.
# DATABASE = "/chemin/vers/projet_web/app.db"
# Comme ça, si on change le chemin dans config.py, tout suit automatiquement.


def initialiser_base():
    """
    Fonction principale : crée la base de données et toutes les tables.

    DEROULEMENT DETAILLE :
    ─────────────────────
    1. sqlite3.connect(DATABASE) --> ouvre (ou crée) le fichier app.db
    2. connexion.executescript(sql) --> exécute le bloc SQL complet
    3. connexion.commit() --> valide les changements (les sauvegarde vraiment)
    4. connexion.close() --> ferme proprement la connexion

    POURQUOI commit() ?
    SQLite fonctionne par "transactions". Tant qu'on n'a pas appelé
    commit(), les changements sont temporaires et peuvent être annulés
    avec rollback(). Le commit() dit "c'est officiel, sauvegarde tout".
    """

    print("=" * 55)
    print("  Initialisation de la base de donnees...")
    print("=" * 55)

    # -- Etape 1 : Vérifier si le fichier app.db existe déjà ----------
    if os.path.exists(DATABASE):
        print(f"\n[!] La base '{DATABASE}' existe deja.")
        print("    Les tables existantes ne seront pas modifiees")
        print("    (grace a IF NOT EXISTS dans le SQL).")
    else:
        print(f"\n[OK] Nouveau fichier cree : {DATABASE}")

    # -- Etape 2 : Ouvrir la connexion à SQLite ------------------------
    connexion = sqlite3.connect(DATABASE)
    # sqlite3.connect() fait deux choses :
    #   - Si app.db existe --> l'ouvre et retourne un objet connexion
    #   - Si app.db n'existe PAS --> crée le fichier vide puis l'ouvre
    # L'objet "connexion" est notre point d'entrée pour toutes les opérations.

    print("\n[OK] Connexion a SQLite etablie.")

    # -- Etape 3 : Activer les clés étrangères -------------------------
    connexion.execute("PRAGMA foreign_keys = ON;")
    # Cette ligne est ESSENTIELLE et souvent oubliée !
    # Par défaut, SQLite ignore les contraintes de clés étrangères.
    # Cette commande les active pour CETTE connexion uniquement.
    # (C'est aussi présent dans le SQL de models.py, mais on le met
    #  ici aussi par sécurité, car executescript() peut le réinitialiser.)

    # -- Etape 4 : Récupérer le SQL de models.py -----------------------
    sql_schema = get_schema()
    # sql_schema contient maintenant tout le texte SQL :
    # "CREATE TABLE IF NOT EXISTS UTILISATEUR (...); CREATE TABLE ..."

    # -- Etape 5 : Exécuter le SQL pour créer toutes les tables --------
    try:
        connexion.executescript(sql_schema)
        # executescript() exécute un BLOC de plusieurs instructions SQL
        # d'un seul coup. C'est différent de execute() qui n'en fait qu'une.
        # Il fait automatiquement un COMMIT à la fin.

        print("[OK] Toutes les tables ont ete creees avec succes :\n")

        # -- Etape 6 : Vérifier les tables créées ----------------------
        curseur = connexion.cursor()
        # Le curseur est comme un "stylo" qu'on utilise pour écrire
        # ou lire dans la base. On en a besoin pour les requêtes SELECT.

        curseur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name;
        """)
        # sqlite_master est une table INTERNE de SQLite qui liste
        # tous les objets de la base (tables, index, vues...).
        # On sélectionne juste les 'table' et on les trie par nom.

        tables = curseur.fetchall()
        # fetchall() récupère TOUS les résultats de la requête SELECT.
        # Retourne une liste de tuples : [('ACHETEUR',), ('ADMIN',), ...]

        for (nom_table,) in tables:
            # On "dépaquète" chaque tuple (nom_table,) en une variable nom_table.
            print(f"   --> {nom_table}")

        print(f"\n[OK] Base de donnees prete ! ({len(tables)} tables au total)")

    except sqlite3.Error as erreur:
        # Si une erreur SQL survient (ex: syntaxe incorrecte),
        # on l'affiche clairement au lieu de laisser Python crasher
        # avec un message incompréhensible.
        print(f"\n[ERREUR] Lors de la creation des tables :")
        print(f"         {erreur}")

    finally:
        # Le bloc "finally" s'exécute TOUJOURS, qu'il y ait une erreur ou non.
        # On s'assure ainsi que la connexion est toujours fermée proprement.
        # Une connexion non fermée peut corrompre la base ou bloquer l'accès.
        connexion.close()
        print("\n[OK] Connexion fermee proprement.")
        print("=" * 55)


def creer_admin_par_defaut():
    """
    Crée un compte administrateur de démonstration si aucun admin n'existe.

    POURQUOI cette fonction ?
    ─────────────────────────
    Au premier lancement, la base est vide. Pour pouvoir tester la
    modération, il faut au moins un compte admin. Cette fonction en
    crée un automatiquement avec des identifiants connus.

    ATTENTION EN PRODUCTION : changer l'email et le mot de passe !
    """

    from werkzeug.security import generate_password_hash
    # werkzeug est installé automatiquement avec Flask.
    # generate_password_hash() transforme "admin123" en une chaîne
    # sécurisée comme : "pbkdf2:sha256:260000$xyz...abc"
    # Même si quelqu'un vole la base, il ne peut pas lire le mot de passe.

    connexion = sqlite3.connect(DATABASE)
    connexion.execute("PRAGMA foreign_keys = ON;")
    curseur = connexion.cursor()

    # Vérifier si un admin existe déjà
    curseur.execute("SELECT COUNT(*) FROM ADMIN;")
    nb_admins = curseur.fetchone()[0]
    # fetchone() récupère UN SEUL résultat (la première ligne).
    # [0] prend le premier élément du tuple : le nombre d'admins.

    if nb_admins == 0:
        print("\n[INFO] Creation du compte administrateur par defaut...")

        mot_de_passe_hache = generate_password_hash("admin123")
        # "admin123" --> hachage sécurisé stocké en base.
        # En production, utiliser un mot de passe fort !

        try:
            # Insérer d'abord dans UTILISATEUR
            curseur.execute("""
                INSERT INTO UTILISATEUR (nom, email, motDePasse, role)
                VALUES (?, ?, ?, ?)
            """, ("Administrateur", "admin@immo.dz", mot_de_passe_hache, "ADMIN"))
            # Les "?" sont des PARAMETRES LIES (placeholders).
            # SQLite remplace chaque "?" par la valeur correspondante dans le tuple.
            # C'est LA PROTECTION contre les injections SQL :
            # les valeurs ne sont JAMAIS concaténées directement dans le SQL.

            id_admin = curseur.lastrowid
            # lastrowid retourne l'ID auto-généré de la dernière insertion.
            # On en a besoin pour l'insérer dans la table ADMIN ensuite.

            # Insérer dans ADMIN avec l'ID récupéré
            curseur.execute("""
                INSERT INTO ADMIN (id_utilisateur, niveau, permissions)
                VALUES (?, ?, ?)
            """, (id_admin, 2, "moderer,valider,rejeter,supprimer"))

            connexion.commit()
            # commit() valide et sauvegarde définitivement les deux insertions.

            print("[OK] Admin cree avec succes !")
            print("     Email        : admin@immo.dz")
            print("     Mot de passe : admin123")
            print("     /!\\ Changez ce mot de passe en production !")

        except sqlite3.IntegrityError as e:
            # IntegrityError = violation de contrainte UNIQUE ou FK.
            # Ex: si on essaie d'insérer un email déjà existant.
            print(f"[!] Admin deja existant ou conflit : {e}")
            connexion.rollback()
            # rollback() annule toutes les opérations non commitées.
            # Evite d'avoir un utilisateur sans entrée ADMIN correspondante.

    else:
        print(f"\n[OK] {nb_admins} admin(s) deja present(s), aucune action necessaire.")

    connexion.close()


# -- Point d'entrée du script ---------------------------------------------
if __name__ == "__main__":
    """
    if __name__ == "__main__" signifie :
    "Exécute ce bloc SEULEMENT si ce fichier est lancé directement"
    (pas s'il est importé dans un autre fichier).

    Exemple :
      --> python init_db.py        --> __name__ == "__main__" --> s'exécute
      --> from init_db import ...  --> __name__ == "init_db"  --> ne s'exécute pas
    """
    initialiser_base()
    creer_admin_par_defaut()
