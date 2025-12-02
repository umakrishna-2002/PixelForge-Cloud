import boto3
import os
from urllib.parse import unquote_plus
from PIL import Image
import io

s3_client = boto3.client('s3')

def resize_image_bytes(image_bytes, max_size=(1024, 1024)):
    with Image.open(io.BytesIO(image_bytes)) as image:
        image.thumbnail(max_size)
        out_buf = io.BytesIO()
        image.save(out_buf, format=image.format or 'JPEG')
        out_buf.seek(0)
        return out_buf

def lambda_handler(event, context):
    # If DEST_BUCKET is not set, resized images go to same bucket
    dest_bucket = os.environ.get('DEST_BUCKET')

    for record in event['Records']:
        src_bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])

        try:
            # Expect key format like: user_id/uploads/filename.jpg
            parts = key.split('/')
            if len(parts) < 3:
                print(f"Invalid object key format: {key}")
                continue

            user_id = parts[0]
            filename = parts[-1]

            # Download original image
            response = s3_client.get_object(Bucket=src_bucket, Key=key)
            original_bytes = response['Body'].read()

            # Resize image
            resized_buf = resize_image_bytes(original_bytes)

            # Destination bucket (same as source if DEST_BUCKET not set)
            output_bucket = dest_bucket if dest_bucket else src_bucket
            output_key = f"{user_id}/resized/{filename}"

            # Upload resized image
            s3_client.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=resized_buf,
                ContentType=response.get("ContentType", "image/jpeg")
            )

            print(f"Resized image stored at {output_bucket}/{output_key}")

        except Exception as e:
            print(f"Error processing {key}: {e}")
            raise

    return {"statusCode": 200, "body": "Resize complete"}
