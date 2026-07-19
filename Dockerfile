FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances système légères nécessaires à l'exécution de curl_cffi
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie uniquement le fichier des dépendances dans un premier temps pour optimiser le cache Docker
COPY requirements.txt .

# Installation des paquets directement dans le conteneur (plus besoin de .venv ici !)
RUN pip install --no-cache-dir -r requirements.txt

# Copie le script de scraping principal
COPY scrap-url.py .

# On expose le port sur lequel l'API FastAPI va écouter
EXPOSE 8000

# Lancement du serveur uvicorn pour écouter les requêtes HTTP de ton Quarkus
CMD ["uvicorn", "scrap-url:app", "--host", "0.0.0.0", "--port", "8000"]