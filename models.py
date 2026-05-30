"""
models.py — Définition du schéma de la base de données
=======================================================
Ce fichier contient UNE SEULE FONCTION : get_schema()
Elle retourne le texte SQL complet pour créer toutes les tables.

POURQUOI un fichier séparé ?
→ Principe de séparation des responsabilités :
  - models.py  = "quoi" (la structure des données)
  - init_db.py = "comment" (comment on crée la BDD)
  - app.py     = "routes" (ce que l'utilisateur peut faire)

ORDRE DE CRÉATION DES TABLES — TRÈS IMPORTANT !
SQLite refuse de créer une table qui référence (FK) une table
qui n'existe pas encore. Donc l'ordre est :
  1. Tables sans dépendances : UTILISATEUR, BIEN_IMMOBILIER
  2. Tables qui en dépendent : VENDEUR, ACHETEUR, ADMIN, SESSION
  3. Tables qui dépendent de niveau 2 : ANNONCE, FILTRE
  4. Tables qui dépendent de niveau 3 : MEDIA, COMPTEUR, SIGNAL_DECISION, RECHERCHE
"""


def get_schema():
    """
    Retourne le script SQL complet sous forme d'une chaîne de caractères.
    Ce script sera exécuté dans init_db.py pour créer toutes les tables.
    """

    return """

    -- =========================================================
    --  PRAGMA : activer les clés étrangères dans SQLite
    -- =========================================================
    -- Par défaut, SQLite N'APPLIQUE PAS les contraintes de clés
    -- étrangères (FK). Il faut l'activer manuellement à chaque
    -- connexion avec cette commande.
    -- Concrètement : si on essaie d'insérer une ANNONCE avec un
    -- id_vendeur qui n'existe pas dans VENDEUR, SQLite renverra
    -- une erreur au lieu de le laisser passer silencieusement.
    PRAGMA foreign_keys = ON;


    -- =========================================================
    --  TABLE 1 : UTILISATEUR  (table racine — aucune dépendance)
    -- =========================================================
    -- C'est la table principale de gestion des comptes.
    -- Toutes les autres tables "personnes" (VENDEUR, ACHETEUR, ADMIN)
    -- sont des SPÉCIALISATIONS de cette table (héritage Merise).
    -- Chaque ligne = une personne inscrite sur la plateforme.
    CREATE TABLE IF NOT EXISTS UTILISATEUR (

        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        -- INTEGER PRIMARY KEY → SQLite crée automatiquement un identifiant
        -- unique pour chaque utilisateur (1, 2, 3, ...).
        -- AUTOINCREMENT → le numéro augmente toujours, même si on supprime
        -- des lignes (évite de réutiliser un ancien ID).

        nom             VARCHAR(100) NOT NULL,
        -- VARCHAR(100) = chaîne de caractères de maximum 100 caractères.
        -- NOT NULL = ce champ est OBLIGATOIRE, on ne peut pas l'omettre.

        email           VARCHAR(150) UNIQUE NOT NULL,
        -- UNIQUE → deux utilisateurs ne peuvent pas avoir le même email.
        -- SQLite créera automatiquement un index pour vérifier ça rapidement.

        motDePasse      VARCHAR(255) NOT NULL,
        -- On stocke le MOT DE PASSE HACHÉ (jamais le mot de passe en clair !).
        -- bcrypt/werkzeug produit des hachés d'environ 60 caractères,
        -- mais on met 255 pour avoir de la marge.

        role            TEXT CHECK(role IN ('ACHETEUR', 'VENDEUR', 'ADMIN'))
                        NOT NULL DEFAULT 'ACHETEUR',
        -- SQLite ne supporte pas ENUM comme MySQL.
        -- On simule avec TEXT + CHECK() qui vérifie que la valeur
        -- fait partie de la liste autorisée.
        -- DEFAULT 'ACHETEUR' → si on ne précise pas le rôle, l'utilisateur
        -- est acheteur par défaut.

        dateInscription DATETIME DEFAULT (datetime('now'))
        -- datetime('now') → fonction SQLite qui retourne la date/heure actuelle
        -- au format : "2024-05-29 18:30:00"
        -- DEFAULT → si on n'insère pas cette valeur, SQLite la remplit automatiquement.
    );


    -- =========================================================
    --  TABLE 2 : VENDEUR  (spécialisation de UTILISATEUR)
    -- =========================================================
    -- Un vendeur EST un utilisateur + des infos supplémentaires.
    -- Le lien se fait par id_utilisateur qui pointe vers UTILISATEUR.id
    -- C'est le pattern "héritage par table séparée" (Merise/MLD).
    CREATE TABLE IF NOT EXISTS VENDEUR (

        id_utilisateur  INTEGER PRIMARY KEY,
        -- PK + FK en même temps :
        -- PRIMARY KEY → identifie de façon unique ce vendeur
        -- (et le numéro EST le même que dans UTILISATEUR)

        agence          VARCHAR(150),
        -- Nom de l'agence immobilière (peut être NULL si vendeur particulier)

        SIRET           VARCHAR(20) UNIQUE,
        -- Numéro SIRET de l'agence (identifiant officiel entreprise France).
        -- UNIQUE → deux agences ne peuvent pas avoir le même SIRET.
        -- Peut être NULL pour les particuliers.

        FOREIGN KEY (id_utilisateur) REFERENCES UTILISATEUR(id)
            ON DELETE CASCADE
        -- FOREIGN KEY = clé étrangère : id_utilisateur doit exister dans UTILISATEUR.id
        -- ON DELETE CASCADE = si on supprime un UTILISATEUR, son entrée VENDEUR
        -- est supprimée automatiquement (évite les données orphelines).
    );


    -- =========================================================
    --  TABLE 3 : ACHETEUR  (spécialisation de UTILISATEUR)
    -- =========================================================
    CREATE TABLE IF NOT EXISTS ACHETEUR (

        id_utilisateur  INTEGER PRIMARY KEY,

        budget          REAL,
        -- REAL = nombre décimal (équivalent DOUBLE en SQLite).
        -- Budget maximum de l'acheteur en DA. Peut être NULL.

        FOREIGN KEY (id_utilisateur) REFERENCES UTILISATEUR(id)
            ON DELETE CASCADE
    );


    -- =========================================================
    --  TABLE 4 : ADMIN  (spécialisation de UTILISATEUR)
    -- =========================================================
    CREATE TABLE IF NOT EXISTS ADMIN (

        id_utilisateur  INTEGER PRIMARY KEY,

        niveau          INTEGER,
        -- Niveau de droits de l'admin (ex: 1 = modérateur, 2 = super-admin).

        permissions     TEXT,
        -- Liste des permissions sous forme de texte (ex: "moderer,supprimer,bannir").
        -- On utilise TEXT car SQLite ne supporte pas les tableaux.

        FOREIGN KEY (id_utilisateur) REFERENCES UTILISATEUR(id)
            ON DELETE CASCADE
    );


    -- =========================================================
    --  TABLE 5 : SESSION  (gestion des connexions actives)
    -- =========================================================
    -- Une SESSION représente une connexion active d'un utilisateur.
    -- Flask gère les sessions côté serveur avec un token unique.
    CREATE TABLE IF NOT EXISTS SESSION (

        token           VARCHAR(255) PRIMARY KEY,
        -- Le token est une longue chaîne aléatoire (ex: UUID).
        -- Il sert de clé primaire CAR il identifie de façon unique
        -- chaque connexion.

        id_utilisateur  INTEGER NOT NULL,

        dateConnexion   DATETIME NOT NULL,

        dateExpiration  DATETIME,
        -- NULL = la session ne expire pas automatiquement.

        FOREIGN KEY (id_utilisateur) REFERENCES UTILISATEUR(id)
            ON DELETE CASCADE
    );


    -- =========================================================
    --  TABLE 6 : BIEN_IMMOBILIER  (table racine — aucune dépendance)
    -- =========================================================
    -- Représente le bien physique (l'appartement, la maison...)
    -- SÉPARÉ de l'annonce car un même bien peut avoir plusieurs
    -- annonces au fil du temps (vendu, puis remis en vente, etc.)
    CREATE TABLE IF NOT EXISTS BIEN_IMMOBILIER (

        id      INTEGER PRIMARY KEY AUTOINCREMENT,

        adresse VARCHAR(255) NOT NULL,
        -- Adresse complète du bien (rue, numéro, ville, wilaya).

        surface REAL,
        -- Surface en m². REAL = nombre décimal.

        type    TEXT CHECK(type IN ('APPARTEMENT', 'MAISON', 'TERRAIN', 'COMMERCIAL'))
        -- Type de bien. CHECK() simule l'ENUM MySQL.
    );


    -- =========================================================
    --  TABLE 7 : ANNONCE  (dépend de VENDEUR et BIEN_IMMOBILIER)
    -- =========================================================
    -- L'annonce est le lien entre un vendeur et un bien immobilier.
    -- C'est la table centrale de toute l'application.
    CREATE TABLE IF NOT EXISTS ANNONCE (

        id          INTEGER PRIMARY KEY AUTOINCREMENT,

        id_vendeur  INTEGER NOT NULL,
        -- FK vers VENDEUR : qui publie cette annonce ?

        id_bien     INTEGER NOT NULL,
        -- FK vers BIEN_IMMOBILIER : quel bien est mis en vente/location ?

        titre       VARCHAR(200) NOT NULL,

        description TEXT,
        -- TEXT = chaîne de caractères sans limite de longueur (pour les longues descriptions).

        prix        REAL NOT NULL,

        statut      TEXT CHECK(statut IN ('BROUILLON', 'EN_ATTENTE', 'PUBLIEE', 'REJETEE', 'ARCHIVEE'))
                    NOT NULL DEFAULT 'EN_ATTENTE',
        -- Une annonce commence toujours en 'EN_ATTENTE' de validation par un admin.
        -- Elle devient 'PUBLIEE' après validation, 'REJETEE' si refusée.

        datePubli   DATE DEFAULT (date('now')),
        -- date('now') → retourne seulement la date sans l'heure : "2024-05-29"

        FOREIGN KEY (id_vendeur) REFERENCES VENDEUR(id_utilisateur)
            ON DELETE CASCADE,
        FOREIGN KEY (id_bien) REFERENCES BIEN_IMMOBILIER(id)
            ON DELETE CASCADE
    );


    -- =========================================================
    --  TABLE 8 : MEDIA  (photos/vidéos d'une annonce)
    -- =========================================================
    -- Une annonce peut avoir PLUSIEURS photos → relation 1,N.
    -- Chaque ligne = un fichier image lié à une annonce.
    CREATE TABLE IF NOT EXISTS MEDIA (

        id          INTEGER PRIMARY KEY AUTOINCREMENT,

        id_annonce  INTEGER NOT NULL,

        url         VARCHAR(500) NOT NULL,
        -- Chemin vers le fichier image sur le serveur.
        -- Ex: "static/uploads/photo_annonce_3.jpg"

        type        VARCHAR(50),
        -- Type de média : "image", "video", etc.

        ordre       INTEGER DEFAULT 0,
        -- Ordre d'affichage des photos dans la galerie.
        -- 0 = première photo (photo principale).

        FOREIGN KEY (id_annonce) REFERENCES ANNONCE(id)
            ON DELETE CASCADE
        -- Si l'annonce est supprimée, toutes ses photos le sont aussi.
    );


    -- =========================================================
    --  TABLE 9 : COMPTEUR  (statistiques d'une annonce)
    -- =========================================================
    -- Compte les vues, contacts et clics sur une annonce.
    -- Relation 1,1 avec ANNONCE (UNIQUE sur id_annonce).
    CREATE TABLE IF NOT EXISTS COMPTEUR (

        id              INTEGER PRIMARY KEY AUTOINCREMENT,

        id_annonce      INTEGER NOT NULL UNIQUE,
        -- UNIQUE → chaque annonce a AU MAXIMUM un compteur.

        vues            INTEGER DEFAULT 0,
        contacts        INTEGER DEFAULT 0,
        prixs           INTEGER DEFAULT 0,
        -- "prixs" = nombre de fois que le prix a été consulté/cliqué.

        tauxConversion  REAL,
        -- Calculé : (contacts / vues) * 100.
        -- Stocké ici pour éviter de recalculer à chaque requête.

        FOREIGN KEY (id_annonce) REFERENCES ANNONCE(id)
            ON DELETE CASCADE
    );


    -- =========================================================
    --  TABLE 10 : SIGNAL_DECISION  (modération des annonces)
    -- =========================================================
    -- Trace chaque décision d'un admin sur une annonce.
    -- Un admin peut APPROUVER, REJETER ou SIGNALER une annonce.
    CREATE TABLE IF NOT EXISTS SIGNAL_DECISION (

        id          INTEGER PRIMARY KEY AUTOINCREMENT,

        id_annonce  INTEGER NOT NULL,

        id_admin    INTEGER NOT NULL,
        -- Quel admin a pris la décision ?

        decision    TEXT CHECK(decision IN ('APPROUVEE', 'REJETEE', 'FLAGGED')) NOT NULL,

        motif       TEXT,
        -- Explication textuelle de la décision (ex: "Photos manquantes").

        dateDecision DATETIME DEFAULT (datetime('now')),

        FOREIGN KEY (id_annonce) REFERENCES ANNONCE(id)
            ON DELETE CASCADE,
        FOREIGN KEY (id_admin) REFERENCES ADMIN(id_utilisateur)
            ON DELETE CASCADE
    );


    -- =========================================================
    --  TABLE 11 : FILTRE  (critères de recherche sauvegardés)
    -- =========================================================
    -- Un acheteur peut sauvegarder ses critères de recherche.
    -- Ex: "appartements à Alger entre 5M et 10M DA".
    CREATE TABLE IF NOT EXISTS FILTRE (

        id              INTEGER PRIMARY KEY AUTOINCREMENT,

        id_acheteur     INTEGER NOT NULL,

        prixMin         REAL,
        prixMax         REAL,
        surfaceMin      REAL,

        type            TEXT CHECK(type IN ('APPARTEMENT', 'MAISON', 'TERRAIN', 'COMMERCIAL')),

        zone            VARCHAR(150),
        -- Wilaya ou quartier recherché.

        dateRecherche   DATETIME DEFAULT (datetime('now')),

        FOREIGN KEY (id_acheteur) REFERENCES ACHETEUR(id_utilisateur)
            ON DELETE CASCADE
    );


    -- =========================================================
    --  TABLE 12 : RECHERCHE  (table d'association N,N)
    -- =========================================================
    -- Issue de la relation N,N entre ACHETEUR et BIEN_IMMOBILIER :
    -- Un acheteur peut consulter plusieurs biens.
    -- Un bien peut être consulté par plusieurs acheteurs.
    -- → On crée une TABLE INTERMÉDIAIRE avec une PK composée.
    CREATE TABLE IF NOT EXISTS RECHERCHE (

        id_acheteur     INTEGER NOT NULL,
        id_bien         INTEGER NOT NULL,
        id_filtre       INTEGER,
        -- Nullable → une recherche peut se faire sans filtre sauvegardé.

        dateRecherche   DATETIME DEFAULT (datetime('now')),

        PRIMARY KEY (id_acheteur, id_bien),
        -- CLÉ PRIMAIRE COMPOSÉE : la combinaison (acheteur + bien) est unique.
        -- Un acheteur ne peut pas "rechercher" le même bien deux fois dans cette table.

        FOREIGN KEY (id_acheteur) REFERENCES ACHETEUR(id_utilisateur)
            ON DELETE CASCADE,
        FOREIGN KEY (id_bien) REFERENCES BIEN_IMMOBILIER(id)
            ON DELETE CASCADE,
        FOREIGN KEY (id_filtre) REFERENCES FILTRE(id)
            ON DELETE SET NULL
        -- ON DELETE SET NULL → si le filtre est supprimé, id_filtre devient NULL
        -- mais la ligne RECHERCHE est conservée (on ne perd pas l'historique).
    );

    """
