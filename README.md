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


Create  S3 bucket where the images will be stored as objects.

<img width="1231" height="445" alt="image" src="https://github.com/user-attachments/assets/bc8f9a98-d352-4f24-8291-27e3110d35b0" />


Create DynamoDB table with table name as **Users** to store the user credentials (username, password, email, hashing password)

<img width="1755" height="728" alt="image" src="https://github.com/user-attachments/assets/db40aded-b161-46dd-93b1-06a7e7a4c600" />


Now create a lambda function which contains the logic for resizing the image.

- Use **Pyhton 3.9** Runtime
  <img width="1595" height="805" alt="image" src="https://github.com/user-attachments/assets/bb143ad7-09ca-4370-b58e-7477072b2cc6" />

  Upload the lambda function code, which will resize the image.

  <img width="1456" height="743" alt="image" src="https://github.com/user-attachments/assets/211a4fce-dd25-4c03-b4a6-dff7c27e16c8" />

Change the name of the handler based on the name of the lambda function.
<img width="1553" height="164" alt="image" src="https://github.com/user-attachments/assets/ec536935-a8c7-44b3-b95e-60d2792ac680" />

Now add the **Pillow Layer** in lambda layer that contains the Pillow (PIL) image-processing library, packaged in a way that Lambda can use it.
- Select the pillow layer based on your lambda function runtime: https://github.com/keithrozario/Klayers/tree/master/deployments 

<img width="1582" height="730" alt="image" src="https://github.com/user-attachments/assets/29bbdebf-8e3d-43a0-938a-395605fc5135" />


Create a trigger that will active whenever there is an image upload from the flask application.

<img width="1554" height="690" alt="image" src="https://github.com/user-attachments/assets/67a50d98-afa1-426e-ac6d-05f62331c0c2" />


Update the Lambda role to access the S3 bucket

<img width="1238" height="486" alt="image" src="https://github.com/user-attachments/assets/bfd8ec1f-d59b-4679-9c73-22374592c5be" />


Create IAM role for EC2 instance to access the S3 bucket the DynamoDB

<img width="1585" height="686" alt="image" src="https://github.com/user-attachments/assets/2ab333db-55ac-4d79-b8c3-37a0c01348e3" />


- Add a custom inline policy for DynamoDB
  1. Add the new user data.
  2. Retrive the user data.
  <img width="1250" height="652" alt="image" src="https://github.com/user-attachments/assets/2a9e22fb-f4e0-4ccf-80da-72b2e1e142b6" />

Create an EC2 instance by adding the  IAM role created 

<img width="1663" height="749" alt="image" src="https://github.com/user-attachments/assets/7ed13d65-49dd-4716-8f03-b12e9eda7f81" />


Connect to the instance and clone the github repo.

```

