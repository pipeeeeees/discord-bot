from pipesbot import PIPEEEEEES_DISCORD_ID
from pipesbot import schedule_messages
from pipesbot import db_handler
import datetime

async def send_message(client, channel_id, message):
    channel = await client.fetch_channel(channel_id)
    await channel.send(message)

async def handler(client, message, scheduler):
    pbot = client.user
    content = message.content
    author = message.author
    channel = message.channel
    guild = message.guild
    mentions = message.mentions
    attachments = message.attachments
    embeds = message.embeds
    created_at = message.created_at
    edited_at = message.edited_at
    
    # Do not reply to yourself, Pipes Bot!
    if message.author == client.user:
        return
    
    #print(author)
    #print(channel)
    #print(attachments)
    #await send_message(client,channel.id, "yo")



    # Manual Schedule
    """
    Format: "$remindme, 9-23-1999, 14:20, get something for Stephen's birthday"
    it will:
       1. add this entry to the database (db_handler.py)
       2. add the request to the scheduler (schedule_messages.py)
    """
    if message.content.startswith('$remindme,'):
        # Parse the data
        msg = message.content.replace('$remindme,','')
        msg_list = msg.split(',')
        raw_date = msg_list[0].replace(' ','')
        raw_date_split = raw_date.split('-')
        raw_time = msg_list[1].replace(' ','')
        raw_time_split = raw_time.split(':')
        joined_string = ','.join(msg_list[2:])

        # Create the right DS's
        date = datetime.date(int(raw_date_split[2]), int(raw_date_split[0]), int(raw_date_split[1]))
        time = datetime.time(int(raw_time_split[0]), int(raw_time_split[1])) 
        channel_id =  channel.id 
        message = joined_string

        # Upload to the scheduler
        await scheduler.schedule_message(channel_id, message, date, time)

        # Upload to the database
        db = db_handler.DatabaseHandler(r'pipesbot/database/messages.db')
        db.add_message(author.id, channel_id, int(raw_date_split[2]), int(raw_date_split[0]), int(raw_date_split[1]), int(raw_time_split[0]), int(raw_time_split[1]), message)
        db.close()

"""
# Access Pipes Bot as a Member object
pbot = client.user

# Access the content of the message
content = message.content

# Access the author of the message as a Member object
author = message.author

# Access the channel where the message was sent as a TextChannel object
channel = message.channel

# Access the guild where the message was sent as a Guild object
guild = message.guild

# Access the list of Member objects that were mentioned in the message
mentions = message.mentions

# Access the list of Attachment objects that were attached to the message
attachments = message.attachments

# Access the list of Embed objects that were included in the message
embeds = message.embeds

# Access the timestamp of when the message was created as a datetime.datetime object
created_at = message.created_at

# Access the timestamp of when the message was last edited as a datetime.datetime object, or None if it was never edited
edited_at = message.edited_at
"""