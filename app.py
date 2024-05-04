import os
import pprint
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# FIRSTMN.CSA website data
# WebForm data
# Form name - cardForm
# submit button name - submit
# title - type string - used as title for the issue
# teamNumber - type int - used as the team number with the issue
# frcEvent - string - used to identify which event has the team with an issue
# problemCategory - type list of strings - need mapping if possible, future item
# priority - type list of strings - set to medium for now
# description - type long string - used for additional details, drop all text in here for now
# attachments - binary data - used for additional contextual information in form of photos, video, etc...
# contactName - string - used to indicate who is reporting the issue
# contactEmail - string - used to indicate who is reporting the issue
firstmncsa = {}

# Grab the environment variables needed
frcEventName = os.environ['FRC_EVENT_NAME']
firstmncsa['api_key'] = os.environ['FIRSTMNCSA_API_KEY']
firstmncsa['url'] = os.environ['FIRSTMNCSA_URL']
firstmncsa['api_endpoint'] = os.environ['FIRSTMNCSA_API_ENDPOINT']

# Install the Slack app and get xoxb- token in advance
app = App(token=os.environ["SLACK_BOT_TOKEN"])

#@app.message("hello")
#def message_hello(message, say):
#    # say() sends a message to the channel where the event was triggered
#    say(f"Hey there <@{message['user']}>!")

# Function to grab data from blocks.
def get_block_text(block):
    pprint.pp(block)
    return str(block['text']['text'])

# Look for CSA Requests
@app.message('')
def message_hello(message, say):
    pprint.pp(message)

    # Check to see if the message was sent by a bot
    if ('subtype','bot_message') in message.items():
        print("Message from a bot: {}".format(message['bot_id']))

        if "requested help" in message['text']:
            # Prep the requests object used to post this to the firstmn.csa web form
            webform = {
                'title': message['text'],
                'teamNumber': message['text'].split()[1],
                'frcEvent': frcEventName,
                'priority': 'Medium',
                'description': "\n".join(list(map(get_block_text, message['blocks']))),
                'contactName': 'Nexus - FTA',
                'contactEmail': 'firstmn.csa@gmail.com',
                'problemCategory': 'Other or not sure',
                'attachments': []
            }
        elif "FTA request" in message['text']:
            # Prep the requests object used to post this to the firstmn.csa web form
            webform = {
                'title': message['text'],
                'teamNumber': message['text'].split()[-1],
                'frcEvent': frcEventName,
                'priority': 'Medium',
                'description': "\n".join(list(map(get_block_text, message['blocks']))),
                'contactName': 'Nexus - FTA',
                'contactEmail': 'firstmn.csa@gmail.com',
                'problemCategory': 'Other or not sure',
                'attachments': []
            }
        else:
            print("Unrecognized message, please tell Chris");
            stop();

        headers = {'Content-type': 'application/json',
            'API-Key': firstmncsa['api_key']}

        print("Posting form to URL: {}".format(firstmncsa['api_endpoint']))
        pprint.pp(webform)

        # Post the data to the First MN CSA
        resp = requests.post(url=firstmncsa['url'], headers=headers, json=webform)

        # How did that go?
        print("Response from web form submission: %s" % resp.text)

        # Let the world know it was submitted.
        say("Message report status: {}".format(resp.text))
    else:
        # say() sends a message to the channel where the event was triggered
        say(f"USER: <@{message['user']}>!")
        say ("Message was not from Nexus, ignoring.")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
