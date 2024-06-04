# iot-data-pipeline
Une solution de pipeline de données d'Internet des Objets (IoT) pour surveiller les animaux et leur état de santé

# Workflow général

![Aperçu du projet](images/flow.png)

## Description
Ce projet IoT est une solution de pipeline de données d'Internet des Objets (IoT) conçue pour connecter et surveiller les animaux ainsi que leur état de santé. Le système permet fournir des diverses données en temps réel  et d'assurer une gestion efficace de la santé animale.
Dans le cadre de notre projet, on travail dans la section numéro 2 du workflow général

![Aperçu du projet](images/flow_project.png)

## Fonctionnalités
- Collecte et analyse des données de santé
- Données pour surveillance en temps réel des animaux
- Données d'activités des animaux  pour surveillance de l'état de santé et aussi pour des fonctionalités de notification et alertes en cas d'anomalies
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
    git clone -b main --depth=1  https://github.com/hanyfy/iot-data-portfolio.git
    ```

2. Accédez au répertoire du projet :
    ```bash
    cd iot-data-portfolio/source
    ```

3. Installez les dépendances :
    ```bash
    docker-compose up --build
    ```

4. Installer les tables du base de données (PostgreSQL).
    ```
    Se connecter sur la base de données avec PgAdmin v4 
        POSTGRES_HOST=localhost
        POSTGRES_PORT=5432
        POSTGRES_USER=root
        POSTGRES_PASSWORD=F7wB2nK9v
    Exécuter les fichiers sql    
        BDD/iot_table.sql
        BDD/iot_table_v2.sql
    ```    
5. Mettez à jour les paramètres de connexion dans les fichiers de configuration.
    API/config/config.json


8. Accédez à l'application via votre navigateur à l'adresse :
    ```
    http://127.0.0.1:8086/docs (pour la documentation de l'api)
    http://127.0.0.1:8085 (pour l'ihm de webhook)
    ```

## Utilisation
1. Creer-vous un acces utilisateur sur django et connectez-vous à l'application webhook.
3. Configurez votre api qui recoit les données à l'application webhook.
![Aperçu du projet](images/0-ihm.PNG)

## Contribution
Les contributions sont les bienvenues ! Si vous souhaitez contribuer, veuillez créer une branche à partir de `main`, apporter vos modifications, puis soumettre une pull request.

## Licence
Ce projet est sous licence MIT. Pour plus de détails, veuillez consulter le fichier `LICENSE`.

## Auteurs
- [Votre Nom](https://github.com/hanyfy)
ramamonjisoafy@gmail.com
Merci de votre intérêt pour ce projet ! N'hésitez pas à me contacter pour toute question ou suggestion.
