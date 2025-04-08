"""
WTForms for the admin panel.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class UserForm(FlaskForm):
    """Form for creating and editing users."""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[Email(), Optional()])
    password = PasswordField('Password', validators=[Length(min=6, max=50), Optional()])
    is_active = BooleanField('Active')
    submit = SubmitField('Save')
