from datetime import datetime
import os
import re
import uuid

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
db = SQLAlchemy(app)


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
    changed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

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
            flash('Неверный логин или пароль', 'danger')

    return render_template('login.html')


@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', username=session.get('username'))


@app.route('/ip')
def ip_dashboard():
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))
    return render_template('ip_dashboard.html', username=session.get('username'))


@app.route('/products')
def products():
    if session.get('role') not in ['ip', 'admin']:
        return redirect(url_for('login'))

    category_id = request.args.get('category_id', '').strip()
    manufacturer = request.args.get('manufacturer', '').strip()
    status = request.args.get('status', '').strip()
    price_from = request.args.get('price_from', '').strip()
    price_to = request.args.get('price_to', '').strip()
    sort_by = request.args.get('sort_by', 'id_desc').strip()

    query = Product.query.join(Category)

    if category_id:
        query = query.filter(Product.category_id == int(category_id))

    if manufacturer:
        query = query.filter(Product.manufacturer.ilike(f'%{manufacturer}%'))

    if status:
        query = query.filter(Product.current_status == status)

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
        query = query.order_by(Product.purchase_price.asc().nullslast())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.purchase_price.desc().nullslast())
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
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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

    app.run(debug=True)