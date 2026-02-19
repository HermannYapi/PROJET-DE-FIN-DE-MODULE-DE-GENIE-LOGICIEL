from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    card_number = db.Column(db.String(32), unique=True, nullable=True)
    affiliation = db.Column(db.String(80), nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    registered_on = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False, nullable=False)
    approved_on = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    loans = db.relationship('Loan', backref='user', lazy=True)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

    def active_loans_count(self):
        return Loan.query.filter_by(user_id=self.id, returned=False).count()

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    author = db.Column(db.String(200))
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    publisher = db.Column(db.String(200), nullable=True)
    publication_year = db.Column(db.Integer, nullable=True)
    language = db.Column(db.String(60), nullable=True)
    category = db.Column(db.String(120), nullable=True)
    total_copies = db.Column(db.Integer, default=1)

    loans = db.relationship('Loan', backref='book', lazy=True)
    reservations = db.relationship('Reservation', backref='book', lazy=True)

    def available_copies(self):
        borrowed = Loan.query.filter_by(book_id=self.id, returned=False).count()
        return max(0, self.total_copies - borrowed)

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    borrowed_on = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))
    returned = db.Column(db.Boolean, default=False)
    returned_on = db.Column(db.DateTime, nullable=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    reserved_on = db.Column(db.DateTime, default=datetime.utcnow)
    expires_on = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    active = db.Column(db.Boolean, default=True)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_type = db.Column(db.String(32), nullable=False)  # admin, user, system
    actor_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(120), nullable=False)
    entity_type = db.Column(db.String(32), nullable=False)  # user, book, loan, reservation
    entity_id = db.Column(db.Integer, nullable=True)
    payload = db.Column(db.Text, nullable=True)
    created_on = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
