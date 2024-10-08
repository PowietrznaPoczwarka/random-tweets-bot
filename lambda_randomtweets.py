import boto3
from requests_oauthlib import OAuth1Session
import json
import re
from openai import OpenAI
import os
import requests

# Parameter Store
ssm = boto3.client('ssm')
PARAMETER_NAME = "/randomtweets/used_topics"
OPENAI_API_KEY_PARAM = "/randomtweets/openai_api_key"

CONSUMER_KEY_PARAM = os.environ.get('CONSUMER_KEY_PARAM')
CONSUMER_SECRET_PARAM = os.environ.get('CONSUMER_SECRET_PARAM')
ACCESS_TOKEN_PARAM = os.environ.get('ACCESS_TOKEN_PARAM')
ACCESS_SECRET_PARAM = os.environ.get('ACCESS_SECRET_PARAM')

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
            used_topics.pop(0)
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

random_words = get_random_words()

# Generate posts
def generate_random_fact_for_twitter(random_words):
    
    os.environ['OPENAI_API_KEY'] = get_parameter(OPENAI_API_KEY_PARAM)
    used_topics = get_used_topics()
    prompt= f"""You are an AI that provides random interesting facts suitable for Twitter posts. Generate an interesting and little-known fact related to one of the following: {random_words}. 
        The fact should be concise, informative, and fit within the character limit for a tweet (280 characters). Don't use hashtags. Don't start with 'Did you know'. 
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


def lambda_handler(event, context):
    
    consumer_key = CONSUMER_KEY_PARAM
    consumer_secret = CONSUMER_SECRET_PARAM
    access_token = ACCESS_TOKEN_PARAM
    access_token_secret = ACCESS_SECRET_PARAM

    payload = {"text": generate_random_fact_for_twitter()}

    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    # Posting the tweet
    response = oauth.post(
        "https://api.twitter.com/2/tweets",
        json=payload,
    )

    if response.status_code != 201:
        raise Exception(
            "Request returned an error: {} {}".format(response.status_code, response.text)
        )

    print("Response code: {}".format(response.status_code))

    json_response = response.json()
    print(json.dumps(json_response, indent=4, sort_keys=True))

    return {
        'statusCode': response.status_code,
        'body': json.dumps(json_response, indent=4, sort_keys=True)
    }