"""OpenLib Application Entry Point."""
import os
from app import create_app, db
from app.models.user import User
from app.models.book import Book, Category, AgeGroup
from app.models.transaction import BorrowRecord, ExchangeRequest, Donation
from app.models.review import Review, Bookmark

app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Book': Book,
        'Category': Category,
        'AgeGroup': AgeGroup,
        'BorrowRecord': BorrowRecord,
        'ExchangeRequest': ExchangeRequest,
        'Donation': Donation,
        'Review': Review,
        'Bookmark': Bookmark,
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

