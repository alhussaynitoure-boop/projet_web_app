"""
seed_data.py — Script de peuplement de la base de données avec des données de test
=================================================================================

Ce script permet de générer des données de test réalistes pour permettre à P3
de tester le scénario complet sans avoir à créer manuellement chaque compte.

Il crée :
- 3 vendeurs avec des profils variés (particulier, agence)
- 2 acheteurs avec différents budgets
- 10 biens immobiliers de différents types
- 10 annonces avec des statuts variés (BROUILLON, EN_ATTENTE, PUBLIEE, REJETEE)
- Des photos factices pour certaines annonces (simulées sans upload réel)

UTILISATION :
    Dans le terminal : python seed_data.py
    Peut être exécuté plusieurs fois en toute sécurité (utilise des vérifications d'existence)

CONTRAINTES :
    - Backend uniquement (Python, Flask, SQL)
    - Ne touche pas au frontend (CSS, JS, design)
    - Utilise les mêmes patterns que les fichiers existants :
      * get_db() pour l'accès à la BDD
      * Requêtes paramétrées pour se protéger des injections SQL
      * Gestion appropriée des transactions avec commit()/rollback()
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash
import uuid
from datetime import datetime, timedelta

# Import du chemin de la base de données depuis config.py
from config import DATABASE


def get_db():
    """
    Crée une connexion directe à la base de données SQLite.
    Même principe que dans les autres fichiers mais sans dépendance au contexte Flask 'g'.
    """
    connexion = sqlite3.connect(DATABASE)
    connexion.execute("PRAGMA foreign_keys = ON;")
    connexion.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
    return connexion


def creer_vendeurs_et_acheteurs():
    """
    Crée des utilisateurs de test : vendeurs et acheteurs.
    Retourne les IDs créés pour les utiliser dans les fonctions suivantes.
    """
    print("=" * 55)
    print("  Création des utilisateurs de test (vendeurs/acheteurs)")
    print("=" * 55)

    connexion = get_db()
    curseur = connexion.cursor()

    # Données de test pour les vendeurs
    vendeurs_test = [
        {
            'nom': 'Ahmed Benali',
            'email': 'ahmed.benali@email.dz',
            'motDePasse': generate_password_hash('vendeur123'),
            'role': 'VENDEUR',
            'agence': 'Immobilier Alger Centre',
            'SIRET': '12345678901234'
        },
        {
            'nom': 'Fatima Zahraoui',
            'email': 'fatima.zahraoui@email.dz',
            'motDePasse': generate_password_hash('vendeur456'),
            'role': 'VENDEUR',
            'agence': None,  # Vendeur particulier
            'SIRET': None
        },
        {
            'nom': 'Karim Dubois',
            'email': 'karim.dubois@email.dz',
            'motDePasse': generate_password_hash('vendeur789'),
            'role': 'VENDEUR',
            'agence': 'Villa Prestige Immobilier',
            'SIRET': '98765432109876'
        }
    ]

    # Données de test pour les acheteurs
    acheteurs_test = [
        {
            'nom': 'Yacine Merabet',
            'email': 'yacine.merabet@email.dz',
            'motDePasse': generate_password_hash('acheteur123'),
            'role': 'ACHETEUR',
            'budget': 8000000.0  # 8 millions DA
        },
        {
            'nom': 'Lina Khaldi',
            'email': 'lina.khaldi@email.dz',
            'motDePasse': generate_password_hash('acheteur456'),
            'role': 'ACHETEUR',
            'budget': 15000000.0  # 15 millions DA
        }
    ]

    ids_vendeurs = []
    ids_acheteurs = []

    try:
        # Insertion des vendeurs
        for vendeur in vendeurs_test:
            # Exécuter la requête une seule fois
            curseur.execute(
                "SELECT id FROM UTILISATEUR WHERE email = ?",
                (vendeur['email'],)
            )
            result = curseur.fetchone()

            if result is None:
                # Insérer dans UTILISATEUR
                # CORRECTION : 'telephone' ajouté pour être cohérent avec le schéma
                # de models.py (colonne ajoutée lors de la correction de l'incohérence P1).
                curseur.execute(
                    """
                    INSERT INTO UTILISATEUR (nom, email, motDePasse, role, telephone)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (vendeur['nom'], vendeur['email'], vendeur['motDePasse'], vendeur['role'], None)
                    # telephone = None (NULL) : les données de test n'ont pas de numéro de téléphone.
                )
                id_utilisateur = curseur.lastrowid

                # Insérer dans VENDEUR
                curseur.execute(
                    """
                    INSERT INTO VENDEUR (id_utilisateur, agence, SIRET)
                    VALUES (?, ?, ?)
                    """,
                    (id_utilisateur, vendeur['agence'], vendeur['SIRET'])
                )

                ids_vendeurs.append(id_utilisateur)
                print(f"[OK] Vendeur créé : {vendeur['nom']} ({vendeur['email']})")
            else:
                # Utiliser le résultat déjà récupéré
                id_utilisateur = result['id']
                ids_vendeurs.append(id_utilisateur)
                print(f"[INFO] Vendeur existant : {vendeur['nom']} ({vendeur['email']})")

        # Insertion des acheteurs
        for acheteur in acheteurs_test:
            # Exécuter la requête une seule fois
            curseur.execute(
                "SELECT id FROM UTILISATEUR WHERE email = ?",
                (acheteur['email'],)
            )
            result = curseur.fetchone()

            if result is None:
                # Insérer dans UTILISATEUR
                # CORRECTION : 'telephone' ajouté pour être cohérent avec le schéma
                # de models.py (colonne ajoutée lors de la correction de l'incohérence P1).
                curseur.execute(
                    """
                    INSERT INTO UTILISATEUR (nom, email, motDePasse, role, telephone)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (acheteur['nom'], acheteur['email'], acheteur['motDePasse'], acheteur['role'], None)
                    # telephone = None (NULL) : les données de test n'ont pas de numéro de téléphone.
                )
                id_utilisateur = curseur.lastrowid

                # Insérer dans ACHETEUR
                curseur.execute(
                    """
                    INSERT INTO ACHETEUR (id_utilisateur, budget)
                    VALUES (?, ?)
                    """,
                    (id_utilisateur, acheteur['budget'])
                )

                ids_acheteurs.append(id_utilisateur)
                print(f"[OK] Acheteur créé : {acheteur['nom']} ({acheteur['email']})")
            else:
                # Utiliser le résultat déjà récupéré
                id_utilisateur = result['id']
                ids_acheteurs.append(id_utilisateur)
                print(f"[INFO] Acheteur existant : {acheteur['nom']} ({acheteur['email']})")

        connexion.commit()
        print(f"\n[OK] {len(ids_vendeurs)} vendeurs et {len(ids_acheteurs)} acheteurs prêts")

    except sqlite3.Error as erreur:
        print(f"\n[ERREUR] Lors de la création des utilisateurs : {erreur}")
        connexion.rollback()
        ids_vendeurs = []
        ids_acheteurs = []
    finally:
        connexion.close()

    return ids_vendeurs, ids_acheteurs


def creer_biens_immobiliers():
    """
    Crée des biens immobiliers de test variés.
    Retourne les IDs créés pour les utiliser dans la création des annonces.
    """
    print("\n" + "=" * 55)
    print("  Création des biens immobiliers de test")
    print("=" * 55)

    connexion = get_db()
    curseur = connexion.cursor()

    # Données de test pour les biens immobiliers
    biens_test = [
        # Appartements
        {
            'adresse': '12 Rue Didouche Mourad, Alger Centre',
            'surface': 85.5,
            'type': 'APPARTEMENT'
        },
        {
            'adresse': '45 Avenue des frères Ouamrane, Oran',
            'surface': 120.0,
            'type': 'APPARTEMENT'
        },
        {
            'adresse': '78 Rue Larbi Ben Mhidi, Constantine',
            'surface': 65.0,
            'type': 'APPARTEMENT'
        },
        # Maisons
        {
            'adresse': 'Lotissement Les Palmiers, Villa No. 25, Annaba',
            'surface': 220.0,
            'type': 'MAISON'
        },
        {
            'adresse': 'Chemin des Pins, Beni Messous, Alger',
            'surface': 180.0,
            'type': 'MAISON'
        },
        # Terrains
        {
            'adresse': 'Zone industrielle ouest, Parcelle No. 124, Sétif',
            'surface': 500.0,
            'type': 'TERRAIN'
        },
        {
            'adresse': 'Route nationale 5, Terrain agricole, Tizi Ouzou',
            'surface': 2000.0,
            'type': 'TERRAIN'
        },
        # Commerciaux
        {
            'adresse': 'Centre commercial Bab Ezzouar, Local No. 45, Alger',
            'surface': 95.0,
            'type': 'COMMERCIAL'
        },
        {
            'adresse': 'Rue de la République, Boutique No. 12, Blida',
            'surface': 45.0,
            'type': 'COMMERCIAL'
        },
        # Appartement luxueux
        {
            'adresse': 'Résidence El Riadh, Appartement A105, Hydra, Alger',
            'surface': 150.0,
            'type': 'APPARTEMENT'
        }
    ]

    ids_biens = []

    try:
        for bien in biens_test:
            # Exécuter la requête une seule fois
            curseur.execute(
                "SELECT id FROM BIEN_IMMOBILIER WHERE adresse = ?",
                (bien['adresse'],)
            )
            result = curseur.fetchone()

            if result is None:
                curseur.execute(
                    """
                    INSERT INTO BIEN_IMMOBILIER (adresse, surface, type)
                    VALUES (?, ?, ?)
                    """,
                    (bien['adresse'], bien['surface'], bien['type'])
                )
                id_bien = curseur.lastrowid
                ids_biens.append(id_bien)
                print(f"[OK] Bien créé : {bien['type']} - {bien['adresse'][:30]}...")
            else:
                # Utiliser le résultat déjà récupéré
                id_bien = result['id']
                ids_biens.append(id_bien)
                print(f"[INFO] Bien existant : {bien['type']} - {bien['adresse'][:30]}...")

        connexion.commit()
        print(f"\n[OK] {len(ids_biens)} biens immobiliers prêts")

    except sqlite3.Error as erreur:
        print(f"\n[ERREUR] Lors de la création des biens : {erreur}")
        connexion.rollback()
        ids_biens = []
    finally:
        connexion.close()

    return ids_biens


def creer_annonces_et_media(ids_vendeurs, ids_biens):
    """
    Crée des annonces de test avec différents statuts et associe des médias factices.
    """
    print("\n" + "=" * 55)
    print("  Création des annonces et médias de test")
    print("=" * 55)

    connexion = get_db()
    curseur = connexion.cursor()

    # Données de test pour les annonces
    # Format : (titre, description, prix, statut, jours_depuis_publication, id_vendeur_index, id_bien_index)
    annonces_test = [
        # Annonces en attente de validation (à valider par l'admin)
        {
            'titre': 'Spacieux F3 au cœur d\'Alger Centre',
            'description': 'Magnifique appartement de 3 chambres récemment rénové, situé au 3ème étage avec ascenseur. Proche de toutes commodités (transports, commerces, écoles).',
            'prix': 7500000.0,
            'statut': 'EN_ATTENTE',
            'jours_depuis_publication': 2,
            'vendeur_idx': 0,  # Ahmed Benali
            'bien_idx': 0      # 12 Rue Didouche Mourad
        },
        {
            'titre': 'Villa familiale avec jardin à Annaba',
            'description': 'Belle villa de 4 chambres avec grand jardin arboré, garage double et terrasse. Idéale pour une famille recherchant calme et confort.',
            'prix': 18000000.0,
            'statut': 'EN_ATTENTE',
            'jours_depuis_publication': 1,
            'vendeur_idx': 1,  # Fatima Zahraoui
            'bien_idx': 3      # Lotissement Les Palmiers
        },
        {
            'titre': 'Local commercial idéal pour activité libérale',
            'description': 'Local commercial de 95m² en rez-de-chaussée d\'un immeuble récent. Vitrine grande hauteur, acces PMR, parking à proximité.',
            'prix': 3200000.0,
            'statut': 'EN_ATTENTE',
            'jours_depuis_publication': 3,
            'vendeur_idx': 2,  # Karim Dubois
            'bien_idx': 7      # Centre commercial Bab Ezzouar
        },
        # Annonces déjà publiées
        {
            'titre': 'Charmant F2 près de l\'universite',
            'description': 'Appartement de 2 chambres entièrement meublé, situé dans résidence sécurisée avec gardiennage 24/7. Proche universitaire et transports.',
            'prix': 4200000.0,
            'statut': 'PUBLIEE',
            'jours_depuis_publication': 15,
            'vendeur_idx': 0,  # Ahmed Benali
            'bien_idx': 1      # 45 Avenue des frères Ouamrane
        },
        {
            'titre': 'Terrain constructible en zone urbaine',
            'description': 'Parcel de terrain de 500m² en zone urbaine constructible, viabilisé (eau, électricité, réseau telecom). Titre foncier clair.',
            'prix': 6500000.0,
            'statut': 'PUBLIEE',
            'jours_depuis_publication': 22,
            'vendeur_idx': 1,  # Fatima Zahraoui
            'bien_idx': 5      # Zone industrielle ouest
        },
        {
            'titre': 'Bureau équipé en centre ville',
            'description': 'Bureau de 45m² entièrement équipé et climatisé, situé dans immeuble de standing avec service de nettoyage inclus.',
            'prix': 1800000.0,
            'statut': 'PUBLIEE',
            'jours_depuis_publication': 8,
            'vendeur_idx': 2,  # Karim Dubois
            'bien_idx': 8      # Rue de la République
        },
        # Annonces rejetées (avec motifs variés)
        {
            'titre': 'Appartement luxe vue sur mer',
            'description': 'Exceptionnel appartement de 4 chambres avec terrasse panoramique et vue directe sur la mer Méditerranée. Finitions haut de gamme.',
            'prix': 25000000.0,
            'statut': 'REJETEE',
            'jours_depuis_publication': 5,
            'vendeur_idx': 0,  # Ahmed Benali
            'bien_idx': 9      # Résidence El Riadh
        },
        {
            'titre': 'Fermette à rénover',
            'description': 'Ancienne fermette en pierre à rénover entièrement, sur terrain de 2000m². Potentiel énorme pour création de gîtes ou résidence secondaire.',
            'prix': 9000000.0,
            'statut': 'REJETEE',
            'jours_depuis_publication': 12,
            'vendeur_idx': 1,  # Fatima Zahraoui
            'bien_idx': 6      # Route nationale 5
        },
        # Annonces en brouillon (en cours de préparation par le vendeur)
        {
            'titre': 'Studio étudiant près du CROUS',
            'description': 'Studio meublé de 30m² idéal pour étudiant, comprenant kitchenette équipée, salle de bain séparée et balcon.',
            'prix': 1800000.0,
            'statut': 'BROUILLON',
            'jours_depuis_publication': 0,  # Aujourd'hui
            'vendeur_idx': 2,  # Karim Dubois
            'bien_idx': 2      # 78 Rue Larbi Ben Mhidi
        },
        {
            'titre': 'Loft industriel réhabilité',
            'description': 'Loft de 180m² dans ancienne usine réhabilitée, avec poutres apparentes et énorme hauteur sous plafond. Parking privé inclus.',
            'prix': 12000000.0,
            'statut': 'BROUILLON',
            'jours_depuis_publication': 0,  # Aujourd'hui
            'vendeur_idx': 0,  # Ahmed Benali
            'bien_idx': 4      # Chemin des Pins
        }
    ]

    ids_annonces = []

    try:
        for annonce_data in annonces_test:
            # Exécuter la requête une seule fois
            curseur.execute(
                "SELECT id FROM ANNONCE WHERE titre = ?",
                (annonce_data['titre'],)
            )
            result = curseur.fetchone()

            if result is None:
                # Calculer la date de publication basée sur les jours depuis publication
                date_publi = (datetime.now() - timedelta(days=annonce_data['jours_depuis_publication'])).date()

                # Insérer l'annonce
                curseur.execute(
                    """
                    INSERT INTO ANNONCE
                    (id_vendeur, id_bien, titre, description, prix, statut, datePubli)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ids_vendeurs[annonce_data['vendeur_idx']],
                        ids_biens[annonce_data['bien_idx']],
                        annonce_data['titre'],
                        annonce_data['description'],
                        annonce_data['prix'],
                        annonce_data['statut'],
                        date_publi
                    )
                )
                id_annonce = curseur.lastrowid
                ids_annonces.append(id_annonce)

                # Créer des médias factices (photos) pour certaines annonces
                # On ajoute des photos seulement aux annonces EN_ATTENTE et PUBLIEE pour plus de réalisme
                if annonce_data['statut'] in ('EN_ATTENTE', 'PUBLIEE'):
                    nb_photos = 3 if annonce_data['statut'] == 'PUBLIEE' else 2  # Plus de photos pour les publiées

                    for i in range(nb_photos):
                        # Générer un nom de fichier factice
                        extension = 'jpg' if i % 2 == 0 else 'png'
                        nom_fichier = f"{uuid.uuid4().hex}.{extension}"
                        chemin_relatif = os.path.join('static', 'uploads', nom_fichier)

                        # Insérer dans MEDIA
                        curseur.execute(
                            """
                            INSERT INTO MEDIA (id_annonce, url, type, ordre)
                            VALUES (?, ?, ?, ?)
                            """,
                            (id_annonce, chemin_relatif, 'image', i)
                        )

                print(f"[OK] Annonce créée : {annonce_data['titre']} ({annonce_data['statut']})")
            else:
                # Utiliser le résultat déjà récupéré
                id_annonce = result['id']
                ids_annonces.append(id_annonce)
                print(f"[INFO] Annonce existante : {annonce_data['titre']} ({annonce_data['statut']})")

        connexion.commit()
        print(f"\n[OK] {len(ids_annonces)} annonces créées")

        # Créer les compteurs associés aux annonces
        print("\n  Création des compteurs de statistiques...")
        for id_annonce in ids_annonces:
            # Vérifier si le compteur existe déjà
            curseur.execute(
                "SELECT id FROM COMPTEUR WHERE id_annonce = ?",
                (id_annonce,)
            )
            if curseur.fetchone() is None:
                # Générer des statistiques réalistes
                vues = 50 + (id_annonce % 10) * 20  # Entre 50 et 230 vues
                contacts = 5 + (id_annonce % 5) * 2   # Entre 5 et 15 contacts
                prixs = 10 + (id_annonce % 8) * 3     # Entre 10 et 31 consultations de prix
                taux_conversion = (contacts / vues * 100) if vues > 0 else 0

                curseur.execute(
                    """
                    INSERT INTO COMPTEUR
                    (id_annonce, vues, contacts, prixs, tauxConversion)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (id_annonce, vues, contacts, prixs, round(taux_conversion, 2))
                )

        connexion.commit()
        print("[OK] Compteurs créés pour toutes les annonces")

    except sqlite3.Error as erreur:
        print(f"\n[ERREUR] Lors de la création des annonces : {erreur}")
        connexion.rollback()
        ids_annonces = []
    finally:
        connexion.close()

    return ids_annonces


def creer_historique_modération(ids_annonces):
    """
    Crée quelques entrées dans la table SIGNAL_DECISION pour l'historique de modération.
    """
    print("\n" + "=" * 55)
    print("  Création de l'historique de modération")
    print("=" * 55)

    connexion = get_db()
    curseur = connexion.cursor()

    # Récupérer l'ID de l'admin par défaut (créé par init_db.py)
    curseur.execute("SELECT id_utilisateur FROM ADMIN LIMIT 1")
    admin_result = curseur.fetchone()

    if admin_result is None:
        print("[!] Aucun admin trouvé. Ignorer la création d'historique de modération.")
        connexion.close()
        return []

    id_admin = admin_result['id_utilisateur']

    # Décisions de modération factices (seulement pour certaines annonces rejetées)
    decisions_test = [
        {
            'annonce_idx': 6,  # Annonce rejetée : Appartement luxe vue sur mer
            'decision': 'REJETEE',
            'motif': 'Photos non conformes - manque de photos des pièces principales'
        },
        {
            'annonce_idx': 7,  # Annonce rejetée : Fermette à rénover
            'decision': 'REJETEE',
            'motif': 'Description insuffisante - préciser l\'état exact des travaux nécessaires'
        }
    ]

    try:
        for decision_data in decisions_test:
            id_annonce = ids_annonces[decision_data['annonce_idx']]

            # Exécuter la requête une seule fois
            curseur.execute(
                "SELECT id FROM SIGNAL_DECISION WHERE id_annonce = ?",
                (id_annonce,)
            )
            result = curseur.fetchone()

            if result is None:
                curseur.execute(
                    """
                    INSERT INTO SIGNAL_DECISION
                    (id_annonce, id_admin, decision, motif, dateDecision)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        id_annonce,
                        id_admin,
                        decision_data['decision'],
                        decision_data['motif'],
                        datetime.now()
                    )
                )
                print(f"[OK] Décision de modération créée pour l'annonce ID {id_annonce}")

        connexion.commit()
        print("[OK] Historique de modération créé")

    except sqlite3.Error as erreur:
        print(f"\n[ERREUR] Lors de la création de l'historique de modération : {erreur}")
        connexion.rollback()
    finally:
        connexion.close()


def verifier_donnees_creees():
    """
    Affiche un résumé des données créées pour vérification.
    """
    print("\n" + "=" * 55)
    print("  Vérification des données créées")
    print("=" * 55)

    connexion = get_db()
    curseur = connexion.cursor()

    try:
        # Compter les utilisateurs par rôle
        curseur.execute("""
            SELECT role, COUNT(*) as nb
            FROM UTILISATEUR
            GROUP BY role
        """)
        roles = curseur.fetchall()
        print("Utilisateurs par rôle :")
        for role in roles:
            print(f"  - {role['role']} : {role['nb']}")

        # Compter les biens par type
        curseur.execute("""
            SELECT type, COUNT(*) as nb
            FROM BIEN_IMMOBILIER
            GROUP BY type
        """)
        types = curseur.fetchall()
        print("\nBiens immobiliers par type :")
        for type_bien in types:
            print(f"  - {type_bien['type']} : {type_bien['nb']}")

        # Compter les annonces par statut
        curseur.execute("""
            SELECT statut, COUNT(*) as nb
            FROM ANNONCE
            GROUP BY statut
        """)
        statuts = curseur.fetchall()
        print("\nAnnonces par statut :")
        for statut in statuts:
            print(f"  - {statut['statut']} : {statut['nb']}")

        # Compter les médias
        curseur.execute("SELECT COUNT(*) as nb FROM MEDIA")
        nb_media = curseur.fetchone()['nb']
        print(f"\nMédias (photos) : {nb_media}")

        # Compter les décisions de modération
        curseur.execute("SELECT COUNT(*) as nb FROM SIGNAL_DECISION")
        nb_decisions = curseur.fetchone()['nb']
        print(f"Décisions de modération : {nb_decisions}")

    except sqlite3.Error as erreur:
        print(f"[ERREUR] Lors de la vérification : {erreur}")
    finally:
        connexion.close()


def main():
    """
    Fonction principale qui orchestre la création de toutes les données de test.
    """
    print("SEED_DATA.PY - Peuplement de la base de données avec des données de test")
    print("=" * 70)
    print("Ce script va créer :")
    print("- 3 vendeurs (particuliers et agences)")
    print("- 2 acheteurs (avec budgets variés)")
    print("- 10 biens immobiliers (appartements, maisons, terrains, commerciaux)")
    print("- 10 annonces (avec statuts variés : BROUILLON, EN_ATTENTE, PUBLIEE, REJETEE)")
    print("- Des photos factices pour les annonces EN_ATTENTE et PUBLIEE")
    print("- Des compteurs de statistiques pour chaque annonce")
    print("- Quelques décisions de modération factices")
    print("=" * 70)

    # Étape 1 : Créer les utilisateurs (vendeurs et acheteurs)
    ids_vendeurs, ids_acheteurs = creer_vendeurs_et_acheteurs()

    # Étape 2 : Créer les biens immobiliers
    ids_biens = creer_biens_immobiliers()

    # Étape 3 : Créer les annonces et les médias associés
    if ids_vendeurs and ids_biens:
        ids_annonces = creer_annonces_et_media(ids_vendeurs, ids_biens)

        # Étape 4 : Créer l'historique de modération
        if ids_annonces:
            creer_historique_modération(ids_annonces)

    # Étape 5 : Vérifier les données créées
    verifier_donnees_creees()

    print("\n" + "=" * 70)
    print("PEUPLEMENT TERMINÉ AVEC SUCCÈS !")
    print("=" * 70)
    print("\nVous pouvez maintenant :")
    print("1. Lancer l'application avec : python app.py")
    print("2. Vous connecter avec les comptes de test :")
    print("   - Vendeur : ahmed.benali@email.dz / vendeur123")
    print("   - Acheteur : yacine.merabet@email.dz / acheteur123")
    print("   - Admin : admin@immo.dz / admin123 (déjà créé par init_db.py)")
    print("3. Tester les fonctionnalités : publication, recherche, modération, etc.")
    print("\nNote : Les photos sont factices (chemins vers des fichiers qui n'existent pas)")
print("       mais cela suffit pour tester l'affichage et les fonctionnalités backend.")


# Point d'entrée du script
if __name__ == "__main__":
    main()