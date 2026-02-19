from app import app, db
from models import User, Book
from datetime import datetime

books_data = [
    ('Le Petit Prince', 'Antoine de Saint-Exupéry', 3),
    ('1984', 'George Orwell', 2),
    ('Les Misérables', 'Victor Hugo', 1),
    ('Le Seigneur des Anneaux', 'J.R.R. Tolkien', 2),
    ('Harry Potter à l\'école des sorciers', 'J.K. Rowling', 4),
    ('Orgueil et Préjugés', 'Jane Austen', 2),
    ('Les Trois Mousquetaires', 'Alexandre Dumas', 2),
    ('Le Comte de Monte Cristo', 'Alexandre Dumas', 2),
    ('L\'Île au Trésor', 'Robert Louis Stevenson', 1),
    ('Sherlock Holmes', 'Arthur Conan Doyle', 3),
    ('Le Hobbit', 'J.R.R. Tolkien', 2),
    ('Fondation', 'Isaac Asimov', 1),
    ('Dune', 'Frank Herbert', 2),
    ('Le Meilleur des Mondes', 'Aldous Huxley', 1),
    ('Fahrenheit 451', 'Ray Bradbury', 2),
    ('L\'Étranger', 'Albert Camus', 1),
    ('La Métamorphose', 'Franz Kafka', 1),
    ('Cent ans de solitude', 'Gabriel García Márquez', 2),
    ('Don Quichotte', 'Miguel de Cervantes', 1),
    ('Crime et Châtiment', 'Fiodor Dostoïevski', 1),
    ('Les Fleurs du Mal', 'Charles Baudelaire', 2),
    ('Moby Dick', 'Herman Melville', 1),
    ('Guerre et Paix', 'Léon Tolstoï', 1),
    ('Anna Karénine', 'Léon Tolstoï', 2),
    ('Notre-Dame de Paris', 'Victor Hugo', 2),
    ('Le Phantom de l\'Opéra', 'Gaston Leroux', 2),
    ('Jane Eyre', 'Charlotte Brontë', 2),
    ('Les Hauts de Hurlevent', 'Emily Brontë', 1),
    ('Le Grand Gatsby', 'F. Scott Fitzgerald', 2),
    ('De la Terre à la Lune', 'Jules Verne', 2),
    ('Vingt mille lieues sous les mers', 'Jules Verne', 2),
    ('Le Voyage au centre de la Terre', 'Jules Verne', 1),
    ('Frankenstein', 'Mary Shelley', 2),
    ('Dracula', 'Bram Stoker', 2),
    ('Dr Jekyll et M. Hyde', 'Robert Louis Stevenson', 2),
    ('Les Aventures de Tom Sawyer', 'Mark Twain', 2),
    ('Les Aventures de Huckleberry Finn', 'Mark Twain', 1),
    ('Robinson Crusoé', 'Daniel Defoe', 1),
    ('Les Aventures du Baron de Munchausen', 'Rudolf Erich Raspe', 1),
    ('Alice au pays des merveilles', 'Lewis Carroll', 3),
    ('De l\'autre côté du miroir', 'Lewis Carroll', 2),
    ('Le Magicien d\'Oz', 'L. Frank Baum', 2),
    ('Peter Pan', 'J.M. Barrie', 2),
    ('L\'Appel de la Forêt', 'Jack London', 1),
    ('Croc-Blanc', 'Jack London', 1),
    ('Tarzan le singe', 'Edgar Rice Burroughs', 1),
    ('La Reine des Neiges', 'Hans Christian Andersen', 2),
    ('Le Vilain Petit Canard', 'Hans Christian Andersen', 1),
    ('Un conte de Noël', 'Charles Dickens', 2),
    ('Oliver Twist', 'Charles Dickens', 2),
    ('Grandes Espérances', 'Charles Dickens', 1),
    ('David Copperfield', 'Charles Dickens', 1),
    ('La Petite Dorrit', 'Charles Dickens', 1),
    ('Bleak House', 'Charles Dickens', 1),
    ('Le Magasin des Merveilles', 'Charles Dickens', 1),
    ('La Maison des Esprits', 'Isabel Allende', 2),
    ('Chronique d\'une mort annoncée', 'Gabriel García Márquez', 2),
    ('L\'Amour aux temps du choléra', 'Gabriel García Márquez', 2),
    ('Mémoires d\'Hadrien', 'Marguerite Yourcenar', 1),
    ('Le Deuxième Sexe', 'Simone de Beauvoir', 1),
    ('Le Sida du Monde', 'Jean-Paul Sartre', 1),
    ('Existentialisme est humanisme', 'Jean-Paul Sartre', 1),
    ('Critique de la Raison Pure', 'Immanuel Kant', 1),
    ('Le Contrat Social', 'Jean-Jacques Rousseau', 1),
    ('Traité sur la Tolérance', 'Voltaire', 1),
    ('Candide', 'Voltaire', 2),
    ('Zadig', 'Voltaire', 1),
    ('La Nouvelle Héloïse', 'Jean-Jacques Rousseau', 1),
    ('Émile ou de l\'Éducation', 'Jean-Jacques Rousseau', 1),
    ('Lettres Philosophiques', 'Voltaire', 1),
    ('L\'Esprit des Lois', 'Montesquieu', 1),
]

users_data = [
    ('Alice Martin', 'alice.martin@example.com'),
    ('Bob Dupont', 'bob.dupont@example.com'),
    ('Charlie Bernard', 'charlie.bernard@example.com'),
    ('Diana Leclerc', 'diana.leclerc@example.com'),
    ('Eva Moreau', 'eva.moreau@example.com'),
    ('François Petit', 'francois.petit@example.com'),
    ('Gabrielle Lefevre', 'gabrielle.lefevre@example.com'),
    ('Henri Michel', 'henri.michel@example.com'),
    ('Isabelle Roux', 'isabelle.roux@example.com'),
    ('Jean Dubois', 'jean.dubois@example.com'),
]

with app.app_context():
    db.create_all()
    
    # Ajouter les livres dynamiquement (sans duplicatas)
    added_books = 0
    for idx, (title, author, copies) in enumerate(books_data, start=1):
        if not Book.query.filter_by(title=title).first():
            book = Book(
                title=title,
                author=author,
                total_copies=copies,
                language='Français',
                category='General',
                isbn=f'9780000{idx:06d}'
            )
            db.session.add(book)
            added_books += 1
    
    # Ajouter les usagers dynamiquement (sans duplicatas)
    added_users = 0
    for idx, (name, email) in enumerate(users_data, start=1):
        if not User.query.filter_by(email=email).first():
            user = User(
                name=name,
                email=email,
                approved=True,
                approved_on=datetime.utcnow(),
                card_number=f'CARD-SEED-{idx:04d}',
                affiliation='Public',
                is_active=True
            )
            db.session.add(user)
            added_users += 1
    
    db.session.commit()
    
    total_books = Book.query.count()
    total_users = User.query.count()
    print(f'✓ Base de données initialisée avec {total_books} livres et {total_users} usagers.')
    if added_books > 0 or added_users > 0:
        print(f'  → {added_books} nouveaux livres ajoutés')
        print(f'  → {added_users} nouveaux usagers ajoutés')
