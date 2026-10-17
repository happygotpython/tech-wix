import os
import sqlite3
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'techwix_secure_secret_key')

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect('techwix.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                condition TEXT NOT NULL,
                price REAL NOT NULL,
                storage TEXT,
                image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_media (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                file_url TEXT NOT NULL,
                media_type TEXT DEFAULT 'image'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer_showcase (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                media_url TEXT NOT NULL,
                media_type TEXT DEFAULT 'image',
                customer_name TEXT,
                caption TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('SELECT COUNT(*) FROM products')
        if cursor.fetchone()[0] == 0:
            sample_products = [
                ("iPhone 14 Pro Max", "Phones", "Brand New", 1450000.00, "256GB / 6GB RAM", "https://images.unsplash.com/photo-1678685888221-cda773a3dcdb?auto=format&fit=crop&q=80&w=600"),
                ("MacBook Pro 16 M3", "Laptops", "UK Used", 2850000.00, "512GB / 18GB RAM", "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=600"),
                ("iPad Air 5th Gen", "iPads", "Brand New", 750000.00, "64GB / WiFi", "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&q=80&w=600"),
                ("Samsung Galaxy S23 Ultra", "Phones", "Nigeria Used", 980000.00, "512GB / 12GB RAM", "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&q=80&w=600")
            ]
            for p in sample_products:
                cursor.execute('''
                    INSERT INTO products (name, category, condition, price, storage, image)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                ''', p)
                pid = cursor.fetchone()[0]
                cursor.execute('INSERT INTO product_media (product_id, file_url, media_type) VALUES (%s, %s, %s)', (pid, p[5], 'image'))
        
        conn.commit()
    else:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    price REAL NOT NULL,
                    storage TEXT,
                    image TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS product_media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    file_url TEXT NOT NULL,
                    media_type TEXT DEFAULT 'image',
                    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS customer_showcase (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    media_url TEXT NOT NULL,
                    media_type TEXT DEFAULT 'image',
                    customer_name TEXT,
                    caption TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM products')
            if cursor.fetchone()[0] == 0:
                sample_products = [
                    ("iPhone 14 Pro Max", "Phones", "Brand New", 1450000.00, "256GB / 6GB RAM", "https://images.unsplash.com/photo-1678685888221-cda773a3dcdb?auto=format&fit=crop&q=80&w=600"),
                    ("MacBook Pro 16 M3", "Laptops", "UK Used", 2850000.00, "512GB / 18GB RAM", "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=600"),
                    ("iPad Air 5th Gen", "iPads", "Brand New", 750000.00, "64GB / WiFi", "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&q=80&w=600"),
                    ("Samsung Galaxy S23 Ultra", "Phones", "Nigeria Used", 980000.00, "512GB / 12GB RAM", "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&q=80&w=600")
                ]
                for p in sample_products:
                    cursor.execute('''
                        INSERT INTO products (name, category, condition, price, storage, image)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', p)
                    pid = cursor.lastrowid
                    cursor.execute('INSERT INTO product_media (product_id, file_url, media_type) VALUES (?, ?, ?)', (pid, p[5], 'image'))
    conn.close()

init_db()

ADMIN_USER = "admin"
ADMIN_PASS = "techwix123"

@app.route('/', methods=['GET', 'POST'])
def index():
    contact_success = False
    if request.method == 'POST' and 'message' in request.form:
        contact_success = True

    category = request.args.get('category')
    condition = request.args.get('condition')
    search_query = request.args.get('q', '').strip()
    sort = request.args.get('sort', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    conn = get_db()
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if category:
        query += " AND category = %s" if DATABASE_URL else " AND category = ?"
        params.append(category)
    
    if condition == 'New':
        query += " AND condition = 'Brand New'"
    elif condition == 'Old':
        query += " AND condition IN ('UK Used', 'Nigeria Used')"
    elif condition:
        query += " AND condition = %s" if DATABASE_URL else " AND condition = ?"
        params.append(condition)

    if search_query:
        query += " AND name LIKE %s" if DATABASE_URL else " AND name LIKE ?"
        params.append(f"%{search_query}%")
    if min_price is not None:
        query += " AND price >= %s" if DATABASE_URL else " AND price >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND price <= %s" if DATABASE_URL else " AND price <= ?"
        params.append(max_price)

    if sort == 'price_asc':
        query += " ORDER BY price ASC"
    elif sort == 'price_desc':
        query += " ORDER BY price DESC"
    else:
        query += " ORDER BY id DESC"

    cursor = conn.cursor()
    cursor.execute(query, params)
    
    if DATABASE_URL:
        columns = [desc[0] for desc in cursor.description]
        products = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM customer_showcase ORDER BY id DESC")
        sc_cols = [d[0] for d in cursor.description]
        showcase_items = [dict(zip(sc_cols, r)) for r in cursor.fetchall()]
    else:
        products = cursor.fetchall()
        cursor.execute("SELECT * FROM customer_showcase ORDER BY id DESC")
        showcase_items = cursor.fetchall()
        
    conn.close()

    return render_template('index.html', products=products, showcase_items=showcase_items, current_category=category, current_condition=condition, search_query=search_query, current_sort=sort, min_price=min_price, max_price=max_price, contact_success=contact_success)

@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        if rating:
            if DATABASE_URL:
                cursor.execute('INSERT INTO reviews (product_id, rating, comment) VALUES (%s, %s, %s)', (product_id, int(rating), comment))
                conn.commit()
            else:
                with conn:
                    conn.execute('INSERT INTO reviews (product_id, rating, comment) VALUES (?, ?, ?)', (product_id, int(rating), comment))
        conn.close()
        return redirect(url_for('product_detail', product_id=product_id))

    if DATABASE_URL:
        cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        prod_row = cursor.fetchone()
        if prod_row:
            cols = [d[0] for d in cursor.description]
            product = dict(zip(cols, prod_row))
        else:
            product = None
    else:
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
    
    if not product:
        conn.close()
        return redirect(url_for('index'))

    if DATABASE_URL:
        cursor.execute('SELECT * FROM product_media WHERE product_id = %s', (product_id,))
        media_cols = [d[0] for d in cursor.description]
        media_items = [dict(zip(media_cols, r)) for r in cursor.fetchall()]
        
        cursor.execute('SELECT * FROM reviews WHERE product_id = %s ORDER BY id DESC', (product_id,))
        rev_cols = [d[0] for d in cursor.description]
        reviews = [dict(zip(rev_cols, r)) for r in cursor.fetchall()]
    else:
        cursor.execute('SELECT * FROM product_media WHERE product_id = ?', (product_id,))
        media_items = cursor.fetchall()
        cursor.execute('SELECT * FROM reviews WHERE product_id = ? ORDER BY id DESC', (product_id,))
        reviews = cursor.fetchall()
        
    conn.close()

    if not media_items and product['image']:
        media_items = [{'file_url': product['image'], 'media_type': 'image'}]

    return render_template('product.html', product=product, media_items=media_items, reviews=reviews)

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        condition = request.form.get('condition')
        price = float(request.form.get('price'))
        storage = request.form.get('storage')
        
        main_image_url = 'https://via.placeholder.com/400'
        
        try:
            file = request.files.get('main_image')
            if file and file.filename != '':
                file.stream.seek(0)
                upload_res = cloudinary.uploader.upload(file.stream, folder="techwix_assets", resource_type="auto")
                main_image_url = upload_res.get('secure_url')
            elif request.form.get('image_url'):
                main_image_url = request.form.get('image_url')
        except Exception as e:
            return f"Main image upload error: {e}", 500

        conn = get_db()
        cursor = conn.cursor()
        
        try:
            if DATABASE_URL:
                cursor.execute('''
                    INSERT INTO products (name, category, condition, price, storage, image)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                ''', (name, category, condition, price, storage, main_image_url))
                pid = cursor.fetchone()[0]
                cursor.execute('INSERT INTO product_media (product_id, file_url, media_type) VALUES (%s, %s, %s)', (pid, main_image_url, 'image'))
                conn.commit()
            else:
                with conn:
                    cursor.execute('''
                        INSERT INTO products (name, category, condition, price, storage, image)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (name, category, condition, price, storage, main_image_url))
                    pid = cursor.lastrowid
                    cursor.execute('INSERT INTO product_media (product_id, file_url, media_type) VALUES (?, ?, ?)', (pid, main_image_url, 'image'))

            gallery_files = request.files.getlist('gallery_files')
            for g_file in gallery_files:
                if g_file and g_file.filename != '':
                    g_file.stream.seek(0)
                    g_upload = cloudinary.uploader.upload(g_file.stream, folder="techwix_assets", resource_type="auto")
                    file_url = g_upload.get('secure_url')
                    resource_type = g_upload.get('resource_type')
                    media_type = 'video' if resource_type == 'video' else 'image'
                    
                    if DATABASE_URL:
                        cursor.execute('INSERT INTO product_media (product_id, file_url, media_type) VALUES (%s, %s, %s)', (pid, file_url, media_type))
                        conn.commit()
                    else:
                        with conn:
                            cursor.execute('INSERT INTO product_media (product_id, file_url, media_type) VALUES (?, ?, ?)', (pid, file_url, media_type))
        except Exception as db_err:
            if DATABASE_URL:
                conn.rollback()
            return f"Database or Upload error: {db_err}", 500
        finally:
            conn.close()

        return redirect(url_for('index'))

    return render_template('add_product.html')

@app.route('/admin/showcase/add', methods=['GET', 'POST'])
def add_showcase():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        customer_name = request.form.get('customer_name')
        caption = request.form.get('caption')
        
        media_url = ''
        media_type = 'image'
        
        try:
            file = request.files.get('media_file')
            if file and file.filename != '':
                file.stream.seek(0)
                upload_res = cloudinary.uploader.upload(file.stream, folder="techwix_assets", resource_type="auto")
                media_url = upload_res.get('secure_url')
                if upload_res.get('resource_type') == 'video':
                    media_type = 'video'
        except Exception as e:
            return f"Showcase upload error: {e}", 500

        conn = get_db()
        cursor = conn.cursor()
        try:
            if DATABASE_URL:
                cursor.execute('''
                    INSERT INTO customer_showcase (title, media_url, media_type, customer_name, caption)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (title, media_url, media_type, customer_name, caption))
                conn.commit()
            else:
                with conn:
                    cursor.execute('''
                        INSERT INTO customer_showcase (title, media_url, media_type, customer_name, caption)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (title, media_url, media_type, customer_name, caption))
        except Exception as db_err:
            if DATABASE_URL:
                conn.rollback()
            return f"Database error during showcase add: {db_err}", 500
        finally:
            conn.close()

        return redirect(url_for('index'))

    return render_template('add_showcase.html')

@app.route('/admin/manage')
def admin_manage():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products ORDER BY id DESC')
    
    if DATABASE_URL:
        cols = [d[0] for d in cursor.description]
        products = [dict(zip(cols, r)) for r in cursor.fetchall()]
    else:
        products = cursor.fetchall()
        
    conn.close()
    return render_template('manage_products.html', products=products)

@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
def admin_edit(product_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        row = cursor.fetchone()
        product = dict(zip([d[0] for d in cursor.description], row)) if row else None
    else:
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
    
    if not product:
        conn.close()
        return redirect(url_for('admin_manage'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        condition = request.form.get('condition')
        price = float(request.form.get('price'))
        storage = request.form.get('storage')
        
        image_url = product['image']
        try:
            file = request.files.get('main_image')
            if file and file.filename != '':
                file.stream.seek(0)
                upload_res = cloudinary.uploader.upload(file.stream, folder="techwix_assets", resource_type="auto")
                image_url = upload_res.get('secure_url')
            elif request.form.get('image_url'):
                image_url = request.form.get('image_url')
        except Exception as e:
            return f"Edit image upload error: {e}", 500
            
        if DATABASE_URL:
            cursor.execute('''
                UPDATE products SET name = %s, category = %s, condition = %s, price = %s, storage = %s, image = %s
                WHERE id = %s
            ''', (name, category, condition, price, storage, image_url, product_id))
            conn.commit()
        else:
            with conn:
                conn.execute('''
                    UPDATE products SET name = ?, category = ?, condition = ?, price = ?, storage = ?, image = ?
                    WHERE id = ?
                ''', (name, category, condition, price, storage, image_url, product_id))
        conn.close()
        return redirect(url_for('admin_manage'))
        
    conn.close()
    return render_template('edit_product.html', product=product)

@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def admin_delete(product_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
    else:
        with conn:
            conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.close()
    return redirect(url_for('admin_manage'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session.permanent = True
            session['is_admin'] = True
            return redirect(url_for('index'))
        error = 'Invalid credentials'
    return render_template('admin.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    cart_session = session.get('cart', {})
    cart_items = []
    total = 0
    if cart_session:
        ids = [int(k) for k in cart_session.keys()]
        conn = get_db()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            placeholders = ','.join(['%s'] * len(ids))
            cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", ids)
            cols = [d[0] for d in cursor.description]
            products = [dict(zip(cols, r)) for r in cursor.fetchall()]
        else:
            placeholders = ','.join(['?'] * len(ids))
            cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", ids)
            products = cursor.fetchall()
            
        conn.close()

        for p in products:
            pid_str = str(p['id'])
            qty = cart_session.get(pid_str, 1)
            subtotal = p['price'] * qty
            total += subtotal
            cart_items.append({
                'id': p['id'],
                'name': p['name'],
                'price': p['price'],
                'image': p['image'],
                'quantity': qty,
                'subtotal': subtotal
            })
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    cart = session.get('cart', {})
    pid_str = str(product_id)
    cart[pid_str] = cart.get(pid_str, 0) + 1
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/cart/clear')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart'))

if __name__ == '__main__':
    app.run(debug=True)