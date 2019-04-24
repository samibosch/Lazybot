# created by Sami Bosch on Wednesday, 31 October 2018

# This file contains all functions necessary to reply to messages
import asyncio
import re
import random
import threading
import time

import discord
import logger

from math import ceil, floor
from datetime import datetime, timedelta

from asynctimer import AsyncTimer
from utils import elem_in_string
import db_handler


commands = ['yo bot', 'yea bot', 'yea boi']


def init(client):
    client = client

    @client.command(aliases=['hey', 'hi', 'hello'], pass_context=True)
    async def ping(context):
        """Responds with "pong" + a mention to the first username in the arguments if present. Also sends a pm to the
        user using the command."""
        m = context.message
        if m.content.find(" ") > 0:
            user = m.server.get_member_named(m.content.split(" ")[1])
            await client.say("pong {}".format(user.mention))
        else:
            await client.say("pong")
        await client.send_message(context.message.author, "pong, but in private.")

    @client.command(pass_context=True)
    async def ban(context):
        """Takes a list of mentioned users + optionally an int. Bans all users in list, and if int has been supplied,
        unbans them after given time in days."""
        m = context.message

        if m.author.server_permissions.ban_members:
            if m.content.find(" ") > 0:
                try:
                    unban_time = float(m.content.split(" ")[-1])
                except ValueError:
                    unban_time = -1
            else:
                unban_time = -1

            for member in m.mentions:
                await client.ban(member, delete_message_days=0)
                await client.say("Banned {} for {} days (-1 = indefinite).".format(member.name, unban_time))

            if unban_time >= 0:
                async def unban_all():
                    for member in m.mentions:
                        await client.unban(m.server, member)
                        await client.send_message(m.channel, "unbanned {}.".format(member.name))

                AsyncTimer(unban_time * 86400, unban_all)
        else:
            await client.say("You do not have the permission to ban users")

    @client.command(pass_context=True)
    async def kick(context):
        """Takes a list of mentioned users and kicks them all."""
        m = context.message
        if m.author.server_permissions.kick_members:
            for member in m.mentions:
                await client.kick(member)
                await client.say("Kicked {}.".format(member.name))
        else:
            await client.say("You do not have the permission to kick users.")

    @client.command(aliases=['mute', 'silence'], pass_context=True)
    async def timeout(context):
        """Takes a list of mentioned users and a timeout at the end of the message and silences all users for the
        specified time in minutes."""
        m = context.message

        if m.author.server_permissions.manage_roles:
            muted = discord.utils.get(m.server.roles, name='Muted')
            if m.content.find(" ") > 0:
                try:
                    mute_time = float(m.content.split(" ")[-1])
                except ValueError:
                    mute_time = -1
            else:
                mute_time = -1

            if mute_time > 0:
                for member in m.mentions:
                    await client.add_roles(member, muted)
                    await client.say("Muted {} for {} minutes.".format(member.name, int(mute_time)))

                async def unmute_all():
                    for member in m.mentions:
                        await client.remove_roles(member, muted)
                        await client.send_message(m.channel, "Unmuted {}.".format(member.name))

                AsyncTimer(mute_time * 60, unmute_all)
            else:
                await client.say("Please provide a time (in minutes).")
        else:
            await client.say("You do not have the permission to ban users.")

    @client.command(aliases=['qs'], pass_context=True)
    async def queue_song(context):
        m = context.message
        pos1 = m.content.find(" ")
        if pos1 > 0:
            url = m.content.split(" ")[1]
            regex = re.compile(
                r'^(?:http|ftp)s?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            if re.match(regex, url) is not None:
                if not db_handler.has_song(url):
                    if db_handler.count_song(m.author.name) < 20:
                        comment = ""
                        pos2 = m.content[pos1:].strip().find(" ")
                        if pos2 > 0:
                            comment = m.content[pos2 + pos1 + 2:].strip()

                        db_handler.add_song_to_queue(url, m.author.name, comment)
                        await client.say("Added!")
                    else:
                        await client.say("You have exceeded the song cap.")
                else:
                    await client.say("This song is already submitted!")
            else:
                await client.say("Please provide a valid URL.")
        else:
            await client.say("Please give at least an URL.")

    @client.command(pass_context=True)
    async def set_song_channel(context):
        m = context.message
        if m.author.server_permissions.administrator:
            if len(m.channel_mentions) > 0:
                print(m.channel_mentions)
                db_handler.set_server(m.server.id, m.channel_mentions[0].id)
                await client.say("Channel {} configured.".format(m.channel_mentions[0].mention))
            else:
                await client.say("Please provide a channel.")
        else:
            await client.say("Insufficient permissions.")

    @client.command(pass_context=True)
    async def force_send(context):
        m = context.message
        if m.author.server_permissions.administrator:
            await send_song(False)
        else:
            await client.say("Insufficient permissions.")

    @client.command(aliases=['hm', 'hmmmmmmmm'], pass_context=True)
    async def how_many(context):
        m = context.message
        if len(m.mentions) == 0:
            await client.say("{} songs in queue.".format(db_handler.count_song()))
        else:
            for member in m.mentions:
                await client.say("{} has {} songs in queue.".format(member.name, db_handler.count_song(member.name)))

    @client.command(aliases=['ls'], pass_context=True)
    async def list_songs(context):
        await client.say(db_handler.list_songs(context.message.author.name))

    @client.event
    async def on_message(message):
        """responding to non command messages"""
        if message.author != client.user:
            if message.channel.name == "bots" and elem_in_string(commands, message.content):
                await client.send_message(message.channel,
                                          client.messages[random.choice(range(len(client.messages)))].content)

        await client.process_commands(message)

    def secs():
        x = datetime.today()
        x_temp = x.replace(hour=12, minute=0, second=0, microsecond=0)
        y = x_temp if x_temp > x else x_temp + timedelta(days=1)
        delta_t = y - x
        logger.info("now: {}, post time: {}".format(x, y))

        sec = delta_t.seconds + 1
        cnt1 = ceil(db_handler.count_song() / 15)
        post_time = round(86400 / cnt1)
        cnt = floor(sec / post_time)
        time_left = sec - cnt * post_time
        cnt = cnt if cnt != 0 else cnt1

        return cnt, post_time, time_left, sec

    async def send_song(timer=True):
        cnt, post_time, time_left, sec = secs()
        if timer:
            logger.info("Launching timer")
            AsyncTimer(sec, send_song)

        logger.info("sending: count: {}, post time: {}, time_left: {}, sec: {}".format(cnt, post_time, time_left, sec))

        i = 0
        cont = True
        while cont:
            song = db_handler.get_song()
            if song is not None:
                for s, c in db_handler.get_servers():
                    server = client.get_server(id=s)
                    channel = discord.utils.get(server.channels, id=c)
                    await client.send_message(channel, "Daily song: {}\nSubmitted by: {}\n{}".format(song[0], song[1],
                                                                                                     song[2]).strip())
            else:
                for s, c in db_handler.get_servers():
                    server = client.get_server(id=s)
                    channel = discord.utils.get(server.channels, id=c)
                    await client.send_message(channel, "No daily song today!")
                cont = False

            if timer:
                await asyncio.sleep(post_time)
            i += 1
            if i >= cnt:
                cont = False

    AsyncTimer(secs()[2], send_song)

    def log_time():
        cnt, post_time, time_left, sec = secs()
        logger.info("restart: count: {}, post time: {}, time_left: {}, sec: {}".format(cnt, post_time, time_left, sec))
        time.sleep(300)
        log_time()

    thread = threading.Thread(target=log_time)
    thread.start()
