from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin или ip


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'ip':
                return redirect(url_for('ip_dashboard'))
        else:
            flash('Неверный логин или пароль')

    return render_template('login.html')


@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', username=session.get('username'))


@app.route('/ip')
def ip_dashboard():
    if session.get('role') != 'ip':
        return redirect(url_for('login'))
    return render_template('ip_dashboard.html', username=session.get('username'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


def create_test_users():
    admin_exists = User.query.filter_by(username='admin').first()
    ip_exists = User.query.filter_by(username='ip_user').first()

    if not admin_exists:
        admin = User(username='admin', password='123', role='admin')
        db.session.add(admin)

    if not ip_exists:
        ip_user = User(username='ip_user', password='123', role='ip')
        db.session.add(ip_user)

    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_test_users()

    app.run(debug=True)