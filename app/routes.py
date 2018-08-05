from flask import render_template, flash, redirect
from app import app, db
from app.forms import LoginForm, UserRegistrationForm, DrinkRegistrationForm
from app.models import User, Usergroup

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home', username='Roy')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}'.format(form.username.data))
        return redirect('/index')
    return render_template('login.html', title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = UserRegistrationForm()
    if form.validate_on_submit():
        #print("User wants to register!")
        user = User(name=form.name.data, usergroup_id=form.group.data)
        #print(user.name, user.usergroup_id)
        db.session.add(user)
        db.session.commit()
        flash("Gebruiker {} succesvol geregistreerd".format(user.name))
        return redirect('/index')
    return render_template('register.html', title='Registreren', form=form)

@app.route('/balance')
def balance():
    return render_template('balance.html', title='Saldo', Usergroup=Usergroup)

@app.route('/users')
def users():
    return render_template('users.html', title='Gebruikers', User=User)

@app.route('/drink/<name>', methods=['GET', 'POST'])
def drink(name):
    form = DrinkRegistrationForm()
    if form.validate_on_submit():
        flash('Drinken gekocht!')
        return redirect('/index')
    return render_template('drink.html', title=name, name=name, form=form, User=User, Usergroup=Usergroup)