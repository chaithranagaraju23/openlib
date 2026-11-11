"""Authentication and user profile forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from app.models.user import User


class LoginForm(FlaskForm):
    """User login form."""
    email_or_username = StringField(
        'Email or Username',
        validators=[DataRequired(), Length(min=2, max=128)],
        render_kw={'placeholder': 'Enter your email or username'}
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()],
        render_kw={'placeholder': 'Enter your password'}
    )
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """User registration form."""
    full_name = StringField(
        'Full Name',
        validators=[DataRequired(), Length(min=2, max=128)],
        render_kw={'placeholder': 'e.g. Aarav Sharma'}
    )
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=3, max=64)],
        render_kw={'placeholder': 'Choose a unique username'}
    )
    email = StringField(
        'Email Address',
        validators=[DataRequired(), Email(), Length(max=128)],
        render_kw={'placeholder': 'you@example.com'}
    )
    preferred_age_group = SelectField(
        'Primary Library Section',
        choices=[
            ('children', "Children's Library (Ages 5–12)"),
            ('youth', 'Youth Library (Ages 13–24)'),
            ('adults', 'Adult Library (Ages 25–59)'),
            ('seniors', 'Senior Citizens Library (Ages 60+)'),
        ],
        default='adults'
    )
    preferred_language = SelectField(
        'Preferred Language',
        choices=[
            ('English', 'English'),
            ('Hindi', 'Hindi'),
            ('Spanish', 'Spanish'),
            ('French', 'French'),
            ('German', 'German'),
            ('Sanskrit', 'Sanskrit'),
            ('Tamil', 'Tamil'),
            ('Other', 'Other'),
        ],
        default='English'
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=8, message='Password must be at least 8 characters long.')
        ],
        render_kw={'placeholder': 'At least 8 characters'}
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')],
        render_kw={'placeholder': 'Repeat your password'}
    )
    submit = SubmitField('Create Free Account')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError('This username is already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError('An account with this email already exists.')


class ProfileUpdateForm(FlaskForm):
    """Profile update form."""
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=128)])
    bio = TextAreaField('About / Reading Interests', validators=[Optional(), Length(max=500)])
    preferred_language = SelectField(
        'Preferred Language',
        choices=[
            ('English', 'English'),
            ('Hindi', 'Hindi'),
            ('Spanish', 'Spanish'),
            ('French', 'French'),
            ('German', 'German'),
            ('Sanskrit', 'Sanskrit'),
            ('Tamil', 'Tamil'),
            ('Other', 'Other'),
        ]
    )
    preferred_age_group = SelectField(
        'Preferred Library Section',
        choices=[
            ('children', "Children's Library (5–12)"),
            ('youth', 'Youth Library (13–24)'),
            ('adults', 'Adult Library (25–59)'),
            ('seniors', 'Senior Citizens Library (60+)'),
        ]
    )
    large_text = BooleanField('Enable Large Text Mode')
    high_contrast = BooleanField('Enable High Contrast Mode')
    text_to_speech = BooleanField('Enable Text-to-Speech Controls')
    night_mode = BooleanField('Enable Night Mode Reader by Default')
    submit = SubmitField('Save Profile & Preferences')


class PasswordChangeForm(FlaskForm):
    """Change password form."""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField(
        'New Password',
        validators=[DataRequired(), Length(min=8, message='Password must be at least 8 characters.')]
    )
    confirm_new_password = PasswordField(
        'Confirm New Password',
        validators=[DataRequired(), EqualTo('new_password', message='Passwords must match.')]
    )
    submit = SubmitField('Update Password')

