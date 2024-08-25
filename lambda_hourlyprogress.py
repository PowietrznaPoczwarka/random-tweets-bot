import json
from requests_oauthlib import OAuth1Session
from datetime import datetime, timedelta
import dateutil.tz
import time
import os

def get_year_progress():

    seoul_tz = dateutil.tz.gettz('Asia/Seoul')
    now = datetime.now(tz=seoul_tz)

    # Rounding up to the nearest hour
    if now.minute >= 30:
        now = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        now = now.replace(minute=0, second=0, microsecond=0)

    start_of_year = datetime(now.year, 1, 1, tzinfo=seoul_tz)
    end_of_year = datetime(now.year + 1, 1, 1, tzinfo=seoul_tz)
    total_duration = end_of_year - start_of_year
    elapsed_duration = now - start_of_year
    progress = (elapsed_duration / total_duration) * 100
    
    return now, progress

def post_to_twitter():

    consumer_key = os.environ.get('CONSUMER_KEY')
    consumer_secret = os.environ.get('CONSUMER_SECRET')
    access_token = os.environ.get('ACCESS_TOKEN')
    access_token_secret = os.environ.get('ACCESS_TOKEN_SECRET')
    
    now, progress = get_year_progress()
    
    text = f'{progress:.3f}% of the year {now.year} has passed.'
    payload = {"text": text}
    
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
    
    return response

def lambda_handler(event, context):
    
    # Script is scheduled to run exactly at: 59 * * * *
    # It waits 45 seconds, then executes the function measuring time and posts it on X (approx. 5-10 secs).
    # Goal is to run the code just before the next hour.

    time.sleep(45)
    response = post_to_twitter()
    
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