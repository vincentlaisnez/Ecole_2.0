# 1. Créer un environnement virtuel (recommandé)
python3 -m venv venv
source venv/bin/activate  # Sur Linux/Mac
# ou
venv\Scripts\activate  # Sur Windows

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Installer les dépendances système (Linux/Debian/Ubuntu)
sudo apt-get update
sudo apt-get install libttspico-utils  # Pour la meilleure qualité vocale

# OU en fallback si Pico TTS n'est pas disponible :
sudo apt-get install espeak

# 4. Lancer l'application
python main.py