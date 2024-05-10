# Stream Guard Bot

## Instructions

### Environment Setup
Start by creating a virtual environment in your project directory
```
python -m venv .venv
```

Activate the virtual environment. On Linux and MacOs:
```
source .venv/bin/activate
```

Install the requirements
```
pip install -r requirements.txt
```

### Access Token Setup
You'll need to first [register your application/bot](https://dev.twitch.tv/docs/authentication/register-app/) on Twitch to get your `CLIENT_ID` and `CLIENT_SECRET`.

After you'll need to create a user access token with `chat:read` and `chat:edit` [permissions](https://dev.twitch.tv/docs/authentication/scopes/). There are many various ways to do this. I personally use [Twitch CLI](https://dev.twitch.tv/docs/cli/) with the following command `twitch token -u -s 'chat:read chat:edit`.

Finally you'll have to create an account with OpenAI and create your [Project API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key) for `OPEN_AI_KEY`.

### Local Envrionment Variables
Now that you have all of the necessary environment variables, create `.env` to store all the information. Do not change the file name.
```
touch .env
```

Please paste the relevant information. Do not change the environment variable names.
```
CLIENT_ID='<Twitch Client ID>'
CLIENT_SECRET='<Twitch Client Secret>'
ACCESS_TOKEN='<Twitch User Access Token>'
REFRESH_TOKEN='<Twitch User Refresh Token>'
OPENAI_API_KEY='<OpenAI Secret Key>'
INITIAL_CHANNEL='<your channel>'
```
**Note**: Initial channel is the channel where your bot will reside in (e.g. twitch.tv/<your channel>) 

For information regarding:

- [Twitch Client ID and Client Secret](https://dev.twitch.tv/docs/authentication/register-app/)
- [Twitch CLI](https://dev.twitch.tv/docs/cli/)
- [OpenAI API Key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key)


### Run Application
Start the program
```
main.py
```

Successful Output
```
Logged in as | <your channel>
User id is | <your id>
```

Admittedly it was a lot of work to get this running. I will continue working on the application to be a little more seemless.