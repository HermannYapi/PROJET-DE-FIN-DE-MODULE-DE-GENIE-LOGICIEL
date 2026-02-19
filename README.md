# Gestion de la Bibliotheque de Plateau

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

## Standard institutionnel (universite / ville)
- Validation administrative des usagers (`approved` / `approved_on`)
- Numero de carte usager (`card_number`)
- Metadonnees bibliographiques standard (ISBN, editeur, annee, langue, categorie)
- Politique de pret configurable (limites/durees via variables d environnement)
- Journal d audit des actions critiques (`/admin/audit`)

### Variables d environnement
- `SECRET_KEY` (obligatoire en production)
- `ADMIN_PASSWORD` (obligatoire en production)
- `MAX_ACTIVE_LOANS` (defaut: 5)
- `DEFAULT_LOAN_DAYS` (defaut: 14)
- `DEFAULT_RESERVATION_DAYS` (defaut: 7)
- `LOAN_EXTENSION_DAYS` (defaut: 7)
- `RESERVATION_EXTENSION_DAYS` (defaut: 7)
