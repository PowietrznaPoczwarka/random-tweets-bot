import json
import requests
from requests_oauthlib import OAuth1Session
import os

consumer_key = os.environ.get('CONSUMER_KEY')
consumer_secret = os.environ.get('CONSUMER_SECRET')
access_token = os.environ.get('ACCESS_TOKEN')
access_token_secret = os.environ.get('ACCESS_TOKEN_SECRET')

def get_wikipedia_image_data():
    wiki_url = 'https://en.wikipedia.org/api/rest_v1/page/random/summary'
    headers = {
        'accept': 'application/problem+json'
    }
    
    response = requests.get(wiki_url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        title = data.get('title', '')
        description = data.get('description')
        link = data['content_urls']['desktop']['page']
        image_url = data.get('originalimage', {}).get('source', '')
        return title, description, link, image_url
    else:
        raise Exception(f"Request failed with status code {response.status_code}")
    
def upload_image_to_twitter(image_url):
    
    # Downloading
    image_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    image_response = requests.get(image_url, headers=image_headers)
    
    if image_response.status_code == 200:
        image_data = image_response.content
    else:
        raise Exception(f"Failed to download image with status code {image_response.status_code}, {image_response.text}")

    # Uploading 
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    media_url = "https://upload.twitter.com/1.1/media/upload.json"
    files = {'media': image_data}
    media_response = oauth.post(media_url, files=files)

    if media_response.status_code != 200:
        raise Exception(
            "Media upload failed: {} {}".format(media_response.status_code, media_response.text)
        )

    media_id = media_response.json()['media_id_string']
    return media_id

def post_tweet_with_image(title, description, link, media_id):
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    text = f"Today's image: {title}, \n{description} \n\nRead more at: {link}"
    payload = {"text": text, "media": {"media_ids": [media_id]}}

    response = oauth.post("https://api.twitter.com/2/tweets", json=payload)

    if response.status_code != 201:
        raise Exception(
            "Request returned an error: {} {}".format(response.status_code, response.text)
        )

    print("Response code: {}".format(response.status_code))
    json_response = response.json()
    print(json.dumps(json_response, indent=4, sort_keys=True))

def lambda_handler(event, context):
    try:
        title, description, link, image_url = get_wikipedia_image_data()
        if image_url:
            media_id = upload_image_to_twitter(image_url)
            post_tweet_with_image(title, description, link, media_id)
            return {
                'statusCode': 200,
                'body': json.dumps('Tweet posted successfully!')
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps('No image URL found for the article.')
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }
