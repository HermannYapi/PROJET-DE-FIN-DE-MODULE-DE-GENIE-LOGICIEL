from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from models import db, User, Book, Loan, Reservation, AuditLog
from datetime import datetime, timedelta
from functools import wraps
import os
import json
import secrets
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Admin password (à changer en production)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Hermann48')
LOAN_EXTENSION_DAYS = int(os.environ.get('LOAN_EXTENSION_DAYS', '7'))
RESERVATION_EXTENSION_DAYS = int(os.environ.get('RESERVATION_EXTENSION_DAYS', '7'))
MAX_ACTIVE_LOANS = int(os.environ.get('MAX_ACTIVE_LOANS', '5'))
DEFAULT_LOAN_DAYS = int(os.environ.get('DEFAULT_LOAN_DAYS', '14'))
DEFAULT_RESERVATION_DAYS = int(os.environ.get('DEFAULT_RESERVATION_DAYS', '7'))

db.init_app(app)

# Décorateur pour vérifier si l'utilisateur est admin
def login_required_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            flash('Vous devez être connecté en tant qu\'administrateur', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Veuillez vous connecter en tant qu usager', 'warning')
            return redirect(url_for('user_login'))
        user = User.query.get(user_id)
        if not user:
            session.pop('user_id', None)
            flash('Compte usager introuvable', 'danger')
            return redirect(url_for('user_login'))
        if not user.is_active:
            flash('Compte usager inactif. Contactez l administration', 'danger')
            return redirect(url_for('user_login'))
        if not user.approved:
            flash('Compte en attente de validation par l administration', 'warning')
            return redirect(url_for('user_pending'))
        return f(*args, **kwargs)
    return decorated_function

def sqlite_add_column_if_missing(table_name: str, column_name: str, ddl_fragment: str):
    cols = [row[1] for row in db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()]
    if column_name not in cols:
        db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_fragment}"))
        db.session.commit()

def generate_card_number() -> str:
    year = datetime.utcnow().year
    return f"CARD-{year}-{secrets.token_hex(4).upper()}"

def log_action(actor_type: str, actor_id: int | None, action: str, entity_type: str, entity_id: int | None, payload: dict | None = None):
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=json.dumps(payload, ensure_ascii=True) if payload else None
    )
    db.session.add(entry)

# Create tables and seed minimal data safely using app context.
# This avoids relying on Flask decorator methods that may not be present
# in all runtime environments when the module is imported.
with app.app_context():
    db.create_all()
    user_columns = [row[1] for row in db.session.execute(text("PRAGMA table_info(user)")).fetchall()]
    approved_column_added = False
    if 'approved' not in user_columns:
        sqlite_add_column_if_missing('user', 'approved', 'BOOLEAN DEFAULT 0')
        approved_column_added = True
    sqlite_add_column_if_missing('user', 'approved_on', 'DATETIME')
    sqlite_add_column_if_missing('user', 'card_number', 'VARCHAR(32)')
    sqlite_add_column_if_missing('user', 'affiliation', 'VARCHAR(80)')
    sqlite_add_column_if_missing('user', 'phone', 'VARCHAR(32)')
    sqlite_add_column_if_missing('user', 'is_active', 'BOOLEAN DEFAULT 1')
    if approved_column_added:
        db.session.execute(text("UPDATE user SET approved = 1"))
    else:
        db.session.execute(text("UPDATE user SET approved = 1 WHERE approved IS NULL"))
    db.session.execute(text("UPDATE user SET is_active = 1 WHERE is_active IS NULL"))
    db.session.execute(text("UPDATE user SET affiliation = 'Public' WHERE affiliation IS NULL"))
    db.session.execute(text("UPDATE user SET card_number = 'CARD-' || strftime('%Y','now') || '-' || printf('%08X', id) WHERE card_number IS NULL"))
    db.session.execute(text("UPDATE user SET approved_on = registered_on WHERE approved = 1 AND approved_on IS NULL"))
    db.session.commit()
    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_card_number_unique ON user(card_number)"))
    db.session.commit()
    sqlite_add_column_if_missing('book', 'isbn', 'VARCHAR(20)')
    sqlite_add_column_if_missing('book', 'publisher', 'VARCHAR(200)')
    sqlite_add_column_if_missing('book', 'publication_year', 'INTEGER')
    sqlite_add_column_if_missing('book', 'language', 'VARCHAR(60)')
    sqlite_add_column_if_missing('book', 'category', 'VARCHAR(120)')
    db.session.execute(text("UPDATE book SET language = 'Français' WHERE language IS NULL"))
    db.session.execute(text("UPDATE book SET category = 'General' WHERE category IS NULL"))
    db.session.commit()
    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_book_isbn_unique ON book(isbn)"))
    db.session.commit()
    sqlite_add_column_if_missing('loan', 'returned_on', 'DATETIME')
    # Lightweight SQLite migration for Reservation.expires_on.
    sqlite_add_column_if_missing('reservation', 'expires_on', 'DATETIME')
    db.session.execute(text(f"UPDATE reservation SET expires_on = datetime(reserved_on, '+{RESERVATION_EXTENSION_DAYS} days') WHERE expires_on IS NULL"))
    db.session.commit()
    # seed minimal data if empty
    if Book.query.count() == 0:
        b1 = Book(title='Le Petit Prince', author='Antoine de Saint-Exupéry', total_copies=3)
        b2 = Book(title='1984', author='George Orwell', total_copies=2)
        db.session.add_all([b1, b2])
        db.session.commit()

@app.route('/')
def index():
    books = Book.query.all()
    total_books = Book.query.count()
    total_users = User.query.count()
    active_loans = Loan.query.filter_by(returned=False).count()
    return render_template('index.html', 
                         books=books,
                         total_books=total_books,
                         total_users=total_users,
                         active_loans=active_loans)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin'] = True
            flash('✓ Connecté en tant qu\'administrateur', 'success')
            return redirect(request.referrer or url_for('users'))
        else:
            flash('❌ Mot de passe incorrect', 'danger')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('✓ Déconnecté', 'success')
    return redirect(url_for('index'))

@app.route('/usager/inscription', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        if not name or not email:
            flash('Nom et email obligatoires', 'danger')
            return redirect(url_for('user_register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.approved:
                flash('Compte deja valide. Connectez-vous avec votre email', 'success')
                return redirect(url_for('user_login'))
            flash('Inscription deja recue. En attente de validation admin', 'warning')
            return redirect(url_for('user_pending', email=email))

        new_user = User(
            name=name,
            email=email,
            card_number=generate_card_number(),
            affiliation='Public',
            approved=False,
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()
        log_action('user', new_user.id, 'REGISTER_REQUESTED', 'user', new_user.id, {'email': new_user.email})
        db.session.commit()
        flash('Demande d inscription enregistree. Validation admin requise', 'success')
        return redirect(url_for('user_pending', email=email))
    return render_template('user_register.html')

@app.route('/usager/connexion', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Email obligatoire', 'danger')
            return redirect(url_for('user_login'))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Aucun compte trouve. Faites d abord une inscription', 'warning')
            return redirect(url_for('user_register'))
        if not user.is_active:
            flash('Compte inactif. Contactez l administration', 'danger')
            return redirect(url_for('user_login'))

        session['user_id'] = user.id
        if not user.approved:
            flash('Compte en attente de validation par l administration', 'warning')
            return redirect(url_for('user_pending'))

        flash('Connexion usager reussie', 'success')
        return redirect(url_for('user_portal'))
    return render_template('user_login.html')

@app.route('/usager/deconnexion')
def user_logout():
    session.pop('user_id', None)
    flash('Vous etes deconnecte', 'success')
    return redirect(url_for('index'))

@app.route('/usager/attente')
def user_pending():
    user = None
    email = request.args.get('email', '').strip().lower()
    if email:
        user = User.query.filter_by(email=email).first()
    user_id = session.get('user_id')
    if not user and user_id:
        user = User.query.get(user_id)
    return render_template('user_pending.html', user=user)

@app.route('/usager')
@user_required
def user_portal():
    user = User.query.get(session['user_id'])
    books = Book.query.order_by(Book.title.asc()).all()
    return render_template('user_portal.html', user=user, books=books)

@app.route('/usager/emprunter', methods=['POST'])
@user_required
def user_borrow():
    user = User.query.get(session['user_id'])
    book_id = int(request.form['book_id'])
    book = Book.query.get_or_404(book_id)
    if book.available_copies() <= 0:
        flash('Aucune copie disponible', 'danger')
        return redirect(url_for('user_portal'))
    if user.active_loans_count() >= MAX_ACTIVE_LOANS:
        flash('Limite d emprunts atteinte', 'danger')
        return redirect(url_for('user_portal'))
    loan = Loan(user_id=user.id, book_id=book.id, due_date=datetime.utcnow() + timedelta(days=DEFAULT_LOAN_DAYS))
    db.session.add(loan)
    db.session.commit()
    log_action('user', user.id, 'BORROW_CREATED', 'loan', loan.id, {'book_id': book.id})
    db.session.commit()
    flash('Emprunt enregistre', 'success')
    return redirect(url_for('user_portal'))

@app.route('/usager/reserver', methods=['POST'])
@user_required
def user_reserve():
    user = User.query.get(session['user_id'])
    book_id = int(request.form['book_id'])
    book = Book.query.get_or_404(book_id)
    if Reservation.query.filter_by(user_id=user.id, book_id=book.id, active=True).first():
        flash('Reservation deja existante', 'warning')
        return redirect(url_for('user_portal'))
    r = Reservation(user_id=user.id, book_id=book.id, expires_on=datetime.utcnow() + timedelta(days=DEFAULT_RESERVATION_DAYS))
    db.session.add(r)
    db.session.commit()
    log_action('user', user.id, 'RESERVATION_CREATED', 'reservation', r.id, {'book_id': book.id})
    db.session.commit()
    flash('Reservation enregistree', 'success')
    return redirect(url_for('user_portal'))

@app.route('/books')
def list_books():
    books = Book.query.all()
    current_user = None
    user_id = session.get('user_id')
    if user_id:
        current_user = User.query.get(user_id)
    user_can_transact = bool(current_user and current_user.approved and current_user.is_active)
    user_can_view_details = bool(session.get('admin') or user_can_transact)
    return render_template(
        'books.html',
        books=books,
        current_user=current_user,
        user_can_transact=user_can_transact,
        user_can_view_details=user_can_view_details
    )

@app.route('/add_book', methods=['GET', 'POST'])
@login_required_admin
def add_book():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        total_copies = request.form.get('total_copies', '1')
        
        if not title or not author:
            flash('Le titre et l\'auteur sont obligatoires', 'danger')
            return redirect(url_for('add_book'))
        
        try:
            total_copies = int(total_copies)
            if total_copies < 1:
                raise ValueError
        except ValueError:
            flash('Le nombre de copies doit être un nombre entier positif', 'danger')
            return redirect(url_for('add_book'))
        
        # Vérifier si le livre existe déjà
        existing_book = Book.query.filter_by(title=title, author=author).first()
        if existing_book:
            existing_book.total_copies += total_copies
            db.session.commit()
            flash(f'✓ Livre existant mise à jour: {total_copies} copie(s) ajoutée(s)', 'success')
        else:
            book = Book(title=title, author=author, total_copies=total_copies)
            db.session.add(book)
            db.session.commit()
            flash(f'✓ Nouvel ouvrage ajouté: {title}', 'success')
        
        return redirect(url_for('book_detail', book_id=book.id))
    
    # GET request - afficher le formulaire avec les derniers livres
    recent_books = Book.query.order_by(Book.id.desc()).limit(5).all()
    return render_template('add_book.html', recent_books=recent_books)

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return redirect(url_for('index'))
    books = Book.query.filter(
        (Book.title.ilike(f'%{q}%')) | 
        (Book.author.ilike(f'%{q}%'))
    ).all()
    return render_template('search.html', query=q, books=books)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    is_admin = bool(session.get('admin'))

    if is_admin:
        all_users = User.query.filter_by(approved=True).all()
        return render_template('book_detail.html', book=book, all_users=all_users, is_admin=True, viewer_user=None)

    user_id = session.get('user_id')
    if not user_id:
        flash('Connectez-vous avec votre email pour acceder aux details, ou inscrivez-vous', 'warning')
        return redirect(url_for('user_login'))

    viewer_user = User.query.get(user_id)
    if not viewer_user:
        session.pop('user_id', None)
        flash('Compte usager introuvable', 'danger')
        return redirect(url_for('user_login'))
    if not viewer_user.is_active:
        flash('Compte usager inactif. Contactez l administration', 'danger')
        return redirect(url_for('user_login'))
    if not viewer_user.approved:
        flash('Compte en attente de validation par l administration', 'warning')
        return redirect(url_for('user_pending'))

    return render_template('book_detail.html', book=book, all_users=[], is_admin=False, viewer_user=viewer_user)

def book_to_dict(b: Book):
    return {
        'id': b.id,
        'title': b.title,
        'author': b.author,
        'isbn': b.isbn,
        'publisher': b.publisher,
        'publication_year': b.publication_year,
        'language': b.language,
        'category': b.category,
        'total_copies': b.total_copies,
        'available_copies': b.available_copies()
    }

def user_to_dict(u: User):
    return {
        'id': u.id,
        'name': u.name,
        'email': u.email,
        'card_number': u.card_number,
        'affiliation': u.affiliation,
        'registered_on': u.registered_on.isoformat(),
        'approved': u.approved,
        'is_active': u.is_active,
        'active_loans': u.active_loans_count()
    }

def loan_to_dict(l: Loan):
    return {
        'id': l.id,
        'user_id': l.user_id,
        'book_id': l.book_id,
        'borrowed_on': l.borrowed_on.isoformat(),
        'due_date': l.due_date.isoformat() if l.due_date else None,
        'returned_on': l.returned_on.isoformat() if l.returned_on else None,
        'returned': l.returned
    }

def reservation_to_dict(r: Reservation):
    return {
        'id': r.id,
        'user_id': r.user_id,
        'book_id': r.book_id,
        'reserved_on': r.reserved_on.isoformat(),
        'expires_on': r.expires_on.isoformat() if r.expires_on else None,
        'active': r.active
    }

@app.route('/api/books')
def api_books():
    books = Book.query.all()
    return jsonify([book_to_dict(b) for b in books])

@app.route('/api/users')
def api_users():
    users = User.query.all()
    return jsonify([user_to_dict(u) for u in users])

@app.route('/api/loans')
def api_loans():
    loans = Loan.query.all()
    return jsonify([loan_to_dict(l) for l in loans])

@app.route('/api/stats')
def api_stats():
    total_books = Book.query.count()
    total_users = User.query.count()
    active_loans = Loan.query.filter_by(returned=False).count()
    total_reservations = Reservation.query.filter_by(active=True).count()
    return jsonify({
        'total_books': total_books,
        'total_users': total_users,
        'active_loans': active_loans,
        'total_reservations': total_reservations
    })

@app.route('/api/latest-books')
def api_latest_books():
    books = Book.query.limit(6).all()
    return jsonify([book_to_dict(b) for b in books])

@app.route('/api/borrow', methods=['POST'])
def api_borrow():
    data = request.get_json() or {}
    try:
        user_id = int(data.get('user_id'))
        book_id = int(data.get('book_id'))
    except Exception:
        return jsonify({'error': 'user_id and book_id are required integers'}), 400
    user = User.query.get(user_id)
    book = Book.query.get(book_id)
    if not user or not book:
        return jsonify({'error': 'user or book not found'}), 404
    if not user.approved:
        return jsonify({'error': 'user is pending admin approval'}), 403
    if book.available_copies() <= 0:
        return jsonify({'error': 'no copies available'}), 400
    if user.active_loans_count() >= MAX_ACTIVE_LOANS:
        return jsonify({'error': 'user has reached loan limit'}), 400
    loan = Loan(user_id=user.id, book_id=book.id, due_date=datetime.utcnow() + timedelta(days=DEFAULT_LOAN_DAYS))
    db.session.add(loan)
    db.session.commit()
    return jsonify({'message': 'loan created', 'loan': loan_to_dict(loan)}), 201

@app.route('/api/reserve', methods=['POST'])
def api_reserve():
    data = request.get_json() or {}
    try:
        user_id = int(data.get('user_id'))
        book_id = int(data.get('book_id'))
    except Exception:
        return jsonify({'error': 'user_id and book_id are required integers'}), 400
    user = User.query.get(user_id)
    book = Book.query.get(book_id)
    if not user or not book:
        return jsonify({'error': 'user or book not found'}), 404
    if not user.approved:
        return jsonify({'error': 'user is pending admin approval'}), 403
    if Reservation.query.filter_by(user_id=user_id, book_id=book_id, active=True).first():
        return jsonify({'error': 'active reservation already exists'}), 400
    r = Reservation(user_id=user_id, book_id=book_id, expires_on=datetime.utcnow() + timedelta(days=DEFAULT_RESERVATION_DAYS))
    db.session.add(r)
    db.session.commit()
    return jsonify({'message': 'reservation created', 'reservation': reservation_to_dict(r)}), 201

@app.route('/users')
@login_required_admin
def users():
    users = User.query.order_by(User.approved.asc(), User.registered_on.asc()).all()
    return render_template('users.html', users=users)

@app.route('/register', methods=['GET', 'POST'])
@login_required_admin
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        if User.query.filter_by(email=email).first():
            flash('Email déjà utilisé', 'warning')
            return redirect(url_for('register'))
        u = User(
            name=name,
            email=email,
            card_number=generate_card_number(),
            affiliation='Staff',
            approved=True,
            approved_on=datetime.utcnow(),
            is_active=True
        )
        db.session.add(u)
        db.session.commit()
        log_action('admin', None, 'USER_CREATED_ADMIN', 'user', u.id, {'email': u.email})
        db.session.commit()
        flash('Utilisateur enregistré', 'success')
        return redirect(request.referrer or url_for('users'))
    return render_template('register_user.html')

@app.route('/profile/<int:user_id>')
@login_required_admin
def profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('profile.html', user=user)


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required_admin
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    active_loans = Loan.query.filter_by(user_id=user.id, returned=False).count()
    active_reservations = Reservation.query.filter_by(user_id=user.id, active=True).count()

    if active_loans > 0 or active_reservations > 0:
        flash('Suppression impossible: cet usager a des emprunts ou reservations actives', 'danger')
        return redirect(request.referrer or url_for('users'))

    Loan.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Reservation.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.delete(user)
    db.session.commit()
    log_action('admin', None, 'USER_DELETED', 'user', user_id, {'email': user.email})
    db.session.commit()

    flash('Usager supprime avec succes', 'success')
    return redirect(request.referrer or url_for('users'))

@app.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required_admin
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.approved:
        flash('Usager deja valide', 'warning')
        return redirect(request.referrer or url_for('admin'))
    user.approved = True
    user.approved_on = datetime.utcnow()
    db.session.commit()
    log_action('admin', None, 'USER_APPROVED', 'user', user.id, {'email': user.email})
    db.session.commit()
    flash('Usager valide avec succes', 'success')
    return redirect(request.referrer or url_for('admin'))


@app.route('/books/<int:book_id>/delete', methods=['POST'])
@login_required_admin
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)

    active_loans = Loan.query.filter_by(book_id=book.id, returned=False).count()
    active_reservations = Reservation.query.filter_by(book_id=book.id, active=True).count()

    if active_loans > 0 or active_reservations > 0:
        flash('Suppression impossible: ce livre a des emprunts ou reservations actives', 'danger')
        return redirect(url_for('list_books'))

    Loan.query.filter_by(book_id=book.id).delete(synchronize_session=False)
    Reservation.query.filter_by(book_id=book.id).delete(synchronize_session=False)
    db.session.delete(book)
    db.session.commit()
    log_action('admin', None, 'BOOK_DELETED', 'book', book_id, {'title': book.title})
    db.session.commit()

    flash('Livre supprime avec succes', 'success')
    return redirect(url_for('list_books'))

@app.route('/borrow', methods=['POST'])
@login_required_admin
def borrow():
    user_id = int(request.form['user_id'])
    book_id = int(request.form['book_id'])
    user = User.query.get_or_404(user_id)
    book = Book.query.get_or_404(book_id)
    if not user.approved:
        flash('Cet usager doit etre valide par l administration', 'danger')
        return redirect(request.referrer or url_for('admin'))
    if book.available_copies() <= 0:
        flash('Aucune copie disponible', 'danger')
        return redirect(request.referrer or url_for('admin'))
    if user.active_loans_count() >= MAX_ACTIVE_LOANS:
        flash('Limite d\'emprunts atteinte', 'danger')
        return redirect(request.referrer or url_for('admin'))
    loan = Loan(user_id=user.id, book_id=book.id, due_date=datetime.utcnow() + timedelta(days=DEFAULT_LOAN_DAYS))
    db.session.add(loan)
    db.session.commit()
    log_action('admin', None, 'BORROW_CREATED_ADMIN', 'loan', loan.id, {'user_id': user.id, 'book_id': book.id})
    db.session.commit()
    flash('Emprunt enregistré', 'success')
    return redirect(request.referrer or url_for('admin'))

@app.route('/return', methods=['POST'])
@login_required_admin
def return_book():
    loan_id = int(request.form['loan_id'])
    loan = Loan.query.get_or_404(loan_id)
    loan.returned = True
    loan.returned_on = datetime.utcnow()
    # after marking returned, try to fulfil next active reservation for this book
    book = loan.book
    db.session.commit()

    # check for active reservations ordered by date
    next_res = Reservation.query.filter_by(book_id=book.id, active=True).order_by(Reservation.reserved_on.asc()).first()
    if next_res and book.available_copies() > 0:
        # create loan for reserved user
        new_loan = Loan(user_id=next_res.user_id, book_id=book.id, due_date=datetime.utcnow() + timedelta(days=DEFAULT_LOAN_DAYS))
        next_res.active = False
        db.session.add(new_loan)
        db.session.commit()
        log_action('admin', None, 'LOAN_RETURNED_AND_RESERVATION_FULFILLED', 'loan', new_loan.id, {'source_loan_id': loan.id, 'reservation_id': next_res.id})
        db.session.commit()
        flash(f'Retour enregistré. Réservation de {next_res.user.name} convertie en emprunt.', 'success')
    else:
        log_action('admin', None, 'LOAN_RETURNED', 'loan', loan.id, None)
        db.session.commit()
        flash('Retour enregistré', 'success')
    return redirect(request.referrer or url_for('admin'))

@app.route('/reserve', methods=['POST'])
@login_required_admin
def reserve():
    user_id = int(request.form['user_id'])
    book_id = int(request.form['book_id'])
    user = User.query.get_or_404(user_id)
    if not user.approved:
        flash('Cet usager doit etre valide par l administration', 'danger')
        return redirect(request.referrer or url_for('admin'))
    if Reservation.query.filter_by(user_id=user_id, book_id=book_id, active=True).first():
        flash('Réservation existante', 'warning')
        return redirect(request.referrer or url_for('admin'))
    r = Reservation(user_id=user_id, book_id=book_id, expires_on=datetime.utcnow() + timedelta(days=DEFAULT_RESERVATION_DAYS))
    db.session.add(r)
    db.session.commit()
    log_action('admin', None, 'RESERVATION_CREATED_ADMIN', 'reservation', r.id, {'user_id': user_id, 'book_id': book_id})
    db.session.commit()
    flash('Réservation créée', 'success')
    return redirect(request.referrer or url_for('admin'))

@app.route('/cancel-loan/<int:loan_id>', methods=['POST'])
@login_required_admin
def cancel_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.returned:
        flash('Emprunt deja termine', 'warning')
        return redirect(request.referrer or url_for('admin'))
    loan.returned = True
    loan.returned_on = datetime.utcnow()
    db.session.commit()
    log_action('admin', None, 'LOAN_INTERRUPTED', 'loan', loan.id, None)
    db.session.commit()
    flash('Emprunt annule', 'success')
    return redirect(request.referrer or url_for('admin'))

@app.route('/cancel-reservation/<int:reservation_id>', methods=['POST'])
@login_required_admin
def cancel_reservation(reservation_id):
    res = Reservation.query.get_or_404(reservation_id)
    if not res.active:
        flash('Reservation deja terminee', 'warning')
        return redirect(request.referrer or url_for('admin'))
    res.active = False
    db.session.commit()
    log_action('admin', None, 'RESERVATION_INTERRUPTED', 'reservation', res.id, None)
    db.session.commit()
    flash('Reservation annulee', 'success')
    return redirect(request.referrer or url_for('admin'))

@app.route('/extend-loan/<int:loan_id>', methods=['POST'])
@login_required_admin
def extend_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.returned:
        flash('Impossible de prolonger un emprunt termine', 'danger')
        return redirect(request.referrer or url_for('admin'))
    base_due_date = loan.due_date or datetime.utcnow()
    loan.due_date = base_due_date + timedelta(days=LOAN_EXTENSION_DAYS)
    db.session.commit()
    log_action('admin', None, 'LOAN_EXTENDED', 'loan', loan.id, {'days': LOAN_EXTENSION_DAYS})
    db.session.commit()
    flash(f'Emprunt prolonge de {LOAN_EXTENSION_DAYS} jours', 'success')
    return redirect(request.referrer or url_for('admin'))

@app.route('/extend-reservation/<int:reservation_id>', methods=['POST'])
@login_required_admin
def extend_reservation(reservation_id):
    res = Reservation.query.get_or_404(reservation_id)
    if not res.active:
        flash('Impossible de prolonger une reservation terminee', 'danger')
        return redirect(request.referrer or url_for('admin'))
    now = datetime.utcnow()
    current_expiry = res.expires_on or now
    if current_expiry < now:
        current_expiry = now
    res.expires_on = current_expiry + timedelta(days=RESERVATION_EXTENSION_DAYS)
    db.session.commit()
    log_action('admin', None, 'RESERVATION_EXTENDED', 'reservation', res.id, {'days': RESERVATION_EXTENSION_DAYS})
    db.session.commit()
    flash(f'Reservation prolongee de {RESERVATION_EXTENSION_DAYS} jours', 'success')
    return redirect(request.referrer or url_for('admin'))

@app.route('/reservations/<int:reservation_id>/fulfill', methods=['POST'])
@login_required_admin
def fulfill_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if not reservation.active:
        flash('Reservation deja traitee', 'warning')
        return redirect(request.referrer or url_for('admin'))

    if reservation.book.available_copies() <= 0:
        flash('Aucune copie disponible pour ce livre', 'danger')
        return redirect(request.referrer or url_for('admin'))

    if reservation.user.active_loans_count() >= MAX_ACTIVE_LOANS:
        flash('Limite d emprunts atteinte pour cet usager', 'danger')
        return redirect(request.referrer or url_for('admin'))

    loan = Loan(user_id=reservation.user_id, book_id=reservation.book_id, due_date=datetime.utcnow() + timedelta(days=DEFAULT_LOAN_DAYS))
    reservation.active = False
    db.session.add(loan)
    db.session.commit()
    log_action('admin', None, 'RESERVATION_FULFILLED', 'reservation', reservation.id, {'loan_id': loan.id})
    db.session.commit()

    flash('Reservation convertie en emprunt', 'success')
    return redirect(request.referrer or url_for('admin'))

@app.route('/admin')
@login_required_admin
def admin():
    from datetime import datetime
    # emprunts actifs
    active_loans = Loan.query.filter_by(returned=False).all()
    # emprunts retournés (derniers)
    returned_loans = Loan.query.filter_by(returned=True).order_by(Loan.borrowed_on.desc()).limit(10).all()
    # réservations actives
    reservations = Reservation.query.filter_by(active=True).all()
    pending_users = User.query.filter_by(approved=False).order_by(User.registered_on.asc()).all()
    approved_users = User.query.filter_by(approved=True, is_active=True).order_by(User.name.asc()).all()
    books = Book.query.order_by(Book.title.asc()).all()
    # statistiques
    total_books = Book.query.count()
    total_users = User.query.count()
    active_loans_count = Loan.query.filter_by(returned=False).count()
    reservations_count = Reservation.query.filter_by(active=True).count()
    
    return render_template('admin.html',
        active_loans=active_loans,
        returned_loans=returned_loans,
        reservations=reservations,
        pending_users=pending_users,
        approved_users=approved_users,
        books=books,
        total_books=total_books,
        total_users=total_users,
        active_loans_count=active_loans_count,
        reservations_count=reservations_count,
        now=datetime.utcnow())

@app.route('/reservations')
@login_required_admin
def reservations_dashboard():
    from datetime import datetime
    from sqlalchemy import func
    
    # Toutes les réservations
    all_reservations = Reservation.query.all()
    
    # Réservations en attente
    pending_list = Reservation.query.filter_by(active=True).order_by(Reservation.reserved_on.desc()).all()
    
    # Réservations complétées
    completed_list = Reservation.query.filter_by(active=False).order_by(Reservation.reserved_on.desc()).limit(20).all()
    
    # Statistiques
    total_reservations = len(all_reservations)
    pending_reservations = len(pending_list)
    completed_reservations = len(completed_list)
    unique_users = len(set(res.user_id for res in all_reservations))
    
    # Livres les plus réservés
    popular_books = db.session.query(Book, func.count(Reservation.id)).join(
        Reservation, Book.id == Reservation.book_id
    ).group_by(Book.id).order_by(func.count(Reservation.id).desc()).limit(5).all()
    
    return render_template('reservations_dashboard.html',
        pending_list=pending_list,
        completed_list=completed_list,
        popular_books=popular_books,
        total_reservations=total_reservations,
        pending_reservations=pending_reservations,
        completed_reservations=completed_reservations,
        unique_users=unique_users)

@app.route('/admin/audit')
@login_required_admin
def audit_dashboard():
    logs = AuditLog.query.order_by(AuditLog.created_on.desc()).limit(200).all()
    return render_template('audit.html', logs=logs)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
