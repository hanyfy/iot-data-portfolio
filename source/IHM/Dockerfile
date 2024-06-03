# Utilisez une image de base avec Python
FROM python:3.9

# Copiez le contenu de votre application Django dans le conteneur
COPY . /app/IHM

# Définissez le répertoire de travail
WORKDIR /app/IHM

# Installez les dépendances Python depuis le fichier requirements.txt
RUN pip install -r requirements.txt

# Utilisez une variable d'environnement pour définir le port par défaut
ENV DJANGO_PORT=8085

# Exécutez la commande pour démarrer le serveur Django
CMD python alpes_echo/manage.py runserver 0.0.0.0:$DJANGO_PORT




