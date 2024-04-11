import datetime
import time
from slack import WebClient
from slack.errors import SlackApiError

# Token needs the following scopes:
# channels:read
# channels:history
# channels:join
# channels:manage
SLACK_API_TOKEN = 'Your Slack Token Here'

ARCHIVE_LAST_MESSAGE_AGE_DAYS = 90

oldest_message_time_to_prevent_archive = (
    datetime.datetime.now() - datetime.timedelta(days=ARCHIVE_LAST_MESSAGE_AGE_DAYS)
).timestamp()

client = WebClient(SLACK_API_TOKEN)

my_user_id = client.auth_test()['user_id']


def channel_has_recent_messages(channel_id):
    # Getting up to 2 messages younger than ARCHIVE_LAST_MESSAGE_AGE_DAYS
    response = client.conversations_history(
        channel=channel_id,
        oldest=oldest_message_time_to_prevent_archive,
        limit=2
    )
    # Filter out message about our bot joining this channel
    real_messages = list(filter(lambda m: m['user'] != my_user_id, response['messages']))
    # If we found at least one - return True, if not - False
    return len(real_messages) > 0


def handle_api_error(error):
    if error.response["error"] == "ratelimited":
        retry_after = int(error.response.headers["Retry-After"])
        print(f"Rate limited. Retrying after {retry_after} seconds.")
        time.sleep(retry_after)
    else:
        print(f"Slack API error: {error.response['error']}")


next_cursor = None
while True:
    try:
        response = client.conversations_list(exclude_archived=True, limit=200, cursor=next_cursor)
        for channel in response['channels']:
            if not channel['is_member']:
                client.conversations_join(channel=channel['id'])
            if channel_has_recent_messages(channel['id']):
                print('#' + channel['name'] + ': has recent messages')
            else:
                print('#' + channel['name'] + ': archiving')
                client.conversations_archive(channel=channel['id'])
        if response.get('response_metadata') and response['response_metadata'].get('next_cursor'):
            next_cursor = response['response_metadata']['next_cursor']
        else:
            print("Reached the end of channels.")
            break
    except SlackApiError as e:
        handle_api_error(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Handle other unexpected errors gracefully
        break