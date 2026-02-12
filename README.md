# Système de gestion de bibliothèque (mini-app)

Ce dépôt contient une application Python minimaliste pour gérer une bibliothèque : emprunts, retours, réservations et gestion des usagers.

Installation rapide:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py
python app.py
```

L'application démarre sur http://127.0.0.1:5000

Points utiles:
- Initialiser la base: exécuter `init_db.py` (créé et seed des données).
- API JSON disponibles:
	- `GET /api/books` — liste des livres
	- `GET /api/users` — liste des usagers
	- `GET /api/loans` — liste des emprunts
	- `GET /api/reservations` — liste des réservations
	- `POST /api/borrow` — emprunter (JSON: {"user_id":1,"book_id":2})
	- `POST /api/reserve` — réserver (JSON: {"user_id":1,"book_id":2})

Fichiers principaux:
- [app.py](app.py)
- [models.py](models.py)
- [requirements.txt](requirements.txt)
- [init_db.py](init_db.py)
- [templates](templates) : interfaces HTML
- [static/style.css](static/style.css)



# Code administracteur: Hermann48