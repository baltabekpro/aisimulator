"""
Определения форм для административной панели.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, EqualTo, ValidationError

class LoginForm(FlaskForm):
    """Форма входа администратора"""
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class CharacterForm(FlaskForm):
    """Форма создания/редактирования персонажа"""
    name = StringField('Имя', validators=[DataRequired(), Length(min=2, max=100)])
    age = IntegerField('Возраст', validators=[Optional(), NumberRange(min=1, max=1000)])
    personality = TextAreaField('Черты характера', validators=[Optional()])
    background = TextAreaField('История персонажа', validators=[Optional()])
    interests = TextAreaField('Интересы (через запятую)', validators=[Optional()])
    submit = SubmitField('Сохранить персонажа')

class UserForm(FlaskForm):
    """Форма редактирования пользователя"""
    name = StringField('Имя', validators=[Optional(), Length(max=100)])
    telegram_id = StringField('Telegram ID', validators=[Optional(), Length(max=50)])
    platform = StringField('Платформа', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Сохранить пользователя')

class MemoryForm(FlaskForm):
    """Форма создания/редактирования памяти"""
    content = TextAreaField('Содержание памяти', validators=[DataRequired()])
    importance = IntegerField('Важность (1-10)', validators=[NumberRange(min=1, max=10)])
    submit = SubmitField('Сохранить память')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')
