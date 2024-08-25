import boto3
from requests_oauthlib import OAuth1Session
import json
import re
from openai import OpenAI
import os
import requests

# Ustawienia Parameter Store
ssm = boto3.client('ssm')
PARAMETER_NAME = "/randomtweets/news_history"
OPENAI_API_KEY_PARAM = "/randomtweets/openai_api_key"

def get_parameter(name):
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response['Parameter']['Value']

# Extract history tweets
def get_used_topics():
    response = ssm.get_parameter(Name=PARAMETER_NAME)
    topics = response['Parameter']['Value'].split(',')
    return topics if topics[0] else []

def extract_first_sentence(text):
    pattern = r'[.!?:]' # changed regex pattern not to include ,
    match = re.search(pattern, text)
    if match:
        return text[:match.start()]
    return text

# Keep only up to 5 tweets history at all times
def manage_used_topics(new_topic, used_topics):
    if new_topic not in used_topics:
        used_topics.append(new_topic)
        if len(used_topics) > 5:
            used_topics.pop(0)  # Remove the oldest topic
        value = ','.join(used_topics)
        ssm.put_parameter(Name=PARAMETER_NAME, Value=value, Type='StringList', Overwrite=True)

# Get headlines and content
def get_news():
    url = "https://newsapi.org/v2/top-headlines?sources=bbc-news&apiKey=417d86108b0b45b8aa0e1afa3d0699be"
    response = requests.get(url)
    articles = response.json()['articles'][0:5]
    output_string = ""
    
    for article in articles:
        output_string += "Title: " + article['title'] + " \n" + "Description: " + article['description'] + " \n" + "Content" + article['content'] + "\n\n"
            
    return output_string
    

# Generate posts
def generate_news_summary():
    
    os.environ['OPENAI_API_KEY'] = get_parameter(OPENAI_API_KEY_PARAM)
    
    used_topics = get_used_topics()
    output_string = get_news()
    
    prompt= f"""You are an AI that summarizes news. Choose the most important piece (or pieces) of news from those listed below and summarize it to a tweet format. 
        Be very concise and fit within the character limit for a tweet (280 characters) - Max 2/3 sentences. Don't use hashtags.
        Here are the news pieces:
        {output_string}
        Avoid repeating topics already covered recently: {', '.join(used_topics)}. If it's impossible to tweet something new write an interesting fact about politics.
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
    
    tweet = chat_completion.choices[0].message.content
    
    if tweet:
        first_sentence = extract_first_sentence(tweet)
        manage_used_topics(first_sentence, used_topics)
    return tweet


def lambda_handler(event, context):
    
    consumer_key = os.environ.get('CONSUMER_KEY')
    consumer_secret = os.environ.get('CONSUMER_SECRET')
    access_token = os.environ.get('ACCESS_TOKEN')
    access_token_secret = os.environ.get('ACCESS_TOKEN_SECRET')

    payload = {"text": generate_news_summary()}

    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    # Making the request
    response = oauth.post(
        "https://api.twitter.com/2/tweets",
        json=payload,
    )

    if response.status_code != 201:
        raise Exception(
            "Request returned an error: {} {}".format(response.status_code, response.text)
        )

    print("Response code: {}".format(response.status_code))

    # Saving the response as JSON
    json_response = response.json()
    print(json.dumps(json_response, indent=4, sort_keys=True))

    return {
        'statusCode': response.status_code,
        'body': json.dumps(json_response, indent=4, sort_keys=True)
    }