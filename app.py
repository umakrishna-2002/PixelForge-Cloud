import os
import uuid
import boto3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from botocore.exceptions import ClientError

# --- Config ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')  # set strong secret in prod

# AWS / App config (set these env vars)
S3_BUCKET = os.environ.get('S3_BUCKET_NAME')
S3_REGION = os.environ.get('AWS_REGION', 'us-east-1')
USE_S3 = os.environ.get('USE_S3', 'true').lower() == 'true'

DYNAMO_TABLE = os.environ.get('DDB_USERS_TABLE', 'Users')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# AWS clients
s3_client = boto3.client('s3', region_name=S3_REGION) if USE_S3 else None
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(DYNAMO_TABLE)

# Local uploads dir (local testing only)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --- Helpers ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_user_prefixes(user_id):
    """
    Create "folders" in S3 by putting empty objects for the prefixes.
    This is optional (S3 does not require folders), but nice for visibility.
    """
    if not USE_S3 or not S3_BUCKET:
        return
    prefixes = [f"{user_id}/uploads/", f"{user_id}/resized/"]
    for key in prefixes:
        try:
            s3_client.put_object(Bucket=S3_BUCKET, Key=key)
        except ClientError as e:
            print(f"Error creating prefix {key}: {e}")

def get_user_by_email(email):
    """Fetch user item from DynamoDB by email"""
    try:
        resp = users_table.get_item(Key={'email': email})
        return resp.get('Item')
    except Exception as e:
        print("DynamoDB get_item error:", e)
        return None

def save_user_to_ddb(email, username, password_hash, user_id):
    item = {
        'email': email,
        'username': username,
        'user_id': user_id,
        'password_hash': password_hash
    }
    users_table.put_item(Item=item)


# --- Routes ---
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    uploads = []
    resized = []

    if USE_S3 and S3_BUCKET:
        # list uploads
        try:
            resp = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=f"{user_id}/uploads/")
            if 'Contents' in resp:
                uploads = [
                    obj['Key'].split('/')[-1] for obj in resp['Contents']
                    if obj['Key'] != f"{user_id}/uploads/" and allowed_file(obj['Key'])
                ]
        except ClientError as e:
            print("Error listing uploads:", e)

        # list resized
        try:
            resp2 = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=f"{user_id}/resized/")
            if 'Contents' in resp2:
                resized = [
                    obj['Key'].split('/')[-1] for obj in resp2['Contents']
                    if obj['Key'] != f"{user_id}/resized/" and allowed_file(obj['Key'])
                ]
        except ClientError as e:
            print("Error listing resized:", e)
    else:
        # local mode: use local uploads folder (no per-user isolation in local mode)
        if os.path.exists(UPLOAD_FOLDER):
            uploads = [f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)]

    return render_template('index.html',
                           username=session.get('username'),
                           user_id=user_id,
                           images_uploads=uploads,
                           images_resized=resized,
                           use_s3=USE_S3,
                           s3_bucket=S3_BUCKET,
                           s3_region=S3_REGION)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        flash('You must be logged in to upload.')
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        user_id = session['user_id']

        if USE_S3 and S3_BUCKET:
            s3_key = f"{user_id}/uploads/{filename}"
            try:
                file.seek(0)
                s3_client.upload_fileobj(
                    file,
                    S3_BUCKET,
                    s3_key,
                    ExtraArgs={'ContentType': file.content_type}
                )
                flash('Image uploaded successfully to S3!')
            except ClientError as e:
                print("S3 upload error:", e)
                flash('Error uploading to S3. Please try again.')
        else:
            # Local save (for dev)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            flash('Image uploaded successfully (local mode)!')

        return redirect(url_for('index'))

    flash('Invalid file type. Please upload an image.')
    return redirect(url_for('index'))


# --- Auth routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        if not username or not email or not password:
            flash('Please fill all fields.')
            return redirect(url_for('signup'))

        # Check existing
        if get_user_by_email(email):
            flash('Email already registered. Try logging in.')
            return redirect(url_for('login'))

        # Create user
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(password)

        try:
            save_user_to_ddb(email, username, password_hash, user_id)
            create_user_prefixes(user_id)
        except Exception as e:
            print("Error saving user:", e)
            flash('Error creating user. Try again.')
            return redirect(url_for('signup'))

        # Auto-login after signup
        session['user_id'] = user_id
        session['username'] = username
        session['email'] = email

        flash('Signup successful! Welcome.')
        return redirect(url_for('index'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        user = get_user_by_email(email)
        if not user:
            flash('No account found with that email.')
            return redirect(url_for('signup'))

        if not check_password_hash(user['password_hash'], password):
            flash('Invalid credentials.')
            return redirect(url_for('login'))

        # Successful login
        session['user_id'] = user['user_id']
        session['username'] = user.get('username')
        session['email'] = user.get('email')
        flash('Logged in successfully.')
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect(url_for('login'))


# --- Run ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
