import os
import pprint
import requests
import re
import datetime
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
firstmncsa['api_key'] = os.environ['FIRSTMNCSA_API_KEY']
firstmncsa['url'] = os.environ['FIRSTMNCSA_URL']
firstmncsa['api_endpoint'] = os.environ['FIRSTMNCSA_API_ENDPOINT']

eventMap={'C070UJW0X46':'Off Season',
          'C070SC5LGB1':'Duluth - Northern Lights',
          'C0716UMRGEN':'Duluth - Lake Superior',
          'C070SCBQM2T':'10,000 Lakes',
          'C0716RAMJQ3':'Granite City',
          'C08F36XRR4L':'North Star',
          'C0716UR6BEW':'Great Northern'
          }

# Get the current date and time
now = datetime.datetime.now()

# Create a datetime object representing the current date and time

# Display a message indicating what is being printed
print("Current date and time : ")

# Print the current date and time in a specific format
print(now.strftime("%Y-%m-%d %H:%M:%S"))

# Install the Slack app and get xoxb- token in advance
app = App(token=os.environ["SLACK_BOT_TOKEN"])

#@app.message("hello")
#def message_hello(message, say):
#    # say() sends a message to the channel where the event was triggered
#    say(f"Hey there <@{message['user']}>!")

# Function to grab data from blocks.
def get_block_text(block):
    print(now.strftime("%Y-%m-%d %H:%M:%S"))
    pprint.pp(block)
    return str(block['text']['text'])

# Look for CSA Requests
@app.message('')
def message_hello(message, say):
    print(now.strftime("%Y-%m-%d %H:%M:%S"))
    pprint.pp(message)

    # Check to see if the message was sent by a bot
    if ('subtype','bot_message') in message.items():
        print("{}: Message from a bot: {}".format(now.strftime("%Y-%m-%d %H:%M:%S"),message['bot_id']))

        if "requested help" in message['text']:
            # Prep the requests object used to post this to the firstmn.csa web form
            webform = {
                'title': message['text'],
                'teamNumber': re.search(r"\d+",message['text']).group(),
                'frcEvent': eventMap[message['channel']],
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
                'teamNumber': re.search(r"\d+",message['text']).group(),
                'frcEvent': eventMap[message['channel']],
                'priority': 'Medium',
                'description': "\n".join(list(map(get_block_text, message['blocks']))),
                'contactName': 'Nexus - FTA',
                'contactEmail': 'firstmn.csa@gmail.com',
                'problemCategory': 'Other or not sure',
                'attachments': []
            }
        else:
            print("{}: Unrecognized message, please tell Chris".format(now.strftime("%Y-%m-%d %H:%M:%S"));
            return();

        headers = {'Content-type': 'application/json',
            'API-Key': firstmncsa['api_key']}

                  print("{}: Posting form to URL: {}".format(now.strftime("%Y-%m-%d %H:%M:%S"),firstmncsa['api_endpoint']))
        pprint.pp(webform)

        # Post the data to the First MN CSA
        resp = requests.post(url=firstmncsa['api_endpoint'], headers=headers, json=webform)

        # How did that go?
                  print("{}: Response from web form submission: {}".format(now.strftime("%Y-%m-%d %H:%M:%S"),resp.text)

        # Let the world know it was submitted.
        say("Message report status: {}".format(resp.text))
    else:
        # say() sends a message to the channel where the event was triggered
        say(f"USER: <@{message['user']}>!")
        say ("Message was not from Nexus, ignoring.")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
