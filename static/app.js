// Mise à jour dynamique des statistiques
async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        // Animation des compteurs
        animateValue('stat-books', data.total_books);
        animateValue('stat-users', data.total_users);
        animateValue('stat-loans', data.active_loans);
    } catch (error) {
        console.error('Erreur lors du chargement des stats:', error);
    }
}

// Animation des compteurs
function animateValue(id, endValue) {
    const element = document.getElementById(id);
    if (!element) return;
    
    const startValue = parseInt(element.textContent) || 0;
    const duration = 800;
    const startTime = Date.now();
    
    function update() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const currentValue = Math.floor(startValue + (endValue - startValue) * progress);
        
        element.textContent = currentValue;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    update();
}

// Charger les derniers livres dynamiquement
async function loadLatestBooks() {
    try {
        const response = await fetch('/api/latest-books');
        const books = await response.json();
        
        const booksContainer = document.getElementById('books-container');
        if (!booksContainer) return;
        
        let html = '';
        books.forEach(book => {
            const availableText = book.available_copies > 0 
                ? `<span class="badge success">${book.available_copies} disponible(s)</span>`
                : `<span class="badge danger">Non disponible</span>`;
            
            html += `
                <div class="book-card">
                    <div class="book-cover">📖</div>
                    <div class="book-info">
                        <h4><a href="/book/${book.id}">${book.title}</a></h4>
                        <p class="author">${book.author}</p>
                        <p class="availability">${availableText}</p>
                    </div>
                </div>
            `;
        });
        
        booksContainer.innerHTML = html;
    } catch (error) {
        console.error('Erreur lors du chargement des livres:', error);
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    updateStats();
    loadLatestBooks();
    
    // Mettre à jour les stats toutes les 10 secondes
    setInterval(updateStats, 10000);
    // Mettre à jour les livres toutes les 30 secondes
    setInterval(loadLatestBooks, 30000);
});