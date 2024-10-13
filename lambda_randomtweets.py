import boto3
from requests_oauthlib import OAuth1Session
import json
import re
from openai import OpenAI
import os
import requests

# Ustawienia Parameter Store
ssm = boto3.client('ssm')
PARAMETER_NAME = "/randomtweets/used_topics"
OPENAI_API_KEY_PARAM = "/randomtweets/openai_api_key"

consumer_key = os.environ.get('CONSUMER_KEY_PARAM')
consumer_secret = os.environ.get('CONSUMER_SECRET_PARAM')
access_token = os.environ.get('ACCESS_TOKEN_PARAM')
access_token_secret = os.environ.get('ACCESS_SECRET_PARAM')

def get_parameter(name):
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response['Parameter']['Value']

# Extract topic list
def get_used_topics():
    response = ssm.get_parameter(Name=PARAMETER_NAME)
    topics = response['Parameter']['Value'].split(',')
    return topics if topics[0] else []

# Save topic list to ssm parameter
def save_used_topics(topics):
    value = ','.join(topics)
    ssm.put_parameter(Name=PARAMETER_NAME, Value=value, Type='StringList', Overwrite=True)

# Extract topic from fact
def extract_first_sentence(text):
    pattern = r'[.!?:,]'
    match = re.search(pattern, text)
    if match:
        return text[:match.start()]
    return text

# Keep only up to 10 topics at all times
def manage_used_topics(new_topic, used_topics):
    if new_topic not in used_topics:
        used_topics.append(new_topic)
        if len(used_topics) > 10:
            used_topics.pop(0)  # Remove the oldest topic
        save_used_topics(used_topics)

def get_random_words(how_many = 10):
    url = "https://random-word-api.herokuapp.com/word"
    params = {
        'number': how_many,
        'lang': 'en'
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        words = response.json()
        return ', '.join(words)
    else:
        return "No random words today, make something up!"

# Generate posts
def generate_random_fact_for_twitter(random_words):
    
    os.environ['OPENAI_API_KEY'] = get_parameter(OPENAI_API_KEY_PARAM)
    
    used_topics = get_used_topics()
    prompt= f"""You are an AI that provides random interesting facts suitable for Twitter posts. Generate an interesting and little-known fact related to one of the following: {random_words}. 
        It shouldn't be a plain definition but a random trivia loosely connected to one of the above words.
        The fact should be concise, informative, and fit within the character limit for a tweet (280 characters). Don't use hashtags. Don't start with 'Did you know'. Emotes are optional.
        Try to make it different from previous facts: {', '.join(used_topics)}.
        """
    print(prompt)
    
    client = OpenAI(
        api_key = os.environ.get("OPENAI_API_KEY"),
    )
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        model = "gpt-4o-mini",
        n=1
    )
    
    fact = chat_completion.choices[0].message.content
    if fact:
        first_sentence = extract_first_sentence(fact)
        manage_used_topics(first_sentence, used_topics)
    return fact


def generate_image(fact):

    os.environ['OPENAI_API_KEY'] = get_parameter(OPENAI_API_KEY_PARAM)
    
    client = OpenAI(
        api_key = os.environ.get("OPENAI_API_KEY"),
    )
    
    response = client.images.generate(
      model="dall-e-2",
      prompt=f"Generate an image to match the following fun fact: {fact}",
      size="1024x1024",
      quality="standard",
      n=1,
    )
    
    return response.data[0].url


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


def post_tweet_with_image(fact, media_id):
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    # text = fact
    payload = {"text": fact, "media": {"media_ids": [media_id]}}

    response = oauth.post("https://api.twitter.com/2/tweets", json=payload)

    if response.status_code != 201:
        raise Exception(
            "Request returned an error: {} {}".format(response.status_code, response.text)
        )

    print("Response code: {}".format(response.status_code))
    json_response = response.json()
    print(json.dumps(json_response, indent=4, sort_keys=True))
    

def post_without_image(fact):
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    # text = fact
    payload = {"text": fact}

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
        # Get random words
        random_words = get_random_words()
        print("fetched random words: ", random_words)
        
        # Generate a fact
        fact = generate_random_fact_for_twitter(random_words)
        print("generated a fact: ", fact)
        
        try:
            # Generate an image
            image_url = generate_image(fact)
            print("generated an image: \n", image_url)
            
            # Upload to Twitter
            media_id = upload_image_to_twitter(image_url)
            print("uploaded to twitter")
            
            # Post
            post_tweet_with_image(fact, media_id)
            print("Posted!")
            
        except Exception as e:
            print(f"Could not generate/upload an image: {str(e)}")
            
            post_without_image(fact)
            print("Posted (without image)!")
        
        return {
                'statusCode': 200,
                'body': json.dumps('Tweet posted successfully!')
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }