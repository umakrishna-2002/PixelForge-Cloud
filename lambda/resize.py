import boto3
import os
import sys
import uuid
from urllib.parse import unquote_plus
from PIL import Image
import io

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

def resize_image(image_path, resized_path):
    with Image.open(image_path) as image:
        image.thumbnail((1024, 1024))
        image.save(resized_path)

def lambda_handler(event, context):
    # Get the bucket and object key from the Event
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        # Define paths
        tmpkey = key.replace('/', '')
        download_path = '/tmp/{}'.format(tmpkey)
        upload_path = '/tmp/resized-{}'.format(tmpkey)
        
        # Destination bucket (can be same or different, usually configured via Env Var)
        # For this example, we'll assume a separate bucket or prefix logic is handled by infrastructure
        # Let's assume we upload to a 'processed' folder in the same bucket for simplicity 
        # or a separate bucket defined in ENV
        dest_bucket = os.environ.get('DEST_BUCKET', bucket)
        sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')

        print(f"Processing {key} from {bucket}")

        try:
            # Download file from S3
            s3_client.download_file(bucket, key, download_path)
            
            # Resize
            resize_image(download_path, upload_path)
            
            # Upload to Destination
            dest_key = 'resized/{}'.format(key)
            s3_client.upload_file(upload_path, dest_bucket, dest_key)
            print(f"Uploaded resized image to {dest_bucket}/{dest_key}")

            # Publish to SNS
            if sns_topic_arn:
                message = f"Image {key} has been resized and uploaded to {dest_key}."
                sns_client.publish(
                    TopicArn=sns_topic_arn,
                    Message=message,
                    Subject='Image Processed Successfully'
                )

        except Exception as e:
            print(e)
            print(f"Error processing object {key} from bucket {bucket}.")
            raise e
            
    return {
        'statusCode': 200,
        'body': 'Image processing complete'
    }
