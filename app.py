from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============ DATABASE MODELS ============
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    current_stock = db.Column(db.Integer, default=0)
    min_threshold = db.Column(db.Integer, default=10)
    max_threshold = db.Column(db.Integer, default=100)
    unit_price = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product_name = db.Column(db.String(100))
    type = db.Column(db.String(10))
    quantity = db.Column(db.Integer)
    reason = db.Column(db.String(200))
    username = db.Column(db.String(80))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product_name = db.Column(db.String(100))
    alert_type = db.Column(db.String(20))
    message = db.Column(db.String(500))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============ CREATE DATABASE AND SAMPLE DATA ============
with app.app_context():
    db.drop_all()
    db.create_all()
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@inventory.com',
        password=generate_password_hash('admin123', method='pbkdf2:sha256'),
        role='admin'
    )
    db.session.add(admin)
    
    # Add sample products
    products = [
        Product(name='Laptop Pro X', category='Electronics', current_stock=5, min_threshold=10, max_threshold=50, unit_price=1200),
        Product(name='Wireless Mouse', category='Electronics', current_stock=25, min_threshold=15, max_threshold=100, unit_price=29.99),
        Product(name='USB-C Cable', category='Accessories', current_stock=8, min_threshold=10, max_threshold=200, unit_price=19.99),
        Product(name='Desk Chair', category='Furniture', current_stock=3, min_threshold=5, max_threshold=30, unit_price=299.99),
        Product(name='Notebook', category='Stationery', current_stock=45, min_threshold=20, max_threshold=150, unit_price=4.99),
        Product(name='Coffee Mug', category='Kitchen', current_stock=12, min_threshold=10, max_threshold=80, unit_price=12.99),
        Product(name='Monitor 24"', category='Electronics', current_stock=2, min_threshold=4, max_threshold=25, unit_price=249.99),
        Product(name='Mechanical Keyboard', category='Electronics', current_stock=7, min_threshold=8, max_threshold=60, unit_price=89.99)
    ]
    for p in products:
        db.session.add(p)
    
    db.session.commit()
    
    # Add sample transactions
    all_products = Product.query.all()
    for i in range(30):
        product = random.choice(all_products)
        trans_type = random.choice(['in', 'out'])
        qty = random.randint(1, 10)
        trans = Transaction(
            product_id=product.id,
            product_name=product.name,
            type=trans_type,
            quantity=qty,
            reason='Sample transaction',
            username='admin',
            timestamp=datetime.now() - timedelta(days=random.randint(0, 30))
        )
        db.session.add(trans)
    db.session.commit()
    
    # Create alerts for low stock
    for product in Product.query.all():
        if product.current_stock <= product.min_threshold:
            alert = Alert(
                product_id=product.id,
                product_name=product.name,
                alert_type='low_stock',
                message=f'⚠️ LOW STOCK: {product.name} has only {product.current_stock} units left! Minimum required is {product.min_threshold}.',
                status='active'
            )
            db.session.add(alert)
    db.session.commit()
    
    print("=" * 50)
    print("✅ DATABASE CREATED SUCCESSFULLY!")
    print("📝 Admin Login: admin / admin123")
    print("🌐 Open http://localhost:5000")
    print("=" * 50)

def check_and_create_alerts(product):
    if product.current_stock <= product.min_threshold:
        existing = Alert.query.filter_by(product_id=product.id, alert_type='low_stock', status='active').first()
        if not existing:
            alert = Alert(
                product_id=product.id,
                product_name=product.name,
                alert_type='low_stock',
                message=f'⚠️ LOW STOCK: {product.name} has only {product.current_stock} units left!',
                status='active'
            )
            db.session.add(alert)
            db.session.commit()
    else:
        alerts = Alert.query.filter_by(product_id=product.id, alert_type='low_stock', status='active').all()
        for alert in alerts:
            alert.status = 'resolved'
        db.session.commit()

# ============ ROUTES ============
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE, current_user=current_user)

@app.route('/inventory')
@login_required
def inventory():
    return render_template_string(INVENTORY_TEMPLATE, current_user=current_user)

@app.route('/alerts')
@login_required
def alerts():
    return render_template_string(ALERTS_TEMPLATE, current_user=current_user)

@app.route('/transactions')
@login_required
def transactions():
    return render_template_string(TRANSACTIONS_TEMPLATE, current_user=current_user)

# ============ API ROUTES ============
@app.route('/api/dashboard/stats')
@login_required
def get_stats():
    total_products = Product.query.count()
    total_stock = db.session.query(db.func.sum(Product.current_stock)).scalar() or 0
    active_alerts = Alert.query.filter_by(status='active').count()
    low_stock_count = Product.query.filter(Product.current_stock <= Product.min_threshold).count()
    total_value = db.session.query(db.func.sum(Product.current_stock * Product.unit_price)).scalar() or 0
    
    month_ago = datetime.now() - timedelta(days=30)
    monthly_sales = db.session.query(db.func.sum(Transaction.quantity)).filter(
        Transaction.type == 'out',
        Transaction.timestamp >= month_ago
    ).scalar() or 0
    
    categories = db.session.query(
        Product.category,
        db.func.sum(Product.current_stock).label('total')
    ).group_by(Product.category).all()
    
    top_products = db.session.query(
        Transaction.product_name,
        db.func.sum(Transaction.quantity).label('sold')
    ).filter_by(type='out').group_by(Transaction.product_name).order_by(db.desc('sold')).limit(5).all()
    
    recent = Transaction.query.order_by(Transaction.timestamp.desc()).limit(5).all()
    
    return jsonify({
        'total_products': total_products,
        'total_stock': total_stock,
        'active_alerts': active_alerts,
        'low_stock_count': low_stock_count,
        'total_value': round(float(total_value), 2),
        'monthly_sales': monthly_sales,
        'categories': [{'name': c[0], 'total': c[1]} for c in categories],
        'top_products': [{'name': p[0], 'sold': p[1]} for p in top_products],
        'recent_transactions': [{
            'id': t.id,
            'product': t.product_name,
            'type': t.type,
            'quantity': t.quantity,
            'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M')
        } for t in recent]
    })

@app.route('/api/products')
@login_required
def get_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category': p.category,
        'current_stock': p.current_stock,
        'min_threshold': p.min_threshold,
        'max_threshold': p.max_threshold,
        'unit_price': p.unit_price,
        'status': 'critical' if p.current_stock <= p.min_threshold else 'over' if p.current_stock >= p.max_threshold else 'normal'
    } for p in products])

@app.route('/api/products', methods=['POST'])
@login_required
def add_product():
    data = request.json
    product = Product(
        name=data['name'],
        category=data['category'],
        current_stock=data.get('current_stock', 0),
        min_threshold=data.get('min_threshold', 10),
        max_threshold=data.get('max_threshold', 100),
        unit_price=data.get('unit_price', 0)
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({'success': True, 'id': product.id})

@app.route('/api/products/<int:product_id>/stock', methods=['PUT'])
@login_required
def update_stock(product_id):
    data = request.json
    product = Product.query.get_or_404(product_id)
    
    old_stock = product.current_stock
    
    if data['type'] == 'in':
        product.current_stock += data['quantity']
    else:
        if product.current_stock - data['quantity'] < 0:
            return jsonify({'error': 'Insufficient stock'}), 400
        product.current_stock -= data['quantity']
    
    transaction = Transaction(
        product_id=product.id,
        product_name=product.name,
        type=data['type'],
        quantity=data['quantity'],
        reason=data.get('reason', 'Manual update'),
        username=current_user.username
    )
    db.session.add(transaction)
    db.session.commit()
    
    check_and_create_alerts(product)
    
    return jsonify({
        'success': True,
        'current_stock': product.current_stock,
        'old_stock': old_stock
    })

@app.route('/api/products/<int:product_id>/thresholds', methods=['PUT'])
@login_required
def update_thresholds(product_id):
    data = request.json
    product = Product.query.get_or_404(product_id)
    product.min_threshold = data['min_threshold']
    product.max_threshold = data['max_threshold']
    db.session.commit()
    check_and_create_alerts(product)
    return jsonify({'success': True})

@app.route('/api/alerts/active')
@login_required
def get_active_alerts():
    alerts = Alert.query.filter_by(status='active').order_by(Alert.created_at.desc()).all()
    return jsonify([{
        'id': a.id,
        'product_name': a.product_name,
        'alert_type': a.alert_type,
        'message': a.message,
        'created_at': a.created_at.isoformat()
    } for a in alerts])

@app.route('/api/alerts/<int:alert_id>/resolve', methods=['PUT'])
@login_required
def resolve_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.status = 'resolved'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/transactions/recent')
@login_required
def get_recent_transactions():
    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(20).all()
    return jsonify([{
        'id': t.id,
        'product_name': t.product_name,
        'type': t.type,
        'quantity': t.quantity,
        'reason': t.reason,
        'username': t.username,
        'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for t in transactions])

# ============ HTML TEMPLATES ============
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Inventory System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .login-card { background: white; border-radius: 20px; max-width: 450px; margin: 100px auto; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
        .login-header { background: linear-gradient(135deg, #4361ee, #3a56d4); color: white; padding: 30px; text-align: center; }
        .login-body { padding: 40px; }
        .btn-login { background: linear-gradient(135deg, #4361ee, #3a56d4); border: none; border-radius: 10px; padding: 12px; font-weight: bold; width: 100%; }
        .btn-login:hover { transform: translateY(-2px); }
        .form-control { border-radius: 10px; padding: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-card">
            <div class="login-header">
                <i class="fas fa-boxes fa-3x mb-3"></i>
                <h3>Inventory Stock Alert System</h3>
                <p>Welcome back! Please login to continue</p>
            </div>
            <div class="login-body">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                <form method="POST">
                    <div class="mb-3">
                        <label><i class="fas fa-user me-2"></i>Username</label>
                        <input type="text" class="form-control" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label><i class="fas fa-lock me-2"></i>Password</label>
                        <input type="password" class="form-control" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-login">Login</button>
                </form>
                <hr>
                <div class="text-center">
                    <small>Demo: admin / admin123</small>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Inventory System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        .sidebar { background: #1e1e2f; min-height: 100vh; }
        .sidebar .nav-link { color: #fff; margin: 5px 10px; border-radius: 10px; transition: all 0.3s; }
        .sidebar .nav-link:hover { background: rgba(255,255,255,0.1); transform: translateX(5px); }
        .sidebar .nav-link.active { background: #4361ee; }
        .stat-card { background: white; border-radius: 15px; padding: 20px; text-align: center; transition: transform 0.3s; box-shadow: 0 2px 10px rgba(0,0,0,0.1); cursor: pointer; }
        .stat-card:hover { transform: translateY(-5px); box-shadow: 0 5px 20px rgba(0,0,0,0.15); }
        .stat-value { font-size: 32px; font-weight: bold; }
        .card-header { background: linear-gradient(135deg, #4361ee, #3a56d4); color: white; border-radius: 10px 10px 0 0; }
        .alert-item { padding: 15px; margin-bottom: 10px; border-radius: 10px; border-left: 5px solid #ef476f; background: #fff3f3; transition: all 0.3s; }
        .alert-item:hover { transform: translateX(5px); }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand"><i class="fas fa-boxes me-2"></i>Inventory Stock Alert System</span>
            <div class="d-flex">
                <span class="text-light me-3"><i class="fas fa-user me-1"></i>{{ current_user.username }}</span>
                <a href="/logout" class="btn btn-outline-light btn-sm"><i class="fas fa-sign-out-alt me-1"></i>Logout</a>
            </div>
        </div>
    </nav>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 p-0">
                <div class="sidebar p-3">
                    <div class="nav flex-column">
                        <a class="nav-link active" href="/"><i class="fas fa-chart-line me-2"></i>Dashboard</a>
                        <a class="nav-link" href="/inventory"><i class="fas fa-warehouse me-2"></i>Inventory</a>
                        <a class="nav-link" href="/alerts"><i class="fas fa-exclamation-triangle me-2"></i>Alerts</a>
                        <a class="nav-link" href="/transactions"><i class="fas fa-history me-2"></i>Transactions</a>
                    </div>
                </div>
            </div>
            <div class="col-md-10 p-4">
                <h2 class="mb-4"><i class="fas fa-chart-line me-2"></i>Dashboard Overview</h2>
                <div class="row mb-4" id="stats"></div>
                <div class="row">
                    <div class="col-md-8">
                        <div class="card mb-4">
                            <div class="card-header"><i class="fas fa-chart-bar me-2"></i>Stock Levels by Product</div>
                            <div class="card-body"><canvas id="stockChart" height="300"></canvas></div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card mb-4">
                            <div class="card-header"><i class="fas fa-chart-pie me-2"></i>Category Distribution</div>
                            <div class="card-body"><canvas id="categoryChart" height="300"></canvas></div>
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card mb-4">
                            <div class="card-header"><i class="fas fa-trophy me-2"></i>Top Selling Products</div>
                            <div class="card-body">
                                <table class="table table-hover" id="topProducts"></table>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card mb-4">
                            <div class="card-header"><i class="fas fa-bell me-2"></i>Recent Alerts</div>
                            <div class="card-body"><div id="alerts"></div></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        let stockChart, categoryChart;
        
        function loadStats() {
            $.get('/api/dashboard/stats', function(data) {
                $('#stats').html(`
                    <div class="col-md-3">
                        <div class="stat-card">
                            <i class="fas fa-box fa-2x text-primary"></i>
                            <h2 class="stat-value mt-2">${data.total_products}</h2>
                            <p class="text-muted mb-0">Total Products</p>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <i class="fas fa-cubes fa-2x text-success"></i>
                            <h2 class="stat-value mt-2">${data.total_stock}</h2>
                            <p class="text-muted mb-0">Total Stock</p>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <i class="fas fa-dollar-sign fa-2x text-warning"></i>
                            <h2 class="stat-value mt-2">$${data.total_value.toLocaleString()}</h2>
                            <p class="text-muted mb-0">Inventory Value</p>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <i class="fas fa-bell fa-2x text-danger"></i>
                            <h2 class="stat-value mt-2">${data.active_alerts}</h2>
                            <p class="text-muted mb-0">Active Alerts</p>
                        </div>
                    </div>
                `);
                updateCharts(data.categories);
                loadTopProducts(data.top_products);
                loadAlerts();
            });
        }
        
        function updateCharts(categories) {
            $.get('/api/products', function(products) {
                const ctx1 = document.getElementById('stockChart').getContext('2d');
                if (stockChart) stockChart.destroy();
                stockChart = new Chart(ctx1, {
                    type: 'bar',
                    data: {
                        labels: products.map(p => p.name.substring(0, 12)),
                        datasets: [
                            { label: 'Current Stock', data: products.map(p => p.current_stock), backgroundColor: '#4361ee', borderRadius: 5 },
                            { label: 'Min Threshold', data: products.map(p => p.min_threshold), backgroundColor: '#ef476f', borderRadius: 5 }
                        ]
                    },
                    options: { responsive: true, maintainAspectRatio: true, scales: { y: { beginAtZero: true, title: { display: true, text: 'Quantity' } } } }
                });
                
                const ctx2 = document.getElementById('categoryChart').getContext('2d');
                if (categoryChart) categoryChart.destroy();
                categoryChart = new Chart(ctx2, {
                    type: 'doughnut',
                    data: {
                        labels: categories.map(c => c.name),
                        datasets: [{ data: categories.map(c => c.total), backgroundColor: ['#4361ee', '#06d6a0', '#ef476f', '#ffd166', '#118ab2'], borderWidth: 0 }]
                    },
                    options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom' } } }
                });
            });
        }
        
        function loadTopProducts(products) {
            let html = '<thead class="table-dark"><tr><th>Product</th><th>Units Sold</th></tr></thead><tbody>';
            products.forEach(p => { html += `<tr><td><strong>${p.name}</strong></td><td>${p.sold}</td></tr>`; });
            html += '</tbody>';
            $('#topProducts').html(html);
        }
        
        function loadAlerts() {
            $.get('/api/alerts/active', function(alerts) {
                if (alerts.length === 0) {
                    $('#alerts').html('<div class="alert alert-success text-center"><i class="fas fa-check-circle me-2"></i>No active alerts!</div>');
                    return;
                }
                let html = '';
                alerts.slice(0, 3).forEach(a => {
                    html += `<div class="alert-item"><i class="fas fa-exclamation-triangle text-danger me-2"></i><strong>${a.product_name}</strong><br><small>${a.message.substring(0, 80)}...</small></div>`;
                });
                if (alerts.length > 3) html += `<div class="text-center mt-2"><a href="/alerts" class="btn btn-sm btn-outline-primary">View all ${alerts.length} alerts →</a></div>`;
                $('#alerts').html(html);
            });
        }
        
        $(document).ready(() => { loadStats(); setInterval(loadStats, 15000); });
    </script>
</body>
</html>
'''

INVENTORY_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Inventory - Inventory System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        .sidebar { background: #1e1e2f; min-height: 100vh; }
        .sidebar .nav-link { color: #fff; margin: 5px 10px; border-radius: 10px; transition: all 0.3s; }
        .sidebar .nav-link:hover { background: rgba(255,255,255,0.1); transform: translateX(5px); }
        .sidebar .nav-link.active { background: #4361ee; }
        .table-hover tbody tr:hover { background: #f8f9fa; transform: scale(1.01); transition: all 0.3s; cursor: pointer; }
        .btn-action { margin: 2px; transition: all 0.3s; }
        .btn-action:hover { transform: translateY(-2px); }
        .badge { padding: 5px 12px; border-radius: 20px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand"><i class="fas fa-boxes me-2"></i>Inventory Stock Alert System</span>
            <div class="d-flex">
                <span class="text-light me-3"><i class="fas fa-user me-1"></i>{{ current_user.username }}</span>
                <a href="/logout" class="btn btn-outline-light btn-sm"><i class="fas fa-sign-out-alt me-1"></i>Logout</a>
            </div>
        </div>
    </nav>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 p-0">
                <div class="sidebar p-3">
                    <div class="nav flex-column">
                        <a class="nav-link" href="/"><i class="fas fa-chart-line me-2"></i>Dashboard</a>
                        <a class="nav-link active" href="/inventory"><i class="fas fa-warehouse me-2"></i>Inventory</a>
                        <a class="nav-link" href="/alerts"><i class="fas fa-exclamation-triangle me-2"></i>Alerts</a>
                        <a class="nav-link" href="/transactions"><i class="fas fa-history me-2"></i>Transactions</a>
                    </div>
                </div>
            </div>
            <div class="col-md-10 p-4">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h2><i class="fas fa-warehouse me-2"></i>Inventory Management</h2>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addModal"><i class="fas fa-plus me-2"></i>Add Product</button>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover table-bordered">
                        <thead class="table-dark">
                            <tr><th>ID</th><th>Name</th><th>Category</th><th>Stock</th><th>Min</th><th>Max</th><th>Price</th><th>Status</th><th>Actions</th></tr>
                        </thead>
                        <tbody id="inventoryTable"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Update Stock Modal -->
    <div class="modal fade" id="updateModal">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-primary text-white"><h5 class="modal-title">Update Stock</h5><button class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
                <div class="modal-body">
                    <input type="hidden" id="updateId">
                    <div class="mb-3"><label>Product</label><input type="text" id="updateName" class="form-control" readonly></div>
                    <div class="mb-3"><label>Type</label><select id="transType" class="form-select"><option value="in">📥 Add Stock</option><option value="out">📤 Remove Stock</option></select></div>
                    <div class="mb-3"><label>Quantity</label><input type="number" id="transQty" class="form-control" min="1" required></div>
                    <div class="mb-3"><label>Reason</label><input type="text" id="transReason" class="form-control" placeholder="e.g., New shipment, Customer purchase"></div>
                </div>
                <div class="modal-footer"><button class="btn btn-primary" onclick="updateStock()">Update</button><button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button></div>
            </div>
        </div>
    </div>
    
    <!-- Set Thresholds Modal -->
    <div class="modal fade" id="thresholdModal">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-info text-white"><h5 class="modal-title">Set Alert Thresholds</h5><button class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
                <div class="modal-body">
                    <input type="hidden" id="thresId">
                    <div class="mb-3"><label>Product</label><input type="text" id="thresName" class="form-control" readonly></div>
                    <div class="mb-3"><label>Minimum Threshold</label><input type="number" id="minThres" class="form-control" required><small class="text-muted">Alert when stock falls below this value</small></div>
                    <div class="mb-3"><label>Maximum Threshold</label><input type="number" id="maxThres" class="form-control" required><small class="text-muted">Alert when stock exceeds this value</small></div>
                </div>
                <div class="modal-footer"><button class="btn btn-primary" onclick="saveThresholds()">Save</button><button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button></div>
            </div>
        </div>
    </div>
    
    <!-- Add Product Modal -->
    <div class="modal fade" id="addModal">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-success text-white"><h5 class="modal-title">Add New Product</h5><button class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
                <div class="modal-body">
                    <div class="mb-3"><label>Product Name</label><input type="text" id="addName" class="form-control" required></div>
                    <div class="mb-3"><label>Category</label><input type="text" id="addCategory" class="form-control" required></div>
                    <div class="mb-3"><label>Initial Stock</label><input type="number" id="addStock" class="form-control" value="0"></div>
                    <div class="mb-3"><label>Min Threshold</label><input type="number" id="addMin" class="form-control" value="10"></div>
                    <div class="mb-3"><label>Max Threshold</label><input type="number" id="addMax" class="form-control" value="100"></div>
                    <div class="mb-3"><label>Unit Price</label><input type="number" id="addPrice" class="form-control" step="0.01" value="0"></div>
                </div>
                <div class="modal-footer"><button class="btn btn-primary" onclick="addProduct()">Add Product</button><button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button></div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function loadInventory() {
            $.get('/api/products', function(products) {
                let html = '';
                products.forEach(p => {
                    let badge = '';
                    if (p.current_stock <= p.min_threshold) badge = '<span class="badge bg-danger">Critical</span>';
                    else if (p.current_stock >= p.max_threshold) badge = '<span class="badge bg-info">Overstock</span>';
                    else badge = '<span class="badge bg-success">Normal</span>';
                    
                    html += `<tr>
                        <td>${p.id}</td>
                        <td><strong>${p.name}</strong></td>
                        <td>${p.category}</td>
                        <td class="${p.current_stock <= p.min_threshold ? 'text-danger fw-bold' : ''}">${p.current_stock}</td>
                        <td>${p.min_threshold}</td>
                        <td>${p.max_threshold}</td>
                        <td>$${p.unit_price}</td>
                        <td>${badge}</td>
                        <td>
                            <button class="btn btn-sm btn-primary btn-action" onclick='openUpdate(${p.id}, "${p.name}")'><i class="fas fa-exchange-alt"></i></button>
                            <button class="btn btn-sm btn-info btn-action" onclick='openThreshold(${p.id}, "${p.name}", ${p.min_threshold}, ${p.max_threshold})'><i class="fas fa-sliders-h"></i></button>
                        </td>
                    </tr>`;
                });
                $('#inventoryTable').html(html);
            });
        }
        
        function openUpdate(id, name) { $('#updateId').val(id); $('#updateName').val(name); new bootstrap.Modal(document.getElementById('updateModal')).show(); }
        function openThreshold(id, name, min, max) { $('#thresId').val(id); $('#thresName').val(name); $('#minThres').val(min); $('#maxThres').val(max); new bootstrap.Modal(document.getElementById('thresholdModal')).show(); }
        
        function updateStock() {
            let id = $('#updateId').val(), qty = parseInt($('#transQty').val()), type = $('#transType').val(), reason = $('#transReason').val();
            if (!qty || qty <= 0) { alert('Please enter a valid quantity'); return; }
            $.ajax({ url: `/api/products/${id}/stock`, method: 'PUT', contentType: 'application/json', data: JSON.stringify({ quantity: qty, type: type, reason: reason }), success: () => location.reload() });
        }
        
        function saveThresholds() {
            let id = $('#thresId').val(), min = parseInt($('#minThres').val()), max = parseInt($('#maxThres').val());
            $.ajax({ url: `/api/products/${id}/thresholds`, method: 'PUT', contentType: 'application/json', data: JSON.stringify({ min_threshold: min, max_threshold: max }), success: () => location.reload() });
        }
        
        function addProduct() {
            let data = {
                name: $('#addName').val(), category: $('#addCategory').val(),
                current_stock: parseInt($('#addStock').val()), min_threshold: parseInt($('#addMin').val()),
                max_threshold: parseInt($('#addMax').val()), unit_price: parseFloat($('#addPrice').val())
            };
            if (!data.name || !data.category) { alert('Please fill product name and category'); return; }
            $.ajax({ url: '/api/products', method: 'POST', contentType: 'application/json', data: JSON.stringify(data), success: () => location.reload() });
        }
        
        $(document).ready(() => loadInventory());
    </script>
</body>
</html>
'''

ALERTS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Alerts - Inventory System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        .sidebar { background: #1e1e2f; min-height: 100vh; }
        .sidebar .nav-link { color: #fff; margin: 5px 10px; border-radius: 10px; transition: all 0.3s; }
        .sidebar .nav-link:hover { background: rgba(255,255,255,0.1); transform: translateX(5px); }
        .sidebar .nav-link.active { background: #4361ee; }
        .alert-card { border-left: 5px solid #ef476f; background: #fff3f3; margin-bottom: 15px; padding: 20px; border-radius: 10px; transition: all 0.3s; }
        .alert-card:hover { transform: translateX(5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand"><i class="fas fa-boxes me-2"></i>Inventory Stock Alert System</span>
            <div class="d-flex">
                <span class="text-light me-3"><i class="fas fa-user me-1"></i>{{ current_user.username }}</span>
                <a href="/logout" class="btn btn-outline-light btn-sm"><i class="fas fa-sign-out-alt me-1"></i>Logout</a>
            </div>
        </div>
    </nav>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 p-0">
                <div class="sidebar p-3">
                    <div class="nav flex-column">
                        <a class="nav-link" href="/"><i class="fas fa-chart-line me-2"></i>Dashboard</a>
                        <a class="nav-link" href="/inventory"><i class="fas fa-warehouse me-2"></i>Inventory</a>
                        <a class="nav-link active" href="/alerts"><i class="fas fa-exclamation-triangle me-2"></i>Alerts</a>
                        <a class="nav-link" href="/transactions"><i class="fas fa-history me-2"></i>Transactions</a>
                    </div>
                </div>
            </div>
            <div class="col-md-10 p-4">
                <h2 class="mb-4"><i class="fas fa-exclamation-triangle me-2"></i>Active Alerts</h2>
                <div id="alertsList"></div>
            </div>
        </div>
    </div>
    <script>
        function loadAlerts() {
            $.get('/api/alerts/active', function(alerts) {
                if (alerts.length === 0) {
                    $('#alertsList').html('<div class="alert alert-success text-center"><i class="fas fa-check-circle fa-3x mb-3"></i><h4>No Active Alerts!</h4><p>All inventory levels are within thresholds.</p></div>');
                    return;
                }
                let html = '';
                alerts.forEach(a => {
                    html += `<div class="alert-card"><div class="d-flex justify-content-between align-items-start"><div><h5><i class="fas fa-exclamation-triangle text-danger me-2"></i>${a.product_name}</h5><p class="mb-2">${a.message}</p><small class="text-muted"><i class="fas fa-clock me-1"></i>${new Date(a.created_at).toLocaleString()}</small></div><button class="btn btn-success btn-sm" onclick="resolveAlert(${a.id})"><i class="fas fa-check me-1"></i>Resolve</button></div></div>`;
                });
                $('#alertsList').html(html);
            });
        }
        
        function resolveAlert(id) {
            if(confirm('Resolve this alert?')) {
                $.ajax({ url: `/api/alerts/${id}/resolve`, method: 'PUT', success: () => { loadAlerts(); location.reload(); } });
            }
        }
        
        $(document).ready(() => { loadAlerts(); setInterval(loadAlerts, 5000); });
    </script>
</body>
</html>
'''

TRANSACTIONS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Transactions - Inventory System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        .sidebar { background: #1e1e2f; min-height: 100vh; }
        .sidebar .nav-link { color: #fff; margin: 5px 10px; border-radius: 10px; transition: all 0.3s; }
        .sidebar .nav-link:hover { background: rgba(255,255,255,0.1); transform: translateX(5px); }
        .sidebar .nav-link.active { background: #4361ee; }
        .table-hover tbody tr:hover { background: #f8f9fa; transform: scale(1.01); transition: all 0.3s; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand"><i class="fas fa-boxes me-2"></i>Inventory Stock Alert System</span>
            <div class="d-flex">
                <span class="text-light me-3"><i class="fas fa-user me-1"></i>{{ current_user.username }}</span>
                <a href="/logout" class="btn btn-outline-light btn-sm"><i class="fas fa-sign-out-alt me-1"></i>Logout</a>
            </div>
        </div>
    </nav>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 p-0">
                <div class="sidebar p-3">
                    <div class="nav flex-column">
                        <a class="nav-link" href="/"><i class="fas fa-chart-line me-2"></i>Dashboard</a>
                        <a class="nav-link" href="/inventory"><i class="fas fa-warehouse me-2"></i>Inventory</a>
                        <a class="nav-link" href="/alerts"><i class="fas fa-exclamation-triangle me-2"></i>Alerts</a>
                        <a class="nav-link active" href="/transactions"><i class="fas fa-history me-2"></i>Transactions</a>
                    </div>
                </div>
            </div>
            <div class="col-md-10 p-4">
                <h2 class="mb-4"><i class="fas fa-history me-2"></i>Transaction History</h2>
                <div class="table-responsive">
                    <table class="table table-hover table-bordered">
                        <thead class="table-dark">
                            <tr><th>Date & Time</th><th>Product</th><th>Type</th><th>Quantity</th><th>User</th><th>Reason</th></tr>
                        </thead>
                        <tbody id="transTable"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <script>
        function loadTransactions() {
            $.get('/api/transactions/recent', function(trans) {
                let html = '';
                trans.forEach(t => {
                    let badge = t.type === 'in' ? '<span class="badge bg-success"><i class="fas fa-arrow-down me-1"></i>Stock In</span>' : '<span class="badge bg-danger"><i class="fas fa-arrow-up me-1"></i>Stock Out</span>';
                    html += `<tr>
                        <td><i class="fas fa-calendar me-1"></i>${t.timestamp}</td>
                        <td><strong>${t.product_name}</strong></td>
                        <td>${badge}</td>
                        <td class="${t.type === 'in' ? 'text-success' : 'text-danger'} fw-bold">${t.type === 'in' ? '+' : '-'}${t.quantity}</td>
                        <td><i class="fas fa-user me-1"></i>${t.username || 'system'}</td>
                        <td>${t.reason || '-'}</td>
                    </tr>`;
                });
                if (trans.length === 0) html = '<tr><td colspan="6" class="text-center">No transactions yet</td></tr>';
                $('#transTable').html(html);
            });
        }
        $(document).ready(() => { loadTransactions(); setInterval(loadTransactions, 10000); });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True, port=5000)