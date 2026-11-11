"""Database seeder for AgeGroups, all 40 Categories, Verified 420+ Book Catalogue, and default accounts."""
import json
import os
from datetime import datetime

from app import db
from app.models.user import User
from app.models.book import AgeGroup, Category, Book
from app.models.transaction import ExchangeListing
from app.services.catalogue_manager import import_from_records


AGE_GROUP_DEFS = [
    {
        'name': 'Children',
        'slug': 'children',
        'display_name': "Children's Library",
        'description': 'Stories, fables, illustrated classics, and foundational science crafted for young minds aged 5–12.',
        'min_age': 5,
        'max_age': 12,
        'icon': 'bi-stars',
        'color_class': 'theme-children',
        'bg_color': '#0284C7',
        'sort_order': 1,
    },
    {
        'name': 'Youth',
        'slug': 'youth',
        'display_name': 'Youth Library',
        'description': 'Programming, STEM, exam prep, entrepreneurship, and fiction for students and young adults aged 13–24.',
        'min_age': 13,
        'max_age': 24,
        'icon': 'bi-rocket-takeoff',
        'color_class': 'theme-youth',
        'bg_color': '#4F46E5',
        'sort_order': 2,
    },
    {
        'name': 'Adults',
        'slug': 'adults',
        'display_name': 'Adult Library',
        'description': 'Business, personal finance, world history, psychology, health, and literature for lifelong learners aged 25–59.',
        'min_age': 25,
        'max_age': 59,
        'icon': 'bi-briefcase',
        'color_class': 'theme-adults',
        'bg_color': '#1E3A5F',
        'sort_order': 3,
    },
    {
        'name': 'Seniors',
        'slug': 'seniors',
        'display_name': 'Senior Citizens Library',
        'description': 'Philosophy, classic literature, poetry, devotional works, gardening, and accessible large-print reading for ages 60+.',
        'min_age': 60,
        'max_age': 100,
        'icon': 'bi-heart-pulse',
        'color_class': 'theme-seniors',
        'bg_color': '#0F766E',
        'sort_order': 4,
    },
]

CATEGORY_DEFS = {
    'children': [
        ('Moral Stories', 'bi-heart', 'Timeless fables and stories building empathy, kindness, and integrity.'),
        ('Fairy Tales', 'bi-magic', 'Classic fairy tales and imaginative folk wonders from around the world.'),
        ('Panchatantra Stories', 'bi-journal-richtext', 'Ancient Indian wisdom tales featuring clever animals and moral lessons.'),
        ('Adventure Stories', 'bi-compass', 'Exciting journeys, treasure quests, and youthful courage.'),
        ('Science for Kids', 'bi-lightbulb', 'Curiosity-sparking introductions to nature, space, and everyday science.'),
        ('Picture Books', 'bi-images', 'Illustrated books designed for early readers and visual storytelling.'),
        ('Educational Books', 'bi-mortarboard', 'Foundational reading, numeracy, and elementary school companions.'),
        ('General Knowledge', 'bi-globe2', 'Fascinating facts about our world, history, wildlife, and wonders.'),
        ('Bedtime Stories', 'bi-moon-stars', 'Gentle, soothing stories ideal for peaceful evening reading.'),
        ('Folktales', 'bi-people', 'Cultural folktales and oral traditions passed across generations.'),
    ],
    'youth': [
        ('Programming and Computer Science', 'bi-code-slash', 'Coding, algorithms, Python, data structures, and computer science foundations.'),
        ('Science and Mathematics', 'bi-calculator', 'Open textbooks and resources in algebra, calculus, physics, and biology.'),
        ('Competitive Exam Preparation', 'bi-award', 'Aptitude, quantitative reasoning, core academic guides, and study references.'),
        ('Self-Improvement', 'bi-graph-up-arrow', 'Study habits, focus, leadership, and personal effectiveness.'),
        ('Entrepreneurship', 'bi-shop', 'Building ventures, startup basics, innovation, and social enterprise.'),
        ('Career Guidance', 'bi-signpost-split', 'Exploring professions, career planning, communication, and workplace readiness.'),
        ('Fiction and Novels', 'bi-book-half', 'Engaging novels, speculative fiction, and coming-of-age stories.'),
        ('Technology', 'bi-cpu', 'Digital literacy, engineering systems, AI concepts, and modern tech.'),
        ('Psychology', 'bi-emoji-smile', 'Understanding memory, learning, emotions, and human behavior.'),
        ('Biographies', 'bi-person-badge', 'Inspiring life stories of scientists, pioneers, and changemakers.'),
    ],
    'adults': [
        ('Business and Entrepreneurship', 'bi-building', 'Strategy, management, organizational leadership, and business economics.'),
        ('Personal Finance', 'bi-cash-coin', 'Budgeting, saving, investing fundamentals, and financial literacy.'),
        ('Literature and Novels', 'bi-bookmarks', 'World novels and enduring literary classics across cultures.'),
        ('History and Culture', 'bi-bank', 'World civilizations, cultural heritage, and historical analysis.'),
        ('Science and Technology', 'bi-atom', 'Modern science, environmental stewardship, data, and technological change.'),
        ('Psychology', 'bi-diagram-3', 'Cognitive science, behavioral economics, social psychology, and wellbeing.'),
        ('Health and Wellness', 'bi-activity', 'Evidence-informed nutrition, preventive health, fitness, and public health.'),
        ('Personal Development', 'bi-compass-fill', 'Critical thinking, ethics, productivity, and lifelong mastery.'),
        ('Parenting', 'bi-house-heart', 'Child development, family wellbeing, and supportive parenting resources.'),
        ('Biographies', 'bi-journal-text', 'Memoirs and biographies of historical leaders, thinkers, and artists.'),
    ],
    'seniors': [
        ('Spirituality and Philosophy', 'bi-sun', 'Philosophical reflections, mindfulness, wisdom traditions, and inner peace.'),
        ('History and Culture', 'bi-hourglass-split', 'Rich historical chronicles, heritage, and cultural retrospectives.'),
        ('Classic Literature', 'bi-book', 'Beloved literary masterpieces in comfortable reading formats.'),
        ('Biographies', 'bi-person-lines-fill', 'Remarkable lives, autobiographies, and inspiring human journeys.'),
        ('Health and Wellness', 'bi-heart', 'Healthy aging, gentle movement, yoga, nutrition, and vitality.'),
        ('Devotional Literature', 'bi-flower1', 'Sacred classics, hymns, devotional poetry, and spiritual commentary.'),
        ('Poetry', 'bi-feather', 'Classic and lyrical poetry celebrating life, nature, and reflection.'),
        ('Short Stories', 'bi-collection', 'Crisp, memorable short fiction from master storytellers.'),
        ('Gardening and Hobbies', 'bi-tree', 'Home gardening, botany, nature observation, and enriching pastimes.'),
        ('Large-Print Books', 'bi-zoom-in', 'Accessible large-print and high-readability editions.'),
    ],
}


def seed_age_groups_and_categories():
    """Ensure all 4 AgeGroups and 40 Categories exist idempotently."""
    ag_map = {}
    for ag_def in AGE_GROUP_DEFS:
        ag = AgeGroup.query.filter_by(slug=ag_def['slug']).first()
        if not ag:
            ag = AgeGroup(**ag_def)
            db.session.add(ag)
            db.session.flush()
        ag_map[ag.slug] = ag

    for ag_slug, cat_list in CATEGORY_DEFS.items():
        ag = ag_map[ag_slug]
        for idx, (cat_name, icon, desc) in enumerate(cat_list, start=1):
            from app.utils.helpers import slugify
            cat_slug = f'{ag_slug}-{slugify(cat_name)}'
            cat = Category.query.filter_by(slug=cat_slug).first()
            if not cat:
                cat = Category(
                    name=cat_name,
                    slug=cat_slug,
                    description=desc,
                    icon=icon,
                    age_group_id=ag.id,
                    is_active=True,
                    sort_order=idx,
                )
                db.session.add(cat)
    db.session.commit()


def seed_default_users(app):
    """Create default admin and demo reader account if not present."""
    admin_email = app.config.get('ADMIN_EMAIL', 'admin@openlib.org')
    admin_username = app.config.get('ADMIN_USERNAME', 'admin')
    admin_password = app.config.get('ADMIN_PASSWORD', 'AdminSecure@2024')

    admin = User.query.filter(
        db.or_(User.email == admin_email, User.username == admin_username)
    ).first()
    if not admin:
        admin = User(
            username=admin_username,
            email=admin_email,
            full_name='OpenLib Chief Librarian',
            role='admin',
            is_active=True,
            is_verified=True,
            email_confirmed=True,
            bio='Administrator overseeing OpenLib catalogue verification and community donations.',
        )
        admin.set_password(admin_password)
        db.session.add(admin)

    demo_user = User.query.filter_by(username='reader').first()
    if not demo_user:
        demo_user = User(
            username='reader',
            email='reader@openlib.org',
            full_name='Maya Patel',
            role='user',
            preferred_age_group='youth',
            preferred_language='English',
            is_active=True,
            is_verified=True,
            email_confirmed=True,
            bio='Lifelong reader exploring classics, STEM textbooks, and community book swaps.',
        )
        demo_user.set_password('ReaderPass@2024')
        db.session.add(demo_user)

    db.session.commit()


def seed_verified_catalogue(app):
    """Load verified catalogue from data/catalogue/openlib_verified_catalogue.json if DB has 0 books."""
    if Book.query.count() > 0:
        return

    catalogue_dir = app.config.get('CATALOGUE_FOLDER')
    json_path = os.path.join(catalogue_dir, 'openlib_verified_catalogue.json')
    if not os.path.isfile(json_path):
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        payload = json.load(f)

    records = payload.get('books', []) if isinstance(payload, dict) else payload
    if records:
        import_from_records(records, update_duplicates=False, verify_urls=False)


def seed_sample_exchange_listings():
    """Seed a couple of initial community exchange listings if none exist."""
    if ExchangeListing.query.count() > 0:
        return
    reader = User.query.filter_by(username='reader').first()
    admin = User.query.filter_by(role='admin').first()
    if not reader or not admin:
        return

    samples = [
        ExchangeListing(
            user_id=reader.id,
            title='Think Python: How to Think Like a Computer Scientist',
            author='Allen B. Downey',
            language='English',
            age_group_name='Youth',
            category_name='Programming and Computer Science',
            condition='Like New',
            location='Bengaluru, IN',
            delivery_method='Local Meetup or Mail',
            looking_for='Any discrete mathematics or algorithms textbook',
            notes='Clean print edition with zero markings.',
            status='available',
        ),
        ExchangeListing(
            user_id=admin.id,
            title='Stories from the Panchatantra (Illustrated Edition)',
            author='Vishnu Sharma',
            language='English',
            age_group_name='Children',
            category_name='Panchatantra Stories',
            condition='Good',
            location='Pune, IN',
            delivery_method='Local Meetup or Mail',
            looking_for='Children fairy tales or science activity books',
            notes='Community library surplus copy available for local family exchange.',
            status='available',
        ),
    ]
    db.session.add_all(samples)
    db.session.commit()


def seed_all(app):
    """Idempotent full database initialization."""
    seed_age_groups_and_categories()
    seed_default_users(app)
    seed_verified_catalogue(app)
    seed_sample_exchange_listings()

