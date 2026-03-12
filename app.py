import os
import pprint
import requests
import re
import datetime
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# FIRSTMN.CSA website data
firstmncsa = {}
firstmncsa['api_key'] = os.environ['FIRSTMNCSA_API_KEY']
firstmncsa['url'] = os.environ['FIRSTMNCSA_URL']
firstmncsa['api_endpoint'] = os.environ['FIRSTMNCSA_API_ENDPOINT']

eventMap = {
    'C070UJW0X46': 'Off Season',
    'C070SC5LGB1': 'Duluth - Northern Lights',
    'C0716UMRGEN': 'Duluth - Lake Superior',
    'C070SCBQM2T': '10,000 Lakes',
    'C0716RAMJQ3': 'Granite City',
    'C08F36XRR4L': 'North Star',
    'C0716UR6BEW': 'Great Northern',
    'C0716TNHADQ': 'State',
    'C07142699HB': 'Off Season',
    'C071VN7D5J4': 'Off Season',
}

app = App(token=os.environ["SLACK_BOT_TOKEN"])


def get_block_text(block):
    now = datetime.datetime.now()
    print("{}: Processing block:".format(now.strftime("%Y-%m-%d %H:%M:%S")))
    pprint.pp(block)

    # Safely handle blocks that may not have a top-level 'text' dict
    block_text = block.get('text')
    if block_text is None:
        return ''
    # 'text' can be a dict (rich blocks) or a plain string
    if isinstance(block_text, dict):
        return str(block_text.get('text', ''))
    return str(block_text)


# Silently ignore channel_join and other message subtypes we don't care about
@app.event({"type": "message", "subtype": "channel_join"})
def handle_channel_join(body, logger):
    logger.debug("Ignoring channel_join event")


@app.message('')
def message_hello(message, say):
    now = datetime.datetime.now()

    print("=" * 60)
    print("{}: RAW MESSAGE RECEIVED".format(now.strftime("%Y-%m-%d %H:%M:%S")))
    print("=" * 60)
    pprint.pp(message)
    print("=" * 60)

    # Ignore messages with any subtype (joins, leaves, edits, etc.)
    if message.get('subtype') is not None:
        print("{}: Ignoring message subtype: {}".format(
            now.strftime("%Y-%m-%d %H:%M:%S"), message.get('subtype')))
        return

    if ('subtype', 'bot_message') in message.items():
        print("{}: Message from a bot: {}".format(
            now.strftime("%Y-%m-%d %H:%M:%S"), message['bot_id']))

        msg_text = message.get('text', '')

        if "requested help" in msg_text or "FTA request" in msg_text:
            team_match = re.search(r"\d+", msg_text)
            team_number = team_match.group() if team_match else 'Unknown'

            webform = {
                'title': msg_text,
                'teamNumber': team_number,
                'frcEvent': eventMap.get(message['channel'], 'Off Season'),
                'priority': 'Medium',
                'description': "\n".join(list(map(get_block_text, message.get('blocks', [])))),
                'contactName': 'Nexus - FTA',
                'contactEmail': 'firstmn.csa@gmail.com',
                'problemCategory': 'Other or not sure',
                'attachments': []
            }
        else:
            print("{}: Unrecognized bot message, please tell Chris".format(
                now.strftime("%Y-%m-%d %H:%M:%S")))
            return

        headers = {
            'Content-type': 'application/json',
            'API-Key': firstmncsa['api_key']
        }

        print("{}: Posting form to URL: {}".format(
            now.strftime("%Y-%m-%d %H:%M:%S"), firstmncsa['api_endpoint']))
        pprint.pp(webform)

        resp = requests.post(url=firstmncsa['api_endpoint'], headers=headers, json=webform)

        print("{}: Response from web form submission: {}".format(
            now.strftime("%Y-%m-%d %H:%M:%S"), resp.text))

        say("Message report status: {}".format(resp.text))

    else:
        print("{}: Message was not from a bot, ignoring.".format(
            now.strftime("%Y-%m-%d %H:%M:%S")))


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
