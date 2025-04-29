from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f1340841002453968837b6053f9dc3fdc7fd3b7d86b87dca'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://haroon:Admin%4050@haroonapp.database.windows.net/HaroonApp?driver=ODBC+Driver+17+for+SQL+Server'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

AZURE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=staticappaghaharoon;AccountKey=rwzgjJW9892D5VlTRZZW7L0ZIJHa1UjQ1l02FXFGArw4eqxH+U3Yedies6Kdb0/ZocOmFnMX1uGj+AStVfS40A==;EndpointSuffix=core.windows.net'
AZURE_CONTAINER_NAME = "uploads"

db = SQLAlchemy(app)
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
try:
    blob_service_client.create_container(AZURE_CONTAINER_NAME)
except Exception:
    pass

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(512), nullable=False)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    caption = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    people_present = db.Column(db.String(256), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    file_path = db.Column(db.String(512), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='media')
    ratings = db.relationship('Rating', backref='media')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'media_id', name='unique_user_media_rating'),)

with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template_string('''
        <style>
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #ff7e5f, #feb47b); color: #fff; }
            .container { background: rgba(0, 0, 0, 0.7); padding: 20px; border-radius: 10px; box-shadow: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23); }
            h1 { text-shadow: 2px 2px 4px #000000; }
            a { color: #ffcc00; text-decoration: none; margin: 0 10px; }
            a:hover { text-decoration: underline; }
        </style>
        <div class="container">
            <h1>Welcome to the My Video Hub</h1>
            <a href="{{ url_for('login') }}">Login</a> |
            <a href="{{ url_for('register') }}">Register</a>
        </div>
    ''')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, role=role, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created!', 'success')
        return redirect(url_for('login'))
    return render_template_string('''
        <style>
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #ff7e5f, #feb47b); color: #fff; }
            .container { background: rgba(0, 0, 0, 0.7); padding: 20px; border-radius: 10px; box-shadow: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23); }
            h1 { text-shadow: 2px 2px 4px #000000; }
            form { margin-top: 20px; }
            input, select, button { display: block; width: 100%; margin-bottom: 10px; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; }
            button { background-color: #ffcc00; color: white; border: none; cursor: pointer; transition: background-color 0.3s ease; }
            button:hover { background-color: #e0ac3c; }
        </style>
        <div class="container">
            <h1>Register</h1>
            <form method="POST">
                <input type="text" name="username" placeholder="Username" required><br>
                <input type="email" name="email" placeholder="Email" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <select name="role" required>
                    <option value="creator">Creator</option>
                    <option value="consumer">Consumer</option>
                </select><br>
                <button type="submit">Register</button>
            </form>
        </div>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed.', 'danger')
    return render_template_string('''
        <style>
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #ff7e5f, #feb47b); color: #fff; }
            .container { background: rgba(0, 0, 0, 0.7); padding: 20px; border-radius: 10px; box-shadow: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23); }
            h1 { text-shadow: 2px 2px 4px #000000; }
            form { margin-top: 20px; }
            input, button { display: block; width: 100%; margin-bottom: 10px; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; }
            button { background-color: #ffcc00; color: white; border: none; cursor: pointer; transition: background-color 0.3s ease; }
            button:hover { background-color: #e0ac3c; }
        </style>
        <div class="container">
            <h1>Login</h1>
            <form method="POST">
                <input type="text" name="username" placeholder="Username" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <button type="submit">Login</button>
            </form>
        </div>
    ''')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.form.get('search_query', '')
    media = Media.query.filter(Media.title.contains(search_query)).options(
        joinedload(Media.comments),
        joinedload(Media.ratings)
    ).all()

    if session['role'] == 'creator':
        return render_template_string('''
            <style>
                body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #ff7e5f, #feb47b); color: #fff; }
                .container { max-width: 1200px; margin: auto; padding: 20px; border-radius: 10px; box-shadow: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23); background: rgba(0, 0, 0, 0.7); }
                h1 { text-align: center; text-shadow: 2px 2px 4px #000000; }
                form { margin-top: 20px; }
                input, select, button { display: block; width: 100%; margin-bottom: 10px; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; }
                button { background-color: #ffcc00; color: white; border: none; cursor: pointer; transition: background-color 0.3s ease; }
                button:hover { background-color: #e0ac3c; }
            </style>
            <div class="container">
                <h1>Creator Dashboard</h1>
                <form method="POST" action="{{ url_for('upload') }}" enctype="multipart/form-data">
                    <input type="text" name="title" placeholder="Title" required><br>
                    <input type="text" name="caption" placeholder="Caption"><br>
                    <input type="text" name="location" placeholder="Location"><br>
                    <input type="text" name="people_present" placeholder="People Present"><br>
                    <input type="file" name="file" required><br>
                    <select name="media_type" required>
                        <option value="video">Video</option>
                        <option value="picture">Picture</option>
                    </select><br>
                    <button type="submit">Upload Media</button>
                </form>
                <a href="{{ url_for('logout') }}">Logout</a>
            </div>
        ''')

    else:
        return render_template_string('''
            <style>
                body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #ff7e5f, #feb47b); color: #fff; }
                .container { max-width: 1200px; margin: auto; padding: 20px; border-radius: 10px; box-shadow: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23); background: rgba(0, 0, 0, 0.7); }
                h1, h2, h4 { text-align: center; text-shadow: 2px 2px 4px #000000; }
                video, img { max-width: 100%; height: auto; display: block; margin: 0 auto; }
                form { margin-top: 20px; }
                input, button { display: block; width: 100%; margin-bottom: 10px; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; }
                button { background-color: #ffcc00; color: white; border: none; cursor: pointer; transition: background-color 0.3s ease; }
                button:hover { background-color: #e0ac3c; }
                ul { list-style-type: none; padding: 0; }
                li { margin-bottom: 10px; }
                .media-item { margin-bottom: 20px; }
            </style>
            <div class="container">
                <h1>Consumer Dashboard</h1>
                <form method="POST" action="{{ url_for('dashboard') }}">
                    <input type="text" name="search_query" placeholder="Search by Title" value="{{ request.form.get('search_query', '') }}">
                    <button type="submit">Search</button>
                </form>

                {% if not media %}
                    <p>No results found.</p>
                {% endif %}

                {% for item in media %}
                    <div class="media-item">
                        <h2>{{ item.title | e }}</h2>
                        <p>{{ item.caption | e }}</p>
                        {% if item.media_type == 'video' %}
                            <video width="500" controls>
                                <source src="{{ item.file_path | e }}" type="video/mp4">
                                Your browser does not support video playback.
                            </video>
                        {% else %}
                            <img src="{{ item.file_path | e }}" alt="Picture" width="500">
                        {% endif %}
                        <h4>Comments:</h4>
                        <ul>
                            {% for comment in item.comments %}
                                <li>{{ comment.text | e }}</li>
                            {% endfor %}
                            {% if not item.comments %}
                                <li>No comments yet.</li>
                            {% endif %}
                        </ul>
                        <form method="POST" action="{{ url_for('comment') }}">
                            <input type="hidden" name="media_id" value="{{ item.id }}">
                            <input type="text" name="text" placeholder="Comment" required>
                            <button type="submit">Comment</button>
                        </form>
                        <h4>Ratings:</h4>
                        <ul>
                            {% for rating in item.ratings %}
                                <li>{{ rating.value | e }}/5</li>
                            {% endfor %}
                            {% if not item.ratings %}
                                <li>No ratings yet.</li>
                            {% endif %}
                        </ul>
                        <form method="POST" action="{{ url_for('rate') }}">
                            <input type="hidden" name="media_id" value="{{ item.id }}">
                            <input type="number" name="value" min="1" max="5" required>
                            <button type="submit">Rate</button>
                        </form>
                        <hr>
                    </div>
                {% endfor %}

                <a href="{{ url_for('logout') }}">Logout</a>
            </div>
        ''', media=media)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session or session['role'] != 'creator':
        return redirect(url_for('login'))
    title = request.form['title']
    caption = request.form['caption']
    location = request.form['location']
    people_present = request.form['people_present']
    file = request.files['file']
    media_type = request.form['media_type']
    if file:
        filename = file.filename
        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=filename)
        blob_client.upload_blob(file, overwrite=True, content_settings=ContentSettings(
            content_type='video/mp4' if media_type == 'video' else 'image/jpeg'))
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename}"
        media = Media(
            title=title,
            caption=caption,
            location=location,
            people_present=people_present,
            file_path=blob_url,
            media_type=media_type if media_type in ['video', 'picture'] else 'picture',
            creator_id=session['user_id']
        )
        db.session.add(media)
        db.session.commit()
        flash('Media uploaded successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/comment', methods=['POST'])
def comment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    comment = Comment(
        text=request.form['text'],
        user_id=session['user_id'],
        media_id=request.form['media_id']
    )
    db.session.add(comment)
    db.session.commit()
    flash('Comment added!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/rate', methods=['POST'])
def rate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    media_id = request.form.get('media_id')
    if not media_id:
        flash('Media ID is required to rate!', 'danger')
        return redirect(url_for('dashboard'))
    try:
        media_id = int(media_id)
    except ValueError:
        flash('Invalid Media ID!', 'danger')
        return redirect(url_for('dashboard'))
    media = Media.query.get(media_id)
    if not media:
        flash('Invalid media item!', 'danger')
        return redirect(url_for('dashboard'))
    existing_rating = Rating.query.filter_by(user_id=session['user_id'], media_id=media_id).first()
    if existing_rating:
        flash('You have already rated this media!', 'warning')
        return redirect(url_for('dashboard'))
    rating = Rating(
        value=int(request.form['value']),
        user_id=session['user_id'],
        media_id=media_id
    )
    db.session.add(rating)
    try:
        db.session.commit()
        flash('Media rated!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Error submitting rating.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
