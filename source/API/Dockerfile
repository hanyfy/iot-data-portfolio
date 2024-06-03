# Utilisez une image de base avec Python
FROM python:3.9

# Copiez le contenu de votre application Django dans le conteneur
COPY . /app/API

# Définissez le répertoire de travail
WORKDIR /app/API

# Installez les dépendances Python depuis le fichier requirements.txt
RUN pip install -r requirements.txt

# Utilisez une variable d'environnement pour définir le port par défaut
ENV API_PORT=8085

# Exécutez la commande pour démarrer le serveur Django
CMD ["python3", "main.py"]