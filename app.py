from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from models import db, User, Book, Loan, Reservation
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Admin password (à changer en production)
ADMIN_PASSWORD = 'Hermann48'

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

# Create tables and seed minimal data safely using app context.
# This avoids relying on Flask decorator methods that may not be present
# in all runtime environments when the module is imported.
with app.app_context():
    db.create_all()
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
            return redirect(url_for('users'))
        else:
            flash('❌ Mot de passe incorrect', 'danger')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('✓ Déconnecté', 'success')
    return redirect(url_for('index'))

@app.route('/books')
def list_books():
    books = Book.query.all()
    return render_template('books.html', books=books)

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
    all_users = User.query.all()
    return render_template('book_detail.html', book=book, all_users=all_users)

def book_to_dict(b: Book):
    return {
        'id': b.id,
        'title': b.title,
        'author': b.author,
        'total_copies': b.total_copies,
        'available_copies': b.available_copies()
    }

def user_to_dict(u: User):
    return {
        'id': u.id,
        'name': u.name,
        'email': u.email,
        'registered_on': u.registered_on.isoformat(),
        'active_loans': u.active_loans_count()
    }

def loan_to_dict(l: Loan):
    return {
        'id': l.id,
        'user_id': l.user_id,
        'book_id': l.book_id,
        'borrowed_on': l.borrowed_on.isoformat(),
        'due_date': l.due_date.isoformat() if l.due_date else None,
        'returned': l.returned
    }

def reservation_to_dict(r: Reservation):
    return {
        'id': r.id,
        'user_id': r.user_id,
        'book_id': r.book_id,
        'reserved_on': r.reserved_on.isoformat(),
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
    if book.available_copies() <= 0:
        return jsonify({'error': 'no copies available'}), 400
    if user.active_loans_count() >= 5:
        return jsonify({'error': 'user has reached loan limit'}), 400
    loan = Loan(user_id=user.id, book_id=book.id)
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
    if Reservation.query.filter_by(user_id=user_id, book_id=book_id, active=True).first():
        return jsonify({'error': 'active reservation already exists'}), 400
    r = Reservation(user_id=user_id, book_id=book_id)
    db.session.add(r)
    db.session.commit()
    return jsonify({'message': 'reservation created', 'reservation': reservation_to_dict(r)}), 201

@app.route('/users')
@login_required_admin
def users():
    users = User.query.all()
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
        u = User(name=name, email=email)
        db.session.add(u)
        db.session.commit()
        flash('Utilisateur enregistré', 'success')
        return redirect(url_for('users'))
    return render_template('register_user.html')

@app.route('/profile/<int:user_id>')
@login_required_admin
def profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('profile.html', user=user)

@app.route('/borrow', methods=['POST'])
def borrow():
    user_id = int(request.form['user_id'])
    book_id = int(request.form['book_id'])
    user = User.query.get_or_404(user_id)
    book = Book.query.get_or_404(book_id)
    if book.available_copies() <= 0:
        flash('Aucune copie disponible', 'danger')
        return redirect(url_for('book_detail', book_id=book_id))
    if user.active_loans_count() >= 5:
        flash('Limite d\'emprunts atteinte', 'danger')
        return redirect(url_for('book_detail', book_id=book_id))
    loan = Loan(user_id=user.id, book_id=book.id)
    db.session.add(loan)
    db.session.commit()
    flash('Emprunt enregistré', 'success')
    return redirect(url_for('book_detail', book_id=book_id))

@app.route('/return', methods=['POST'])
def return_book():
    loan_id = int(request.form['loan_id'])
    loan = Loan.query.get_or_404(loan_id)
    loan.returned = True
    # after marking returned, try to fulfil next active reservation for this book
    book = loan.book
    db.session.commit()

    # check for active reservations ordered by date
    next_res = Reservation.query.filter_by(book_id=book.id, active=True).order_by(Reservation.reserved_on.asc()).first()
    if next_res and book.available_copies() > 0:
        # create loan for reserved user
        new_loan = Loan(user_id=next_res.user_id, book_id=book.id)
        next_res.active = False
        db.session.add(new_loan)
        db.session.commit()
        flash(f'Retour enregistré. Réservation de {next_res.user.name} convertie en emprunt.', 'success')
    else:
        flash('Retour enregistré', 'success')
    return redirect(url_for('users'))

@app.route('/reserve', methods=['POST'])
def reserve():
    user_id = int(request.form['user_id'])
    book_id = int(request.form['book_id'])
    if Reservation.query.filter_by(user_id=user_id, book_id=book_id, active=True).first():
        flash('Réservation existante', 'warning')
        return redirect(url_for('book_detail', book_id=book_id))
    r = Reservation(user_id=user_id, book_id=book_id)
    db.session.add(r)
    db.session.commit()
    flash('Réservation créée', 'success')
    return redirect(url_for('book_detail', book_id=book_id))

@app.route('/cancel-loan/<int:loan_id>', methods=['POST'])
def cancel_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    loan.returned = True
    db.session.commit()
    flash(f'✓ Emprunt annulé', 'success')
    return redirect(request.referrer or url_for('profile', user_id=loan.user_id))

@app.route('/cancel-reservation/<int:reservation_id>', methods=['POST'])
def cancel_reservation(reservation_id):
    res = Reservation.query.get_or_404(reservation_id)
    res.active = False
    db.session.commit()
    flash(f'✓ Réservation annulée', 'success')
    return redirect(request.referrer or url_for('profile', user_id=res.user_id))

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
    # statistiques
    total_books = Book.query.count()
    total_users = User.query.count()
    active_loans_count = Loan.query.filter_by(returned=False).count()
    reservations_count = Reservation.query.filter_by(active=True).count()
    
    return render_template('admin.html',
        active_loans=active_loans,
        returned_loans=returned_loans,
        reservations=reservations,
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
