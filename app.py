import os
import boto3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')  # Use env var in production

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# AWS S3 Configuration
S3_BUCKET = os.environ.get('S3_BUCKET_NAME')  # Set this as environment variable
S3_REGION = os.environ.get('AWS_REGION', 'us-east-1')
USE_S3 = os.environ.get('USE_S3', 'false').lower() == 'true'

# Initialize S3 client if using S3
if USE_S3:
    s3_client = boto3.client('s3', region_name=S3_REGION)
else:
    s3_client = None

# Ensure upload directory exists for local testing
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_s3(file, filename):
    """Upload file to S3 bucket"""
    try:
        s3_client.upload_fileobj(
            file,
            S3_BUCKET,
            f'uploads/{filename}',
            ExtraArgs={
                'ContentType': file.content_type
            }
        )
        return True
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        return False

@app.route('/')
def index():
    # In a real app, this would fetch from a database (RDS)
    # For local testing, we just list files in the upload folder
    images = []
    
    if USE_S3 and S3_BUCKET:
        # Fetch images from S3
        try:
            response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix='uploads/')
            if 'Contents' in response:
                images = [obj['Key'].replace('uploads/', '') for obj in response['Contents'] 
                         if obj['Key'] != 'uploads/' and allowed_file(obj['Key'])]
        except ClientError as e:
            print(f"Error listing S3 objects: {e}")
    else:
        # Local mode: list files from local folder
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            images = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if allowed_file(f)]
    
    return render_template('index.html', images=images, use_s3=USE_S3, s3_bucket=S3_BUCKET, s3_region=S3_REGION)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        if USE_S3 and S3_BUCKET:
            # PRODUCTION MODE: Upload to S3
            if upload_to_s3(file, filename):
                flash(f'Image uploaded successfully to S3!')
            else:
                flash('Error uploading to S3. Please try again.')
        else:
            # LOCAL TESTING MODE: Save to local disk
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('Image uploaded successfully (local mode)!')
        
        return redirect(url_for('index'))
    
    flash('Invalid file type. Please upload an image.')
    return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
