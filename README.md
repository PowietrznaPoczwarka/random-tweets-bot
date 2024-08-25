# random-tweets-bot #

Automated X (formerly Twitter) account(s) posting random things with X API (and OpenAI API).

Project consists of a few X automated accounts and their respective scheduled (with Amazon EventBridge) AWS Lambda functions:

- [Daily Trivia Drop](https://x.com/DailyTriviaDrop)

Posts meaningless facts generated with gpt-4o-mini. In order to keep posts randomized, model is asked to generate a trivia related to one of the provided random words fetched via [Random Word API](https://random-word-api.herokuapp.com/home).

- [Daily Wikimedia Drop](https://x.com/DailyWikimedia)

Posts random wikipedia image fetched via [Wikimedia REST API](https://www.mediawiki.org/wiki/Wikimedia_REST_API).

- [Daily News Drop](https://x.com/DailyNewsDrop_)

Selects and summarizes some news into tweet-sized format (from [News API](https://newsapi.org/)).

- [Hourly Year Update](https://x.com/HourYearUpdate)

Calculates the percentage of the year that has passed and automatically posts that percentage as a tweet using Twitter's API.

### Requirements ###

- AWS Account
- OpenAI API key
- X Developer Account (+ API keys and tokens)
- News API key


### TODO

- European Weather Station

Retrieves the current weather information (such as temperature, humidity, etc.) for a randomly selected European city and posts this data as a tweet.



