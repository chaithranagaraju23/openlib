"""Forms for books, reviews, donations, exchanges, contact, and admin import."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, TextAreaField, IntegerField, SelectField, BooleanField, SubmitField
)
from wtforms.validators import DataRequired, Length, Optional, Email, NumberRange, URL


class BookForm(FlaskForm):
    """Admin book creation / editing form."""
    title = StringField('Title', validators=[DataRequired(), Length(max=300)])
    author = StringField('Author', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10)])
    age_group_id = SelectField('Age Group', coerce=int, validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    min_age = IntegerField('Recommended Minimum Age', validators=[Optional(), NumberRange(min=0, max=100)], default=5)
    max_age = IntegerField('Recommended Maximum Age', validators=[Optional(), NumberRange(min=1, max=120)], default=99)
    language = StringField('Language', validators=[DataRequired(), Length(max=50)], default='English')
    publisher = StringField('Publisher', validators=[Optional(), Length(max=200)])
    publication_year = IntegerField('Publication Year', validators=[Optional(), NumberRange(min=1000, max=2100)])
    isbn = StringField('ISBN (if available)', validators=[Optional(), Length(max=32)])
    pages = IntegerField('Page Count', validators=[Optional(), NumberRange(min=1, max=20000)])
    file_format = SelectField(
        'File Format',
        choices=[
            ('PDF', 'PDF'),
            ('HTML', 'HTML (Online Text)'),
            ('EPUB', 'EPUB'),
            ('PDF/HTML', 'PDF & HTML'),
            ('Print/Digital', 'Print / Digital Loan'),
        ],
        default='PDF'
    )
    reading_url = StringField('Official Reading URL', validators=[Optional(), URL(), Length(max=1000)])
    download_url = StringField('Authorized Download URL', validators=[Optional(), URL(), Length(max=1000)])
    source_url = StringField('Original Source URL', validators=[DataRequired(), URL(), Length(max=1000)])
    source_repository = SelectField(
        'Source Repository',
        choices=[
            ('Project Gutenberg', 'Project Gutenberg'),
            ('Internet Archive', 'Internet Archive'),
            ('Directory of Open Access Books', 'Directory of Open Access Books (DOAB)'),
            ('Wikisource', 'Wikisource'),
            ('StoryWeaver', 'StoryWeaver (Pratham Books)'),
            ('OpenStax', 'OpenStax'),
            ('Standard Ebooks', 'Standard Ebooks'),
            ('Open Textbook Library', 'Open Textbook Library'),
            ('Community Donation', 'Community Donation'),
            ('Other Verified Repository', 'Other Verified Repository'),
        ],
        default='Project Gutenberg'
    )
    copyright_status = SelectField(
        'Copyright Status',
        choices=[
            ('Public Domain', 'Public Domain'),
            ('Open Access (Creative Commons)', 'Open Access (Creative Commons)'),
            ('Borrow / Controlled Digital Lending', 'Borrow / Controlled Digital Lending'),
            ('Author / Publisher Permission', 'Author / Publisher Permission'),
        ],
        default='Public Domain'
    )
    licence = StringField('Licence Information', validators=[DataRequired(), Length(max=200)], default='Public Domain')
    licence_url = StringField('Licence URL', validators=[Optional(), URL(), Length(max=500)])
    tags = StringField('Tags (comma-separated)', validators=[Optional(), Length(max=500)])
    cover_file = FileField('Upload Cover Image (JPG/PNG/WEBP)', validators=[
        Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only!')
    ])
    pdf_file = FileField('Upload Authorized PDF Book (if redistribution permitted)', validators=[
        Optional(), FileAllowed(['pdf'], 'PDF documents only!')
    ])
    is_readable_online = BooleanField('Available to Read Online', default=True)
    is_downloadable = BooleanField('Download Permitted by Licence', default=False)
    redistribution_permitted = BooleanField('Hosting / Redistribution Permitted', default=False)
    is_borrowable = BooleanField('Available to Borrow in OpenLib', default=True)
    is_exchangeable = BooleanField('Available for Community Exchange', default=False)
    is_featured = BooleanField('Feature on Homepage', default=False)
    is_verified = BooleanField('Metadata & Source Verified', default=True)
    licence_verified = BooleanField('Licence Explicitly Verified', default=True)
    is_active = BooleanField('Active in Public Catalogue', default=True)
    verification_notes = TextAreaField('Verification Notes', validators=[Optional()])
    submit = SubmitField('Save Book')


class ReviewForm(FlaskForm):
    """Book review and rating form."""
    rating = SelectField(
        'Rating',
        coerce=int,
        choices=[(5, '5 - Excellent'), (4, '4 - Very Good'), (3, '3 - Good'), (2, '2 - Fair'), (1, '1 - Poor')],
        validators=[DataRequired()]
    )
    title = StringField('Review Headline', validators=[DataRequired(), Length(min=3, max=200)])
    content = TextAreaField('Your Review', validators=[DataRequired(), Length(min=10, max=2000)])
    submit = SubmitField('Submit Review')


class DonationForm(FlaskForm):
    """Donate a digital or physical book to OpenLib."""
    donor_name = StringField('Your Name', validators=[DataRequired(), Length(min=2, max=128)])
    donor_email = StringField('Your Email', validators=[DataRequired(), Email(), Length(max=128)])
    donation_type = SelectField(
        'Donation Type',
        choices=[
            ('digital', 'Digital Book (Public Domain / Open Access / Own Work)'),
            ('physical', 'Physical Book Donation for Community Library'),
        ],
        default='digital'
    )
    book_title = StringField('Book Title', validators=[DataRequired(), Length(max=300)])
    book_author = StringField('Author', validators=[DataRequired(), Length(max=200)])
    book_description = TextAreaField('Description / Summary', validators=[DataRequired(), Length(min=10, max=2000)])
    age_group_name = SelectField(
        'Recommended Age Group',
        choices=[
            ('Children', "Children's Library (5–12)"),
            ('Youth', 'Youth Library (13–24)'),
            ('Adults', 'Adult Library (25–59)'),
            ('Seniors', 'Senior Citizens Library (60+)'),
        ],
        default='Adults'
    )
    book_category = StringField('Category / Subject', validators=[DataRequired(), Length(max=100)])
    book_language = StringField('Language', validators=[DataRequired(), Length(max=50)], default='English')
    isbn = StringField('ISBN (Optional)', validators=[Optional(), Length(max=32)])
    publication_year = IntegerField('Publication Year (Optional)', validators=[Optional(), NumberRange(min=1000, max=2100)])
    publisher = StringField('Publisher (Optional)', validators=[Optional(), Length(max=200)])
    licence = StringField('Licence / Copyright Status', validators=[DataRequired(), Length(max=200)], default='Public Domain')
    source_url = StringField('Official Source / Reference URL', validators=[Optional(), URL(), Length(max=500)])
    file_url = StringField('Direct File / Reading URL (if digital)', validators=[Optional(), URL(), Length(max=500)])
    pdf_file = FileField('Upload Authorized PDF (Optional, Public Domain / CC only)', validators=[
        Optional(), FileAllowed(['pdf'], 'Only PDF files are accepted.')
    ])
    book_condition = SelectField(
        'Book Condition (for Physical Donations)',
        choices=[('New', 'New'), ('Like New', 'Like New'), ('Good', 'Good'), ('Fair', 'Fair'), ('Digital', 'Digital Copy')],
        default='Digital'
    )
    shipping_address = TextAreaField('Pickup / Drop-off City & Address (for Physical Donations)', validators=[Optional(), Length(max=500)])
    copyright_confirmation = BooleanField(
        'I confirm this book is in the Public Domain, openly licensed (e.g., Creative Commons), or I hold full rights to donate it.',
        validators=[DataRequired(message='You must confirm copyright/licensing eligibility before donating.')]
    )
    submit = SubmitField('Submit Book Donation')


class ExchangeListingForm(FlaskForm):
    """Post a personal/physical book for community exchange."""
    title = StringField('Book Title', validators=[DataRequired(), Length(max=300)])
    author = StringField('Author', validators=[DataRequired(), Length(max=200)])
    isbn = StringField('ISBN (Optional)', validators=[Optional(), Length(max=32)])
    language = StringField('Language', validators=[DataRequired(), Length(max=50)], default='English')
    age_group_name = SelectField(
        'Age Group',
        choices=[('Children', 'Children'), ('Youth', 'Youth'), ('Adults', 'Adults'), ('Seniors', 'Seniors')],
        default='Adults'
    )
    category_name = StringField('Category / Genre', validators=[Optional(), Length(max=100)])
    condition = SelectField(
        'Condition',
        choices=[('New', 'New'), ('Like New', 'Like New'), ('Good', 'Good'), ('Fair', 'Fair')],
        default='Good'
    )
    location = StringField('City / Neighbourhood', validators=[DataRequired(), Length(max=120)])
    delivery_method = SelectField(
        'Exchange Method',
        choices=[
            ('Local Meetup', 'Local Meetup'),
            ('Mail / Postal', 'Mail / Postal'),
            ('Local Meetup or Mail', 'Local Meetup or Mail'),
        ],
        default='Local Meetup or Mail'
    )
    looking_for = StringField('Books / Genres You Are Looking For', validators=[Optional(), Length(max=300)])
    notes = TextAreaField('Additional Notes', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Publish Exchange Listing')


class ExchangeRequestForm(FlaskForm):
    """Send an exchange proposal for a listed book."""
    offered_book_title = StringField('Book You Are Offering', validators=[DataRequired(), Length(max=300)])
    offered_book_author = StringField('Author of Offered Book', validators=[DataRequired(), Length(max=200)])
    offered_book_condition = SelectField(
        'Condition of Offered Book',
        choices=[('New', 'New'), ('Like New', 'Like New'), ('Good', 'Good'), ('Fair', 'Fair')],
        default='Good'
    )
    message = TextAreaField('Message to Owner', validators=[DataRequired(), Length(min=5, max=1000)])
    submit = SubmitField('Send Exchange Request')


class ContactForm(FlaskForm):
    """Contact OpenLib team."""
    name = StringField('Your Name', validators=[DataRequired(), Length(min=2, max=128)])
    email = StringField('Your Email', validators=[DataRequired(), Email(), Length(max=128)])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=3, max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=3000)])
    submit = SubmitField('Send Message')


class CatalogueImportForm(FlaskForm):
    """Admin JSON/CSV catalogue import form."""
    file = FileField('Catalogue File (JSON or CSV)', validators=[
        DataRequired(), FileAllowed(['json', 'csv'], 'Only .json or .csv files are supported.')
    ])
    update_duplicates = BooleanField('Update existing records if duplicate detected', default=False)
    verify_urls = BooleanField('Validate source URL format strictly', default=True)
    submit = SubmitField('Import & Validate Catalogue')

