# iot-data-pipeline
Une solution de pipeline de données d'Internet des Objets (IoT) pour surveiller les animaux et leur état de santé

# Workflow général

![Aperçu du projet](images/flow.png)

## Description
Ce projet IoT est une solution de pipeline de données d'Internet des Objets (IoT) conçue pour connecter et surveiller les animaux ainsi que leur état de santé. Le système permet fournir des diverses données en temps réel  et d'assurer une gestion efficace de la santé animale.
Dans le cadre de notre projet, on travail dans la section numéro 2 du workflow général

![Aperçu du projet](images/flow_project.png)

## Fonctionnalités
- Données pour surveillance en temps réel de l'état de santé des animaux
- Collecte et analyse des données de santé
- Données d'activité pour des fonctionalités de notification et alertes en cas d'anomalies
- Interface utilisateur intuitive webhook pour la gestion des api qui récupère les données

## Outils et Technologies
Le projet utilise les technologies et outils suivants :
- **Langages de programmation** : Python, JavaScript, HTML, css
- **Frameworks et bibliothèques** : Fastapi, Django, jquery, datatable, bootstrap shapely 
- **Bases de données** : PostgreSQL, SQL
- **Formats de données** : JSON, JWT
- **Conteneurisation** : Docker
- **Plateforme de télématique** : Digital Matter, Oem server, Telematics Guru

## Installation
Pour installer et exécuter ce projet localement, veuillez suivre les étapes ci-dessous :

1. Clonez le dépôt :
    ```bash
    git clone https://github.com/votre-utilisateur/votre-repo.git
    ```

2. Accédez au répertoire du projet :
    ```bash
    cd votre-repo
    ```

3. Installez les dépendances :
    ```bash
    pip install -r requirements.txt
    ```

4. Configurez les bases de données (MongoDB et PostgreSQL) et mettez à jour les paramètres de connexion dans les fichiers de configuration.

5. Exécutez les migrations de la base de données :
    ```bash
    python manage.py migrate
    ```

6. Lancez l'application :
    ```bash
    python manage.py runserver
    ```

7. Accédez à l'application via votre navigateur à l'adresse :
    ```
    http://127.0.0.1:8000
    ```

## Utilisation
1. Inscrivez-vous et connectez-vous à l'application.
2. Ajoutez les informations de vos animaux.
3. Configurez les capteurs IoT pour collecter les données de santé.
4. Surveillez l'état de santé des animaux en temps réel via le tableau de bord.
5. Recevez des notifications en cas d'anomalies ou de problèmes de santé.

## Contribution
Les contributions sont les bienvenues ! Si vous souhaitez contribuer, veuillez créer une branche à partir de `main`, apporter vos modifications, puis soumettre une pull request.

## Licence
Ce projet est sous licence MIT. Pour plus de détails, veuillez consulter le fichier `LICENSE`.

## Auteurs
- [Votre Nom](https://github.com/votre-utilisateur)

Merci de votre intérêt pour ce projet ! N'hésitez pas à me contacter pour toute question ou suggestion.
