from datetime import datetime
from zoneinfo import ZoneInfo
import os
import re
import uuid

from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
db = SQLAlchemy(app)

VLADIVOSTOK_TZ = ZoneInfo("Asia/Vladivostok")


def now_vladivostok():
    return datetime.now(VLADIVOSTOK_TZ)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / ip


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    warehouse_id = db.Column(db.String(50), nullable=True)
    manufacturer = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(255), nullable=False)
    purchase_price = db.Column(db.Numeric(10, 2), nullable=True)
    image_path = db.Column(db.Text, nullable=True)
    specifications = db.Column(db.Text, nullable=True)
    condition_rate = db.Column(db.Integer, nullable=False)
    current_status = db.Column(db.String(50), nullable=False)
    comments = db.Column(db.Text, nullable=True)

    status_history = db.relationship(
        'ProductStatusHistory',
        backref='product',
        lazy=True,
        cascade='all, delete-orphan'
    )

class ProductStatusHistory(db.Model):
    __tablename__ = 'product_status_history'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    status_name = db.Column(db.String(50), nullable=False)
    changed_at = db.Column(db.DateTime, nullable=False, default=now_vladivostok)

class Buyer(db.Model):
    __tablename__ = 'buyers'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text, nullable=True)
    contact_info = db.Column(db.String(100), nullable=False)
    source_channel = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    sales = db.relationship('Sale', backref='buyer', lazy=True)

class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, unique=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('buyers.id'), nullable=False)
    sale_state = db.Column(db.String(50), nullable=False)
    sale_begin_date = db.Column(db.DateTime, nullable=False, default=now_vladivostok)
    sale_date = db.Column(db.DateTime, nullable=True)
    channel = db.Column(db.String(100), nullable=True)
    sale_comment = db.Column(db.Text, nullable=True)

    product = db.relationship('Product', backref=db.backref('sale', uselist=False))

class FinType(db.Model):
    __tablename__ = 'fin_type'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False)

    finances = db.relationship('Finance', backref='fin_type', lazy=True)

class Article(db.Model):
    __tablename__ = 'article'

    id = db.Column(db.Integer, primary_key=True)
    article = db.Column(db.String(20), nullable=False)

    finances = db.relationship('Finance', backref='article_ref', lazy=True)

class Finance(db.Model):
    __tablename__ = 'finances'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, db.ForeignKey('fin_type.id'), nullable=False)
    op_date = db.Column(db.DateTime, nullable=False, default=now_vladivostok)
    article = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True)
    comment = db.Column(db.Text, nullable=True)

    product = db.relationship('Product', backref='finances')
    sale = db.relationship('Sale', backref='finances')

AVAILABLE_SALE_STATES = [
    'Активна',
    'Завершена',
    'Отменена'
]

AVAILABLE_STATUSES = [
    'Требует ремонта',
    'В ремонте',
    'Готов к продаже',
    'Зарезервирован',
    'Продан',
    'Снят с продажи'
]

WAREHOUSE_UNIQUE_STATUSES = {
    'Требует ремонта',
    'В ремонте',
    'Готов к продаже',
    'Опубликован',
    'Зарезервирован'
}

WAREHOUSE_LOCKED_STATUSES = {
    'Продан',
    'Снят с продажи'
}

class Advertisement(db.Model):
    __tablename__ = 'advertisements'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    platform = db.Column(db.String(100), nullable=False)
    ad_price = db.Column(db.Numeric(10, 2), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    media_urls = db.Column(db.Text, nullable=True)
    ad_status = db.Column(db.String(50), nullable=False)
    ad_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now_vladivostok)

    product = db.relationship('Product', backref='advertisements')

AVAILABLE_AD_PLATFORMS = [
    'Avito',
    'Telegram',
    'Другое'
]

AVAILABLE_AD_STATUSES = [
    'Активно',
    'Снято',
    'Продано'
]

def ensure_upload_folder():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def get_free_warehouse_slot():
    occupied_slots = {
        product.warehouse_id
        for product in Product.query.filter(Product.current_status.in_(list(WAREHOUSE_UNIQUE_STATUSES))).all()
        if product.warehouse_id
    }

    for number in range(1, 500):
        slot = f'{number:03d}'
        if slot not in occupied_slots:
            return slot

    return None


def is_valid_warehouse_id(value):
    return bool(re.fullmatch(r'\d{3}', value or ''))


def save_uploaded_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    if not filename:
        return None

    ext = os.path.splitext(filename)[1].lower()
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

    if ext not in allowed_extensions:
        return None

    unique_filename = f'{uuid.uuid4().hex}{ext}'
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file_storage.save(full_path)

    return f'uploads/{unique_filename}'


def warehouse_slot_is_busy(warehouse_id, current_status, exclude_product_id=None):
    if current_status not in WAREHOUSE_UNIQUE_STATUSES:
        return False

    query = Product.query.filter(
        Product.warehouse_id == warehouse_id,
        Product.current_status.in_(list(WAREHOUSE_UNIQUE_STATUSES))
    )

    if exclude_product_id is not None:
        query = query.filter(Product.id != exclude_product_id)

    return db.session.query(query.exists()).scalar()

def build_buyer_form_data(request_form):
    return {
        'full_name': request_form.get('buyer_full_name', '').strip(),
        'address': request_form.get('buyer_address', '').strip(),
        'contact_info': request_form.get('buyer_contact_info', '').strip(),
        'source_channel': request_form.get('buyer_source_channel', '').strip(),
        'notes': request_form.get('buyer_notes', '').strip(),
    }

def build_sale_form_data(request_form):
    return {
        'buyer_id': request_form.get('buyer_id', '').strip(),
        'buyer_search': request_form.get('buyer_search', '').strip(),
        'channel': request_form.get('channel', '').strip(),
        'sale_comment': request_form.get('sale_comment', '').strip(),
    }

def add_product_status_history_if_changed(product, new_status):
    old_status = product.current_status
    if old_status != new_status:
        product.current_status = new_status
        db.session.add(ProductStatusHistory(
            product_id=product.id,
            status_name=new_status
        ))

def set_active_ads_to_removed(product_id):
    active_ads = Advertisement.query.filter_by(product_id=product_id, ad_status='Активно').all()
    for ad in active_ads:
        ad.ad_status = 'Снято'

def set_all_ads_to_sold(product_id):
    ads = Advertisement.query.filter(Advertisement.product_id == product_id).all()
    for ad in ads:
        ad.ad_status = 'Продано'

def create_default_fin_types():
    default_types = ['IN', 'OUT']

    for item in default_types:
        exists = FinType.query.filter_by(type=item).first()
        if not exists:
            db.session.add(FinType(type=item))

    db.session.commit()

def build_finance_form_data(request_form):
    return {
        'type': request_form.get('type', '').strip(),
        'op_date': request_form.get('op_date', '').strip(),
        'article': request_form.get('article', '').strip(),
        'amount': request_form.get('amount', '').strip(),
        'product_id': request_form.get('product_id', '').strip(),
        'sale_id': request_form.get('sale_id', '').strip(),
        'comment': request_form.get('comment', '').strip(),
    }
    
def create_default_articles():
    default_articles = [
        'закупка',
        'ремонт',
        'комиссия',
        'продажа',
        'доставка',
        'прочее'
    ]

    for item in default_articles:
        exists = Article.query.filter_by(article=item).first()
        if not exists:
            db.session.add(Article(article=item))

    db.session.commit()

@app.route('/')
def home():
    if session.get('role') in ['ip', 'admin']:
        return redirect(url_for('products'))
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    return redirect(url_for('products'))

app.route('/ip')
def ip_dashboard():
    return redirect(url_for('products'))
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
            return redirect(url_for('products'))
        else:
            flash('Неверный логин или пароль', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/products')

def products():
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    category_id = request.args.get('category_id', '').strip()
    manufacturer = request.args.get('manufacturer', '').strip()
    status = request.args.get('status', '').strip()
    price_from = request.args.get('price_from', '').strip()
    price_to = request.args.get('price_to', '').strip()
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'id_desc').strip()

    query = Product.query.join(Category)

    if category_id:
        query = query.filter(Product.category_id == int(category_id))

    if manufacturer:
        query = query.filter(Product.manufacturer.ilike(f'%{manufacturer}%'))

    if status:
        query = query.filter(Product.current_status == status)

    if search:
        query = query.filter(
            db.or_(
                Product.manufacturer.ilike(f'%{search}%'),
                Product.model.ilike(f'%{search}%'),
                Product.warehouse_id.ilike(f'%{search}%'),
                Product.comments.ilike(f'%{search}%'),
                Product.specifications.ilike(f'%{search}%')
            )
        )

    if price_from:
        try:
            query = query.filter(Product.purchase_price >= float(price_from))
        except ValueError:
            flash('Минимальная цена указана некорректно', 'danger')

    if price_to:
        try:
            query = query.filter(Product.purchase_price <= float(price_to))
        except ValueError:
            flash('Максимальная цена указана некорректно', 'danger')

    if sort_by == 'id_asc':
        query = query.order_by(Product.id.asc())
    elif sort_by == 'id_desc':
        query = query.order_by(Product.id.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Product.purchase_price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.purchase_price.desc())
    else:
        query = query.order_by(Product.id.desc())

    product_list = query.all()
    categories = Category.query.order_by(Category.name).all()

    manufacturers = [
        row[0] for row in db.session.query(Product.manufacturer)
        .filter(Product.manufacturer.isnot(None))
        .distinct()
        .order_by(Product.manufacturer.asc())
        .all()
        if row[0]
    ]

    filters = {
        'category_id': category_id,
        'manufacturer': manufacturer,
        'status': status,
        'price_from': price_from,
        'price_to': price_to,
        'search': search,
        'sort_by': sort_by
    }

    return render_template(
        'products.html',
        products=product_list,
        categories=categories,
        manufacturers=manufacturers,
        statuses=AVAILABLE_STATUSES,
        filters=filters
    ) 

@app.route('/products/create', methods=['GET', 'POST'])
def create_product():
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    categories = Category.query.order_by(Category.name).all()
    suggested_slot = get_free_warehouse_slot()

    if request.method == 'POST':
        form_data = build_product_form_data(request.form)

        category_id = form_data['category_id']
        warehouse_id = form_data['warehouse_id']
        manufacturer = form_data['manufacturer']
        model = form_data['model']
        purchase_price = form_data['purchase_price']
        specifications = form_data['specifications']
        condition_rate = form_data['condition_rate']
        current_status = form_data['current_status']
        comments = form_data['comments']
        image_file = request.files.get('image_file')

        if not category_id or not manufacturer or not model or not condition_rate or not current_status:
            flash('Заполните все обязательные поля', 'danger')
            return render_template(
                'product_form.html',
                product=form_data,
                categories=categories,
                statuses=AVAILABLE_STATUSES,
                suggested_slot=suggested_slot,
                warehouse_locked=False,
                is_edit=False
            )

        if not warehouse_id:
            warehouse_id = suggested_slot or ''
            form_data['warehouse_id'] = warehouse_id

        if not warehouse_id:
            flash('Свободные складские места закончились', 'danger')
            return render_template(
                'product_form.html',
                product=form_data,
                categories=categories,
                statuses=AVAILABLE_STATUSES,
                suggested_slot=suggested_slot,
                warehouse_locked=False,
                is_edit=False
            )

        if not is_valid_warehouse_id(warehouse_id):
            flash('Складской номер должен состоять ровно из 3 цифр', 'danger')
            return render_template(
                'product_form.html',
                product=form_data,
                categories=categories,
                statuses=AVAILABLE_STATUSES,
                suggested_slot=suggested_slot,
                warehouse_locked=False,
                is_edit=False
            )

        try:
            condition_rate_int = int(condition_rate)
            if condition_rate_int < 1 or condition_rate_int > 5:
                flash('Оценка состояния должна быть от 1 до 5', 'danger')
                return render_template(
                    'product_form.html',
                    product=form_data,
                    categories=categories,
                    statuses=AVAILABLE_STATUSES,
                    suggested_slot=suggested_slot,
                    warehouse_locked=False,
                    is_edit=False
                )

            purchase_price_value = None
            if purchase_price:
                purchase_price_value = float(purchase_price)
                if purchase_price_value <= 0:
                    flash('Закупочная цена должна быть больше 0', 'danger')
                    return render_template(
                        'product_form.html',
                        product=form_data,
                        categories=categories,
                        statuses=AVAILABLE_STATUSES,
                        suggested_slot=suggested_slot,
                        warehouse_locked=False,
                        is_edit=False
                    )

            if warehouse_slot_is_busy(warehouse_id, current_status):
                flash('Это складское место уже занято другим активным товаром', 'danger')
                return render_template(
                    'product_form.html',
                    product=form_data,
                    categories=categories,
                    statuses=AVAILABLE_STATUSES,
                    suggested_slot=suggested_slot,
                    warehouse_locked=False,
                    is_edit=False
                )

            image_path = None
            if image_file and image_file.filename:
                image_path = save_uploaded_image(image_file)
                if image_path is None:
                    flash('Допустимы только изображения JPG, JPEG, PNG, GIF, WEBP', 'danger')
                    return render_template(
                        'product_form.html',
                        product=form_data,
                        categories=categories,
                        statuses=AVAILABLE_STATUSES,
                        suggested_slot=suggested_slot,
                        warehouse_locked=False,
                        is_edit=False
                    )

            new_product = Product(
                category_id=int(category_id),
                warehouse_id=warehouse_id,
                manufacturer=manufacturer,
                model=model,
                purchase_price=purchase_price_value,
                image_path=image_path,
                specifications=specifications if specifications else None,
                condition_rate=condition_rate_int,
                current_status=current_status,
                comments=comments if comments else None
            )

            db.session.add(new_product)
            db.session.flush()

            db.session.add(ProductStatusHistory(
                product_id=new_product.id,
                status_name=current_status
            ))

            if purchase_price_value is not None:
                out_type_id = get_fin_type_id_by_code('OUT')
                purchase_article_id = get_article_id_by_name('закупка')

                if out_type_id and purchase_article_id:
                    db.session.add(Finance(
                        type=out_type_id,
                        op_date=now_vladivostok(),
                        article=purchase_article_id,
                        amount=purchase_price_value,
                        product_id=new_product.id,
                        sale_id=None,
                        comment='Автоматически создано при регистрации товара'
                    ))

            db.session.commit()
            flash('Карточка товара успешно создана', 'success')
            return redirect(url_for('products'))

        except ValueError:
            flash('Проверьте корректность числовых полей', 'danger')
            return render_template(
                'product_form.html',
                product=form_data,
                categories=categories,
                statuses=AVAILABLE_STATUSES,
                suggested_slot=suggested_slot,
                warehouse_locked=False,
                is_edit=False
            )

    empty_form_data = {
        'category_id': '',
        'warehouse_id': suggested_slot or '',
        'manufacturer': '',
        'model': '',
        'purchase_price': '',
        'image_path': None,
        'specifications': '',
        'condition_rate': '',
        'current_status': '',
        'comments': '',
    }

    return render_template(
        'product_form.html',
        product=empty_form_data,
        categories=categories,
        statuses=AVAILABLE_STATUSES,
        suggested_slot=suggested_slot,
        warehouse_locked=False,
        is_edit=False
    )
    
@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    db_product = Product.query.get_or_404(product_id)
    categories = Category.query.order_by(Category.name).all()
    warehouse_locked = db_product.current_status in WAREHOUSE_LOCKED_STATUSES

    if request.method == 'POST':
        form_data = build_product_form_data(request.form, image_path=db_product.image_path)

        old_status = db_product.current_status
        old_warehouse_id = db_product.warehouse_id

        category_id = form_data['category_id']
        manufacturer = form_data['manufacturer']
        model = form_data['model']
        purchase_price = form_data['purchase_price']
        specifications = form_data['specifications']
        condition_rate = form_data['condition_rate']
        current_status = form_data['current_status']
        comments = form_data['comments']
        image_file = request.files.get('image_file')

        if warehouse_locked:
            warehouse_id = old_warehouse_id
            form_data['warehouse_id'] = old_warehouse_id or ''
        else:
            warehouse_id = form_data['warehouse_id']

        if not category_id or not manufacturer or not model or not condition_rate or not current_status:
            flash('Заполните все обязательные поля', 'danger')
            return render_template(
                'product_form.html',
                product=form_data,
                categories=categories,
                statuses=AVAILABLE_STATUSES,
                suggested_slot=None,
                warehouse_locked=warehouse_locked,
                is_edit=True
            )

        if not warehouse_id:
            flash('Укажите складской номер', 'danger')
            return render_template(
                'product_form.html',
                product=form_data,
                categories=categories,
                statuses=AVAILABLE_STATUSES,
                suggested_slot=None,
                warehouse_locked=warehouse_locked,
                is_edit=True
            )

        if not is_valid_warehouse_id(warehouse_id):
            flash('Складской номер должен состоять ровно из 3 цифр', 'danger')
            return render_template(
                'product_form.html',
                product=form_data,
                categories=categories,
                statuses=AVAILABLE_STATUSES,
                suggested_slot=None,
                warehouse_locked=warehouse_locked,
                is_edit=True
            )

        try:
            condition_rate_int = int(condition_rate)
            if condition_rate_int < 1 or condition_rate_int > 5:
                flash('Оценка состояния должна быть от 1 до 5', 'danger')
                return render_template(
                    'product_form.html',
                    product=form_data,
                    categories=categories,
                    statuses=AVAILABLE_STATUSES,
                    suggested_slot=None,
                    warehouse_locked=warehouse_locked,
                    is_edit=True
                )

            purchase_price_value = None
            if purchase_price:
                purchase_price_value = float(purchase_price)
                if purchase_price_value <= 0:
                    flash('Закупочная цена должна быть больше 0', 'danger')
                    return render_template(
                        'product_form.html',
                        product=form_data,
                        categories=categories,
                        statuses=AVAILABLE_STATUSES,
                        suggested_slot=None,
                        warehouse_locked=warehouse_locked,
                        is_edit=True
                    )

            if warehouse_slot_is_busy(warehouse_id, current_status, exclude_product_id=db_product.id):
                flash('Это складское место уже занято другим активным товаром', 'danger')
                return render_template(
                    'product_form.html',
                    product=form_data,
                    categories=categories,
                    statuses=AVAILABLE_STATUSES,
                    suggested_slot=None,
                    warehouse_locked=warehouse_locked,
                    is_edit=True
                )

            if image_file and image_file.filename:
                new_image_path = save_uploaded_image(image_file)
                if new_image_path is None:
                    flash('Допустимы только изображения JPG, JPEG, PNG, GIF, WEBP', 'danger')
                    return render_template(
                        'product_form.html',
                        product=form_data,
                        categories=categories,
                        statuses=AVAILABLE_STATUSES,
                        suggested_slot=None,
                        warehouse_locked=warehouse_locked,
                        is_edit=True
                    )
                db_product.image_path = new_image_path
                form_data['image_path'] = new_image_path

            db_product.category_id = int(category_id)
            db_product.warehouse_id = warehouse_id
            db_product.manufacturer = manufacturer
            db_product.model = model
            db_product.purchase_price = purchase_price_value
            db_product.specifications = specifications if specifications else None
            db_product.condition_rate = condition_rate_int
            db_product.current_status = current_status
            db_product.comments = comments if comments else None

            if old_status != current_status:
                db.session.add(ProductStatusHistory(
                    product_id=db_product.id,
                    status_name=current_status
                ))

            db.session.commit()

            if old_status == 'В ремонте' and current_status != 'В ремонте':
                flash('Укажите расход на ремонт товара', 'success')
                return redirect(url_for(
                    'finances',
                    product_id=db_product.id,
                    prefill_repair='1'
                ))

            flash('Карточка товара успешно обновлена', 'success')
            return redirect(url_for('edit_product', product_id=db_product.id))

        except ValueError:
            flash('Проверьте корректность числовых полей', 'danger')
            return render_template(
                'product_form.html',
                product=form_data,
                categories=categories,
                statuses=AVAILABLE_STATUSES,
                suggested_slot=None,
                warehouse_locked=warehouse_locked,
                is_edit=True
            )

    product_data = {
        'id': db_product.id,
        'category_id': db_product.category_id,
        'warehouse_id': db_product.warehouse_id or '',
        'manufacturer': db_product.manufacturer or '',
        'model': db_product.model or '',
        'purchase_price': str(db_product.purchase_price) if db_product.purchase_price is not None else '',
        'image_path': db_product.image_path,
        'specifications': db_product.specifications or '',
        'condition_rate': db_product.condition_rate,
        'current_status': db_product.current_status or '',
        'comments': db_product.comments or '',
        'status_history': db_product.status_history
    }

    return render_template(
        'product_form.html',
        product=product_data,
        categories=categories,
        statuses=AVAILABLE_STATUSES,
        suggested_slot=None,
        warehouse_locked=warehouse_locked,
        is_edit=True
    )
    
@app.route('/advertisements')
def advertisements():
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    platform = request.args.get('platform', '').strip()
    ad_status = request.args.get('ad_status', '').strip()
    manufacturer = request.args.get('manufacturer', '').strip()
    category_id = request.args.get('category_id', '').strip()
    price_from = request.args.get('price_from', '').strip()
    price_to = request.args.get('price_to', '').strip()
    sort_by = request.args.get('sort_by', 'created_desc').strip()

    query = Advertisement.query.join(Product).join(Category)

    if platform:
        query = query.filter(Advertisement.platform == platform)

    if ad_status:
        query = query.filter(Advertisement.ad_status == ad_status)

    if manufacturer:
        query = query.filter(Product.manufacturer == manufacturer)

    if category_id:
        try:
            query = query.filter(Product.category_id == int(category_id))
        except ValueError:
            flash('Категория указана некорректно', 'danger')

    if price_from:
        try:
            query = query.filter(Advertisement.ad_price >= float(price_from))
        except ValueError:
            flash('Минимальная цена указана некорректно', 'danger')

    if price_to:
        try:
            query = query.filter(Advertisement.ad_price <= float(price_to))
        except ValueError:
            flash('Максимальная цена указана некорректно', 'danger')

    if sort_by == 'created_asc':
        query = query.order_by(Advertisement.created_at.asc())
    elif sort_by == 'created_desc':
        query = query.order_by(Advertisement.created_at.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Advertisement.ad_price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Advertisement.ad_price.desc())
    elif sort_by == 'id_asc':
        query = query.order_by(Advertisement.id.asc())
    else:
        query = query.order_by(Advertisement.id.desc())

    ad_list = query.all()

    categories = Category.query.order_by(Category.name).all()

    manufacturers = [
        row[0] for row in db.session.query(Product.manufacturer)
        .filter(Product.manufacturer.isnot(None))
        .distinct()
        .order_by(Product.manufacturer.asc())
        .all()
        if row[0]
    ]

    filters = {
        'platform': platform,
        'ad_status': ad_status,
        'manufacturer': manufacturer,
        'category_id': category_id,
        'price_from': price_from,
        'price_to': price_to,
        'sort_by': sort_by
    }

    return render_template(
        'advertisements.html',
        advertisements=ad_list,
        platforms=AVAILABLE_AD_PLATFORMS,
        ad_statuses=AVAILABLE_AD_STATUSES,
        categories=categories,
        manufacturers=manufacturers,
        filters=filters
    )   
    
@app.route('/products/<int:product_id>/advertisements/create', methods=['GET', 'POST'])
def create_advertisement(product_id):
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    product = Product.query.get_or_404(product_id)

    if product.current_status != 'Готов к продаже':
        flash('Создание объявления доступно только для товаров со статусом «Готов к продаже»', 'danger')
        return redirect(url_for('edit_product', product_id=product.id))

    if request.method == 'POST':
        form_data = build_advertisement_form_data(request.form, product)

        platform = form_data['platform']
        ad_price = form_data['ad_price']
        title = form_data['title']
        description = form_data['description']
        media_urls = form_data['media_urls']
        ad_status = form_data['ad_status']
        ad_url = form_data['ad_url']

        if not platform or not ad_price or not title or not description or not ad_status:
            flash('Заполните все обязательные поля объявления', 'danger')
            return render_template(
                'advertisement_form.html',
                product=product,
                advertisement=form_data,
                platforms=AVAILABLE_AD_PLATFORMS,
                ad_statuses=AVAILABLE_AD_STATUSES
            )

        try:
            ad_price_value = float(ad_price)
            if ad_price_value <= 0:
                flash('Цена в объявлении должна быть больше 0', 'danger')
                return render_template(
                    'advertisement_form.html',
                    product=product,
                    advertisement=form_data,
                    platforms=AVAILABLE_AD_PLATFORMS,
                    ad_statuses=AVAILABLE_AD_STATUSES
                )

            new_advertisement = Advertisement(
                product_id=product.id,
                platform=platform,
                ad_price=ad_price_value,
                title=title,
                description=description,
                media_urls=media_urls if media_urls else None,
                ad_status=ad_status,
                ad_url=ad_url if ad_url else None
            )

            db.session.add(new_advertisement)

            if ad_status == 'Активно' and product.current_status != 'Опубликован':
                old_status = product.current_status
                product.current_status = 'Опубликован'

                if old_status != 'Опубликован':
                    db.session.add(ProductStatusHistory(
                        product_id=product.id,
                        status_name='Опубликован'
                    ))

            db.session.commit()

            flash('Объявление успешно создано', 'success')
            return redirect(url_for('advertisements'))

        except ValueError:
            flash('Проверьте корректность цены объявления', 'danger')
            return render_template(
                'advertisement_form.html',
                product=product,
                advertisement=form_data,
                platforms=AVAILABLE_AD_PLATFORMS,
                ad_statuses=AVAILABLE_AD_STATUSES
            )

    default_title = f'{product.manufacturer} {product.model}'.strip()

    description_parts = []
    if product.specifications:
        description_parts.append(product.specifications)
    if product.comments:
        description_parts.append(f'Комментарий: {product.comments}')

    default_description = '\n\n'.join(description_parts).strip()

    advertisement_data = {
        'platform': '',
        'ad_price': '',
        'title': default_title,
        'description': default_description,
        'media_urls': product.image_path if product.image_path else '',
        'ad_status': 'Активно',
        'ad_url': ''
    }

    return render_template(
        'advertisement_form.html',
        product=product,
        advertisement=advertisement_data,
        platforms=AVAILABLE_AD_PLATFORMS,
        ad_statuses=AVAILABLE_AD_STATUSES
    )
    
@app.route('/buyers', methods=['GET', 'POST'])
def buyers():
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    search = request.args.get('search', '').strip()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        address = request.form.get('address', '').strip()
        contact_info = request.form.get('contact_info', '').strip()
        source_channel = request.form.get('source_channel', '').strip()
        notes = request.form.get('notes', '').strip()

        if not full_name or not contact_info:
            flash('Для создания клиента заполните ФИО/никнейм и контактные данные', 'danger')
        else:
            normalized_phone = normalize_phone(contact_info)
            if not normalized_phone:
                flash('Введите телефон клиента в корректном формате', 'danger')
            else:
                new_buyer = Buyer(
                    full_name=full_name,
                    address=address or None,
                    contact_info=normalized_phone,
                    source_channel=source_channel or None,
                    notes=notes or None
                )
                db.session.add(new_buyer)
                db.session.commit()
                flash('Клиент успешно добавлен', 'success')
                return redirect(url_for('buyers'))

    query = Buyer.query
    if search:
        query = query.filter(Buyer.contact_info.ilike(f'%{search}%'))

    buyer_list = query.order_by(Buyer.id.desc()).all()

    buyer_form = {
        'full_name': '',
        'address': '',
        'contact_info': '',
        'source_channel': '',
        'notes': ''
    }

    return render_template(
        'buyers.html',
        buyers=buyer_list,
        search=search,
        buyer_form=buyer_form
    )
    
@app.route('/products/<int:product_id>/sales/create', methods=['GET', 'POST'])
def create_sale(product_id):
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    product = Product.query.get_or_404(product_id)

    if product.current_status not in ['Готов к продаже', 'Опубликован']:
        flash('Создание сделки доступно только для товаров со статусом «Готов к продаже» или «Опубликован»', 'danger')
        return redirect(url_for('edit_product', product_id=product.id))

    existing_sale = Sale.query.filter_by(product_id=product.id).first()
    if existing_sale and existing_sale.sale_state == 'Активна':
        flash('По этому товару уже существует активная сделка', 'danger')
        return redirect(url_for('sale_detail', sale_id=existing_sale.id))

    buyer_search = request.args.get('buyer_search', '').strip()
    buyers_query = Buyer.query
    if buyer_search:
        buyers_query = buyers_query.filter(Buyer.contact_info.ilike(f'%{buyer_search}%'))
    buyer_list = buyers_query.order_by(Buyer.full_name.asc()).all()
    no_buyer_found = bool(buyer_search) and len(buyer_list) == 0

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create_buyer':
            buyer_data = build_buyer_form_data(request.form)

            if not buyer_data['full_name'] or not buyer_data['contact_info']:
                flash('Для создания покупателя заполните ФИО/никнейм и контактные данные', 'danger')
                sale_data = build_sale_form_data(request.form)
                return render_template(
                    'sale_form.html',
                    product=product,
                    buyers=buyer_list,
                    sale=sale_data,
                    buyer_form=buyer_data,
                    show_buyer_form=True,
                    no_buyer_found=no_buyer_found
                )

            normalized_phone = normalize_phone(buyer_data['contact_info'])

            if not normalized_phone:
                flash('Введите телефон в корректном формате', 'danger')
                sale_data = build_sale_form_data(request.form)
                return render_template(
                    'sale_form.html',
                    product=product,
                    buyers=buyer_list,
                    sale=sale_data,
                    buyer_form=buyer_data,
                    show_buyer_form=True,
                    no_buyer_found=no_buyer_found
                )

            new_buyer = Buyer(
                full_name=buyer_data['full_name'],
                address=buyer_data['address'] or None,
                contact_info=normalized_phone,
                source_channel=buyer_data['source_channel'] or None,
                notes=buyer_data['notes'] or None
            )
            
            db.session.add(new_buyer)
            db.session.commit()

            flash('Покупатель успешно создан. Теперь можно оформить сделку.', 'success')
            return redirect(url_for('create_sale', product_id=product.id, buyer_search=new_buyer.contact_info))

        sale_data = build_sale_form_data(request.form)

        if not sale_data['buyer_id']:
            flash('Выберите покупателя для сделки', 'danger')
            return render_template(
                'sale_form.html',
                product=product,
                buyers=buyer_list,
                sale=sale_data,
                buyer_form=build_buyer_form_data(request.form),
                show_buyer_form=request.form.get('show_buyer_form') == '1',
                no_buyer_found=no_buyer_found
            )

        buyer = Buyer.query.get(sale_data['buyer_id'])
        if not buyer:
            flash('Выбранный покупатель не найден', 'danger')
            return render_template(
                'sale_form.html',
                product=product,
                buyers=buyer_list,
                sale=sale_data,
                buyer_form=build_buyer_form_data(request.form),
                show_buyer_form=request.form.get('show_buyer_form') == '1',
                no_buyer_found=no_buyer_found
            )

        new_sale = Sale(
            product_id=product.id,
            buyer_id=buyer.id,
            sale_state='Активна',
            sale_begin_date=now_vladivostok(),
            channel=sale_data['channel'] or None,
            sale_comment=sale_data['sale_comment'] or None
        )

        db.session.add(new_sale)

        add_product_status_history_if_changed(product, 'Зарезервирован')
        set_active_ads_to_removed(product.id)

        db.session.commit()

        flash('Сделка успешно создана', 'success')
        return redirect(url_for('sale_detail', sale_id=new_sale.id))

    sale_data = {
        'buyer_id': '',
        'buyer_search': buyer_search,
        'channel': '',
        'sale_comment': ''
    }

    empty_buyer_form = {
        'full_name': '',
        'address': '',
        'contact_info': buyer_search,
        'source_channel': '',
        'notes': ''
    }

    return render_template(
        'sale_form.html',
        product=product,
        buyers=buyer_list,
        sale=sale_data,
        buyer_form=empty_buyer_form,
        show_buyer_form=False,
        no_buyer_found=no_buyer_found
    )

@app.route('/sales/<int:sale_id>')
def sale_detail(sale_id):
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    sale = Sale.query.get_or_404(sale_id)
    return render_template('sale_detail.html', sale=sale)

@app.route('/sales/<int:sale_id>/complete', methods=['POST'])
def complete_sale(sale_id):
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    sale = Sale.query.get_or_404(sale_id)

    if sale.sale_state != 'Активна':
        flash('Завершить можно только активную сделку', 'danger')
        return redirect(url_for('sale_detail', sale_id=sale.id))

    sale.sale_state = 'Завершена'
    sale.sale_date = now_vladivostok()

    add_product_status_history_if_changed(sale.product, 'Продан')
    set_all_ads_to_sold(sale.product_id)

    in_type_id = get_fin_type_id_by_code('IN')
    sale_article_id = get_article_id_by_name('продажа')

    last_ad = Advertisement.query.filter_by(product_id=sale.product_id).order_by(Advertisement.created_at.desc()).first()

    sale_amount = None
    if last_ad and last_ad.ad_price is not None:
        sale_amount = float(last_ad.ad_price)

    finance_created = False

    if not in_type_id:
        flash('Не найден тип финансовой операции IN. Проверьте справочник fin_type.', 'danger')
    elif not sale_article_id:
        flash('Не найдена статья "продажа". Проверьте справочник article.', 'danger')
    elif sale_amount is None or sale_amount <= 0:
        flash('Не удалось создать доход: у товара нет объявления с корректной ценой продажи.', 'danger')
    else:
        db.session.add(Finance(
            type=in_type_id,
            op_date=now_vladivostok(),
            article=sale_article_id,
            amount=sale_amount,
            product_id=sale.product_id,
            sale_id=sale.id,
            comment='Автоматически создано при завершении сделки'
        ))
        finance_created = True

    db.session.commit()

    if finance_created:
        flash('Сделка успешно завершена, доход по продаже добавлен', 'success')
    else:
        flash('Сделка завершена, но запись о доходе не была создана', 'warning')

    return redirect(url_for('sale_detail', sale_id=sale.id))

@app.route('/sales')
def sales():
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    state = request.args.get('state', '').strip()

    query = Sale.query.join(Product).join(Buyer)

    if state:
        query = query.filter(Sale.sale_state == state)

    sale_list = query.order_by(Sale.sale_begin_date.desc()).all()
    return render_template('sales.html', sales=sale_list, state=state, states=AVAILABLE_SALE_STATES)

@app.route('/reports')
def reports():
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    product_status = request.args.get('product_status', '').strip()
    category_id = request.args.get('category_id', '').strip()

    products_sort = request.args.get('products_sort', 'id_desc').strip()
    sales_sort = request.args.get('sales_sort', 'date_desc').strip()
    finances_sort = request.args.get('finances_sort', 'date_desc').strip()
    sold_sort = request.args.get('sold_sort', 'sale_date_desc').strip()

    date_from_value = None
    date_to_value = None

    try:
        if date_from:
            date_from_value = datetime.strptime(date_from, '%Y-%m-%d')
        if date_to:
            date_to_value = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        flash('Некорректный формат даты в фильтре отчетов', 'danger')

    products_query = Product.query.join(Category)
    sales_query = Sale.query.join(Product).join(Buyer)
    finances_query = Finance.query.join(FinType).join(Article)
    ads_query = Advertisement.query

    if product_status:
        products_query = products_query.filter(Product.current_status == product_status)

    if category_id:
        try:
            products_query = products_query.filter(Product.category_id == int(category_id))
        except ValueError:
            flash('Некорректная категория в фильтре отчетов', 'danger')

    if date_from_value:
        sales_query = sales_query.filter(Sale.sale_begin_date >= date_from_value)
        finances_query = finances_query.filter(Finance.op_date >= date_from_value)
        ads_query = ads_query.filter(Advertisement.created_at >= date_from_value)

    if date_to_value:
        sales_query = sales_query.filter(Sale.sale_begin_date <= date_to_value)
        finances_query = finances_query.filter(Finance.op_date <= date_to_value)
        ads_query = ads_query.filter(Advertisement.created_at <= date_to_value)

    if products_sort == 'id_asc':
        products_query = products_query.order_by(Product.id.asc())
    elif products_sort == 'id_desc':
        products_query = products_query.order_by(Product.id.desc())
    elif products_sort == 'price_asc':
        products_query = products_query.order_by(Product.purchase_price.asc())
    elif products_sort == 'price_desc':
        products_query = products_query.order_by(Product.purchase_price.desc())
    elif products_sort == 'status_asc':
        products_query = products_query.order_by(Product.current_status.asc())
    else:
        products_query = products_query.order_by(Product.id.desc())

    if sales_sort == 'id_asc':
        sales_query = sales_query.order_by(Sale.id.asc())
    elif sales_sort == 'id_desc':
        sales_query = sales_query.order_by(Sale.id.desc())
    elif sales_sort == 'date_asc':
        sales_query = sales_query.order_by(Sale.sale_begin_date.asc())
    else:
        sales_query = sales_query.order_by(Sale.sale_begin_date.desc())

    if finances_sort == 'id_asc':
        finances_query = finances_query.order_by(Finance.id.asc())
    elif finances_sort == 'id_desc':
        finances_query = finances_query.order_by(Finance.id.desc())
    elif finances_sort == 'amount_asc':
        finances_query = finances_query.order_by(Finance.amount.asc())
    elif finances_sort == 'amount_desc':
        finances_query = finances_query.order_by(Finance.amount.desc())
    elif finances_sort == 'date_asc':
        finances_query = finances_query.order_by(Finance.op_date.asc())
    else:
        finances_query = finances_query.order_by(Finance.op_date.desc())

    products = products_query.all()
    sales = sales_query.all()
    finances = finances_query.all()
    advertisements = ads_query.all()

    sold_products = []
    for sale in sales:
        if sale.sale_state == 'Завершена':
            sold_products.append(sale)

    if sold_sort == 'id_asc':
        sold_products.sort(key=lambda x: x.product.id if x.product else 0)
    elif sold_sort == 'id_desc':
        sold_products.sort(key=lambda x: x.product.id if x.product else 0, reverse=True)
    elif sold_sort == 'sale_date_asc':
        sold_products.sort(key=lambda x: x.sale_date or datetime.min)
    else:
        sold_products.sort(key=lambda x: x.sale_date or datetime.min, reverse=True)

    income_total = 0.0
    expense_total = 0.0

    for item in finances:
        if item.fin_type.type == 'IN':
            income_total += float(item.amount)
        elif item.fin_type.type == 'OUT':
            expense_total += float(item.amount)

    active_ads_count = sum(1 for ad in advertisements if ad.ad_status == 'Активно')
    active_sales_count = sum(1 for sale in sales if sale.sale_state == 'Активна')
    completed_sales_count = sum(1 for sale in sales if sale.sale_state == 'Завершена')

    repair_count = sum(1 for product in Product.query.all() if product.current_status == 'В ремонте')
    reserved_count = sum(1 for product in Product.query.all() if product.current_status == 'Зарезервирован')
    sold_count = sum(1 for product in Product.query.all() if product.current_status == 'Продан')

    product_profit_rows = []
    for product in products:
        expense_sum = 0.0
        income_sum = 0.0

        for fin in product.finances:
            if date_from_value and fin.op_date < date_from_value:
                continue
            if date_to_value and fin.op_date > date_to_value:
                continue

            if fin.fin_type.type == 'OUT':
                expense_sum += float(fin.amount)
            elif fin.fin_type.type == 'IN':
                income_sum += float(fin.amount)

        product_profit_rows.append({
            'product': product,
            'expense': expense_sum,
            'income': income_sum,
            'profit': income_sum - expense_sum
        })

    expense_by_article = {}
    for item in finances:
        if item.fin_type.type == 'OUT':
            article_name = item.article_ref.article
            expense_by_article.setdefault(article_name, 0.0)
            expense_by_article[article_name] += float(item.amount)

    expense_by_article_rows = [
        {'article': article, 'amount': amount}
        for article, amount in expense_by_article.items()
    ]
    expense_by_article_rows.sort(key=lambda x: x['amount'], reverse=True)

    sales_by_channel = {}
    for sale in sales:
        channel_name = sale.channel.strip() if sale.channel else 'Не указан'
        sales_by_channel.setdefault(channel_name, 0)
        sales_by_channel[channel_name] += 1

    sales_by_channel_rows = [
        {'channel': channel, 'count': count}
        for channel, count in sales_by_channel.items()
    ]
    sales_by_channel_rows.sort(key=lambda x: x['count'], reverse=True)

    summary = {
        'products_count': len(products),
        'active_ads_count': active_ads_count,
        'active_sales_count': active_sales_count,
        'completed_sales_count': completed_sales_count,
        'income_total': income_total,
        'expense_total': expense_total,
        'profit_total': income_total - expense_total,
        'repair_count': repair_count,
        'reserved_count': reserved_count,
        'sold_count': sold_count
    }

    categories = Category.query.order_by(Category.name.asc()).all()

    filters = {
        'date_from': date_from,
        'date_to': date_to,
        'product_status': product_status,
        'category_id': category_id,
        'products_sort': products_sort,
        'sales_sort': sales_sort,
        'finances_sort': finances_sort,
        'sold_sort': sold_sort
    }

    return render_template(
        'reports.html',
        summary=summary,
        products=products,
        sales=sales,
        finances=finances,
        sold_products=sold_products,
        product_profit_rows=product_profit_rows,
        expense_by_article_rows=expense_by_article_rows,
        sales_by_channel_rows=sales_by_channel_rows,
        filters=filters,
        categories=categories,
        statuses=AVAILABLE_STATUSES + ['Опубликован']
    )
    
@app.route('/finances', methods=['GET', 'POST'])
def finances():
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    fin_types = FinType.query.order_by(FinType.id.asc()).all()
    articles = Article.query.order_by(Article.article.asc()).all()
    products = Product.query.order_by(Product.id.desc()).all()
    sales_list = Sale.query.order_by(Sale.id.desc()).all()

    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    prefill_repair = request.args.get('prefill_repair', '').strip()
    prefill_product_id = request.args.get('product_id', '').strip()

    if request.method == 'POST':
        form_data = build_finance_form_data(request.form)

        type_id = form_data['type']
        op_date = form_data['op_date']
        article_id = form_data['article']
        amount = form_data['amount']
        product_id = form_data['product_id']
        sale_id = form_data['sale_id']
        comment = form_data['comment']

        if not type_id or not article_id or not amount:
            flash('Заполните обязательные поля финансовой операции', 'danger')
        else:
            try:
                amount_value = float(amount)
                if amount_value <= 0:
                    flash('Сумма операции должна быть больше 0', 'danger')
                else:
                    op_date_value = now_vladivostok()

                    if product_id:
                        product_exists = Product.query.get(product_id)
                        if not product_exists:
                            flash('Указанный товар не найден', 'danger')
                            raise ValueError

                    if sale_id:
                        sale_exists = Sale.query.get(sale_id)
                        if not sale_exists:
                            flash('Указанная сделка не найдена', 'danger')
                            raise ValueError

                    new_finance = Finance(
                        type=int(type_id),
                        op_date=op_date_value,
                        article=int(article_id),
                        amount=amount_value,
                        product_id=int(product_id) if product_id else None,
                        sale_id=int(sale_id) if sale_id else None,
                        comment=comment or None
                    )

                    db.session.add(new_finance)
                    db.session.commit()

                    flash('Финансовая операция успешно добавлена', 'success')
                    return redirect(url_for('finances'))

            except ValueError:
                if not get_flashed_messages():
                    flash('Проверьте корректность даты и суммы', 'danger')

        query = Finance.query.join(FinType).join(Article)
        try:
            if date_from:
                date_from_value = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Finance.op_date >= date_from_value)

            if date_to:
                date_to_value = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(Finance.op_date <= date_to_value)
        except ValueError:
            flash('Некорректный формат даты в фильтре', 'danger')

        finance_list = query.order_by(Finance.op_date.desc()).all()

        return render_template(
            'finances.html',
            finance_form=form_data,
            finances=finance_list,
            fin_types=fin_types,
            articles=articles,
            products=products,
            sales_list=sales_list,
            filters={'date_from': date_from, 'date_to': date_to}
        )

    query = Finance.query.join(FinType).join(Article)

    try:
        if date_from:
            date_from_value = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Finance.op_date >= date_from_value)

        if date_to:
            date_to_value = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_value = date_to_value.replace(hour=23, minute=59, second=59)
            query = query.filter(Finance.op_date <= date_to_value)
    except ValueError:
        flash('Некорректный формат даты в фильтре', 'danger')

    finance_list = query.order_by(Finance.op_date.desc()).all()

    empty_form = {
    'type': '',
    'op_date': to_datetime_local_value(now_vladivostok()),
    'article': '',
    'amount': '',
    'product_id': '',
    'sale_id': '',
    'comment': ''
}

    if prefill_repair == '1':
        out_type_id = get_fin_type_id_by_code('OUT')
        repair_article_id = get_article_id_by_name('ремонт')

        empty_form['type'] = str(out_type_id) if out_type_id else ''
        empty_form['article'] = str(repair_article_id) if repair_article_id else ''
        empty_form['product_id'] = prefill_product_id
        empty_form['comment'] = 'Расход на ремонт товара'

    return render_template(
        'finances.html',
        finance_form=empty_form,
        finances=finance_list,
        fin_types=fin_types,
        articles=articles,
        products=products,
        sales_list=sales_list,
        filters={'date_from': date_from, 'date_to': date_to}
    )


def normalize_phone(value):
    digits = re.sub(r'\D', '', value or '')

    if not digits:
        return ''

    if digits.startswith('8'):
        digits = '7' + digits[1:]

    if not digits.startswith('7'):
        digits = '7' + digits

    digits = digits[:11]

    if len(digits) != 11:
        return ''

    return f'+7({digits[1:4]})-{digits[4:7]}-{digits[7:9]}-{digits[9:11]}'

def build_product_form_data(request_form, image_path=None):
    return {
        'category_id': request_form.get('category_id', '').strip(),
        'warehouse_id': request_form.get('warehouse_id', '').strip(),
        'manufacturer': request_form.get('manufacturer', '').strip(),
        'model': request_form.get('model', '').strip(),
        'purchase_price': request_form.get('purchase_price', '').strip(),
        'image_path': image_path,
        'specifications': request_form.get('specifications', '').strip(),
        'condition_rate': request_form.get('condition_rate', '').strip(),
        'current_status': request_form.get('current_status', '').strip(),
        'comments': request_form.get('comments', '').strip(),
    }
    
def build_advertisement_form_data(request_form, product):
    default_title = f'{product.manufacturer} {product.model}'.strip()

    description_parts = []
    if product.specifications:
        description_parts.append(product.specifications)
    if product.comments:
        description_parts.append(f'Комментарий: {product.comments}')

    default_description = '\n\n'.join(description_parts).strip()

    return {
        'platform': request_form.get('platform', '').strip(),
        'ad_price': request_form.get('ad_price', '').strip(),
        'title': request_form.get('title', default_title).strip() or default_title,
        'description': request_form.get('description', default_description).strip() or default_description,
        'media_urls': request_form.get('media_urls', '').strip(),
        'ad_status': request_form.get('ad_status', 'Активно').strip() or 'Активно',
        'ad_url': request_form.get('ad_url', '').strip(),
    }

def create_test_users():
    admin_exists = User.query.filter_by(username='admin').first()
    ip_exists = User.query.filter_by(username='ip_user').first()

    if not admin_exists:
        db.session.add(User(username='admin', password='123', role='admin'))

    if not ip_exists:
        db.session.add(User(username='ip_user', password='123', role='ip'))

    db.session.commit()
    
def get_fin_type_id_by_code(code):
    fin_type = FinType.query.filter_by(type=code).first()
    return fin_type.id if fin_type else None


def get_article_id_by_name(name):
    article = Article.query.filter_by(article=name).first()
    return article.id if article else None


def to_datetime_local_value(dt):
    if not dt:
        return ''
    return dt.strftime('%Y-%m-%dT%H:%M')

def create_default_categories():
    default_categories = [
        'Электроника',
        'Инструменты',
        'Бытовая техника',
        'Комплектующие'
    ]

    for category_name in default_categories:
        exists = Category.query.filter_by(name=category_name).first()
        if not exists:
            db.session.add(Category(name=category_name))

    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        ensure_upload_folder()
        db.create_all()
        create_test_users()
        create_default_categories()
        create_default_fin_types()
        create_default_articles()

    app.run(debug=True)