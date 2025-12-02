# PixelForge-Cloud  (Image resizer)


## 🏗️ Architecture

- **Frontend**: Flask + HTML/CSS (Glassmorphic design)
- **Storage**: AWS S3 for image storage
- **Compute**: EC2 for web server
- **Processing**: Lambda for image resizing
- **Database**: DynamoDB 


**Workflow**

- A flask application is hosted on **AWS**
- User login/SignUp using the Web UI.
- Flask validates the user and stores/reads user details (email, username, password hash, user_id) from DynamoDB.
- Flask keeps the user logged in using a session (with user_id in session) after login.
- User uploads the image via flask app.
- Flask uploads the image to S3, by defining the specific path in the S3 bucket (user_id/uploads/image).
- S3 triggers the Lambda function when a new object is created in the uploads folder.
- Lambda downloads the image from S3, resizes it using Pillow (PIL), and generates a smaller version.
- Lambda function uploads the resized image in S3 under specified path (user_id/resized/image).
- The user can access the original and resized images.
- Flask passes these image lists to the HTML template, which displays the user’s uploaded and resized images in the UI.
- All access to S3 and DynamoDB is controlled using IAM roles attached to the EC2 instance and the Lambda function.
