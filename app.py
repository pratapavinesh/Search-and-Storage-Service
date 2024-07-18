from flask import Flask, request, jsonify
from werkzeug.security import check_password_hash
from bson import ObjectId
from db import db
import boto3
import os
from flask import request, jsonify
import jwt
from dotenv import load_dotenv
from functools import wraps
import base64
from flask_cors import CORS
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')


def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Missing JWT token'}), 401

        try:
            # Decode the JWT token using the secret key
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            # Check if the username in the token matches the one in the request
            if payload['username'] == request.args.get('username'):
                # Add the decoded payload to the request context
                request.current_user = payload
            else:
                return jsonify({'message': 'Invalid username in JWT token'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'JWT token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid JWT token'}), 401

        return f(*args, **kwargs)
    return decorated_function

# Initialize AWS S3 client
s3_client = boto3.client('s3')
bucket_name = 'labelsimages'

# Endpoint to get all labels with images for a given username
@app.route('/get-user-labels', methods=['GET'])
@jwt_required
def get_user_labels():
    username = request.args.get('username')  # Get username from query parameters
    # Retrieve labels for the given username from MongoDB
    labels = list(db.labels_collection.find({'username': username}))
    
    # Create a list to store label data with image information
    labeled_images = []
    for label in labels:
        # Get image data from S3 bucket
        s3_key = label['image_url']
        image_data = s3_client.get_object(Bucket=bucket_name, Key=s3_key)['Body'].read()

        # Append label data with image information to the list
        labeled_images.append({
            'label_name': label['label_name'],
            'image_content': label['image_content'],
            'image_data': base64.b64encode(image_data).decode('utf-8')  # Encode image data as base64
        })
    return jsonify({'labeled_images': labeled_images}), 200

# Endpoint to search labels by label name and fetch image data from S3
@app.route('/search-labels', methods=['GET'])
@jwt_required
def search_labels_by_name():
    label_name = request.args.get('labelName')  # Get label name from query parameters

    # Search for labels with the given label name from MongoDB
    labels = list(db.labels_collection.find({'label_name': label_name}))
    # Create a list to store labels with image information
    labeled_images = []
    for label in labels:
        # Get image data from S3 bucket
        s3_key = label['image_url']
        image_data = s3_client.get_object(Bucket=bucket_name, Key=s3_key)['Body'].read()

        # Append label data with image information to the list
        labeled_images.append({
            'label_name': label['label_name'],
            'image_content': label['image_content'],
            'image_data': base64.b64encode(image_data).decode('utf-8')  # Encode image data as base64
        })
    return jsonify({'matching_labels': labeled_images}), 200

# Endpoint to upload image and create label
@app.route('/create-label', methods=['POST'])
@jwt_required
def create_label():
    data = request.json
    username = data['username']
    label_name = data['label_name']
    image_content = data['image_content']
    image_data = data['image_data']

    # Upload image to S3 bucket
    s3_key = f"{username}/{label_name}"
    s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=image_data, ContentType='image/jpg')

    # Insert label data into MongoDB
    label_data = {
        'username': username,
        'label_name': label_name,
        'image_url': s3_key,
        'image_content': image_content
    }
    db.labels_collection.insert_one(label_data)

    return jsonify({'message': 'Label created successfully.'}), 201

#-----------------------Testing of aws s3----------------------------------

# Endpoint to download image from S3 URL
@app.route('/download-image', methods=['GET'])
def download_image():
    s3_image_key = "make-04-00043-g008-550.jpg"  # Key of the image in your S3 bucket
    
    try:
        # Download the image from S3
        s3_client.download_file('labelsimages', s3_image_key, 'downloaded_image.jpg')
        return jsonify({'message': 'Image downloaded successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to download image: {str(e)}'}), 500

# Endpoint to check if S3 bucket is accessible
@app.route('/check-s3', methods=['GET'])
def checkS3():
    try:
        response = s3_client.list_objects(Bucket='labelsimages')
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = 5001  # Choose the port number you want to use
    app.run(debug=True, port=port)
    print(f"Server is running on port {port}")