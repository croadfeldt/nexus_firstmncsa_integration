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

# Debug logging - defaults to on, set DEBUG=false to disable
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'

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


def log(msg):
    now = datetime.datetime.now()
    print("{}: {}".format(now.strftime("%Y-%m-%d %H:%M:%S"), msg))


def log_debug(msg, obj=None):
    if DEBUG:
        now = datetime.datetime.now()
        print("{}: [DEBUG] {}".format(now.strftime("%Y-%m-%d %H:%M:%S"), msg))
        if obj is not None:
            pprint.pp(obj)


def get_block_text(block):
    block_type = block.get('type')
    log_debug("Processing block type: {}".format(block_type), block)

    # rich_text blocks have a nested elements structure
    if block_type == 'rich_text':
        texts = []
        for element in block.get('elements', []):
            for sub in element.get('elements', []):
                if sub.get('type') == 'text':
                    texts.append(sub.get('text', ''))
                elif sub.get('type') == 'link':
                    texts.append(sub.get('text', ''))
        return ''.join(texts)

    # section blocks have a top-level 'text' dict
    elif block_type == 'section':
        block_text = block.get('text', {})
        text = block_text.get('text', '')
        # Unescape Slack's HTML encoding
        text = text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
        return text

    # Ignore other block types (divider, image, actions, etc.)
    return ''


# Silently ignore channel_join and other message subtypes we don't care about
@app.event({"type": "message", "subtype": "channel_join"})
def handle_channel_join(body, logger):
    logger.debug("Ignoring channel_join event")


@app.event({"type": "message", "subtype": "channel_leave"})
def handle_channel_leave(body, logger):
    logger.debug("Ignoring channel_leave event")


@app.event({"type": "message", "subtype": "message_changed"})
def handle_message_changed(body, logger):
    logger.debug("Ignoring message_changed event")


@app.event({"type": "message", "subtype": "message_deleted"})
def handle_message_deleted(body, logger):
    logger.debug("Ignoring message_deleted event")


@app.event({"type": "message", "subtype": "bot_add"})
def handle_bot_add(body, logger):
    logger.debug("Ignoring bot_add event")


@app.message('')
def message_hello(message, say):
    log_debug("RAW MESSAGE RECEIVED", message)

    subtype = message.get('subtype')

    # Only process bot_message subtypes, ignore everything else
    if subtype != 'bot_message':
        log_debug("Ignoring non-bot message subtype: {}".format(subtype))
        return

    log("Message from bot: {}".format(message.get('bot_id')))

    msg_text = message.get('text', '')

    # Ignore Nexus channel setup/introductory messages
    if "This channel will receive" in msg_text:
        log("Ignoring channel setup message from bot {}".format(message.get('bot_id')))
        return

    # Ignore LRI inspection flag messages (handled by the inspection
    # team directly via the reinspection channel; no CSA ticket needed)
    if "has had an inspection item flagged for the LRI" in msg_text:
        log("Ignoring LRI flag message from bot {}".format(message.get('bot_id')))
        return

    # Ignore reinspection request messages
    if "has been flagged for reinspection" in msg_text or "requested reinspection" in msg_text:
        log("Ignoring reinspection message from bot {}".format(message.get('bot_id')))
        return

    # Order matters - volunteer check must come before generic "has requested help"
    if "volunteer has requested help" in msg_text:
        contact_name = 'Nexus - Volunteer'
    elif "FTA request for team" in msg_text:
        contact_name = 'Nexus - FTA'
    elif "has requested help" in msg_text:
        contact_name = 'Nexus - Team'
    else:
        log("Unrecognized bot message, please tell Chris")
        log_debug("Unrecognized message text: {}".format(msg_text))
        return

    team_match = re.search(r"team\s+(\d+)", msg_text, re.IGNORECASE)
    team_number = team_match.group(1) if team_match else 'Unknown'
    event_name = eventMap.get(message['channel'], 'Off Season')

    description = "\n".join(filter(None, map(get_block_text, message.get('blocks', []))))

    webform = {
        'title': msg_text,
        'teamNumber': team_number,
        'frcEvent': event_name,
        'priority': 'Medium',
        'description': description,
        'contactName': contact_name,
        'contactEmail': 'firstmn.csa@gmail.com',
        'problemCategory': 'Other or not sure',
        'attachments': []
    }

    log_debug("Webform payload:", webform)

    headers = {
        'Content-type': 'application/json',
        'API-Key': firstmncsa['api_key']
    }

    log("Posting CSA ticket for team {} at {} via {}".format(
        team_number, event_name, contact_name))

    try:
        resp = requests.post(
            url=firstmncsa['api_endpoint'],
            headers=headers,
            json=webform,
            timeout=10
        )
        resp.raise_for_status()
        log("CSA ticket created successfully for team {} at {}".format(team_number, event_name))
        log_debug("API response: {}".format(resp.text))
        say("✅ CSA ticket created for team {} at {}.".format(team_number, event_name))

    except requests.exceptions.Timeout:
        log("ERROR: API call timed out for team {} at {}".format(team_number, event_name))
        say("⚠️ Failed to create CSA ticket for team {} - API timed out. Please submit manually.".format(team_number))

    except requests.exceptions.HTTPError as e:
        log("ERROR: API returned HTTP error: {}".format(str(e)))
        log_debug("API error response: {}".format(resp.text))
        say("⚠️ Failed to create CSA ticket for team {} - API error ({}). Please submit manually.".format(
            team_number, resp.status_code))

    except requests.exceptions.RequestException as e:
        log("ERROR: API call failed: {}".format(str(e)))
        say("⚠️ Failed to create CSA ticket for team {} - Connection error. Please submit manually.".format(team_number))


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
