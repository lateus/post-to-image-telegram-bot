#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

"""
Telegram bot to provide tools like simulate axies breeding: t.me/AxieInfinityTools_bot

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Send two Axie's IDs and it will reply with a simulation of the breed.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging, os, re, requests, datetime, tweepy, html
from io import BytesIO

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import api as API

# Enable logging
logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Telegram bot token
TOKEN = '5076087173:AAG5_poCSDwlLfA3jJGLVNXMedoJvS0mJJ0'
tweetUrlRegexp = re.compile('(https?:\/\/)?(www\.)?twitter\.com\/(\w+)\/status(es)?\/\d+\/?', flags = re.DOTALL)

# Setup twitter access
twitterAPI = API.setupTwitterAccess("QTisT5HlQgV5gJGJbWCOu7MLd", "2CKN9B0nzCKNzl2HXXRd0JkcasLnnJjcLrvmezDalw3lsTrpbX", "1073450779934105604-5cpRtgHDB85bhKThhXuZzJdAf2cxlz", "LMB4ttBqpjOVJI6ZPiFCdn2BPMV1jQbYO4mCqIGmRBwhP")

# Define a few command handlers. These usually take the two arguments update and
# context.
def start(update: Update, context: CallbackContext) -> None:
	"""Send a message when the command /start is issued."""
	user = update.effective_user
	if context.args and context.args[0] == "contribute":
		contribute_command(update, context)
	else:
		update.message.reply_markdown_v2(
			'''Hi ''' + user.mention_markdown_v2() + '''\!\n'''
			'''Send a tweet\'s url to convert it to an image\.'''
		)


def help_command(update: Update, context: CallbackContext) -> None:
	"""Send a message when the command /help is issued."""
	update.message.reply_markdown_v2(
		'''*Help \- Axie Infinity Tools Bot*\n\n'''
		'''_How to use?_\n'''
		'''Send one Axie\'s ID to get basic info\.\n'''
		'''Send two Axie\'s IDs to simulate breeding\.\n'''
		'''Send one Axie\'s ID twice to check genes\.\n'''
		'''Send a ronin address to check balance\.\n'''
		'''_In a group_\n'''
		'''You can use command `/breed` followed one or two IDs\. For example `/breed 2975324` or `/breed 1680265 740196`\.\n'''
		'''The same applies to `/info`, `/slp` and the rest of commands with arguments\.\n'''
		'''*Note:* When in a group, other bots with access to messages may interfere and consume this bot\'s commands\. To solve that, promote this bot to admin \(it doesn\'t need any permission, so you can disable them all\)\.\n'''
		'''\n__Commands__\n'''
		'''`/info id` \- Show basic info of this Axie\n'''
		'''`/breed id1 id2` \- Simulate breed of these Axies\n'''
		'''`/breed id` \- Read genes of this Axie\n'''
		'''`/pic id` \- Get a picture of this Axie\n'''
		'''`/slp ronin` \- Check the balance of a player\n'''
		'''`/contribute` \- Contribute to the development of this bot\n'''
		'''`/help` \- Show this message\n\n'''
		'''Check [our blog](https://telegra.ph/Axie-Infinity-Tools-Bot-10-21), also available [in Spanish](https://telegra.ph/Axie-Infinity-Tools-Bot-Espa%C3%B1ol-10-21)\.'''
	, disable_web_page_preview=True)


def contribute_command(update: Update, context: CallbackContext) -> None:
	update.message.reply_markdown_v2(
		'''*We need your support to keep pushing forward\!*\n\n'''
		'''_If you like this bot, your contributions are welcome:_\n'''
		'''__Ronin:__ `ronin:c1f5233e97f1a859e1aad4dcb32ba2d7426f8fd8`\n'''
		'''__Ethereum:__ `0x00e715b01058c222fd8dfa0e61f59a71716c8c11\n`'''
		'''__Bitcoin:__ `1BADpmDUWGQpHq2BoWczDGcet2nKT5sNBj`'''
	)


def replyToText(update: Update, context: CallbackContext) -> None:
	# Check if tweet link?
	messageText = update.message.text
	tweetUrlMatch = tweetUrlRegexp.search(messageText)
	if tweetUrlMatch:
		matchString = tweetUrlMatch.group()
		parsedId = matchString
		if parsedId.endswith('/'):
			parsedId = parsedId[:-1]
		index1 = parsedId.rindex('/') + 1
		index2 = len(parsedId)
		parsedId = parsedId[index1:index2]
		if parsedId.isnumeric() and int(parsedId) > 0:
			# get config (theme, size, banner)
			isDark = " dark" in messageText
			width = 0
			height = 0
			if " w=" in messageText:
				tempIndex = messageText.rindex(" w=") + len(" w=")
				width = int(''.join(filter(str.isdigit, messageText[tempIndex:tempIndex+4])))
			if " h=" in messageText:
				tempIndex = messageText.rindex(" h=") + len(" h=")
				height = int(''.join(filter(str.isdigit, messageText[tempIndex:tempIndex+4])))
			banner = not " no_banner" in messageText
			finalStatus  = "FINAL STATUS:\n"
			finalStatus += "- Theme:  " + ("Dark" if isDark else "Light") + "\n"
			finalStatus += "- Size:   " + str(width) + "x" + str(height) + "\n"
			finalStatus += "- Banner: " + ("Yes" if banner else "Not") + "\n"
			print(finalStatus)
			# do the thing
			statusId = int(parsedId)
			print("Getting tweet")
			status = twitterAPI.get_status(statusId, tweet_mode='extended')
			print(str(status))
			profileUrl = status.user.profile_image_url.replace("_normal", "")
			bannerUrl = status.user.profile_banner_url if not status.user.profile_use_background_image and banner else profileUrl
			title = API.deEmojify(status.user.name)
			user = "@" + status.user.screen_name
			content = html.unescape(API.deEmojify(status.full_text))
			profileImage = API.loadImage(requests.get(profileUrl, stream=True).raw if not status.user.default_profile_image else "twitter_default_profile.jpg")
			backgroundImage = API.loadImage(requests.get(bannerUrl, stream=True).raw if not status.user.default_profile_image else "twitter_default_profile.jpg")
			print("Converting tweet to image")
			resultImage = API.tweetToImage(backgroundImage, profileImage, width, height, title, user, content, isDark)
			print("Loading image into memory")
			# post the image from memory
			bytes_io = BytesIO()
			bytes_io.name = "tweet.jpeg"
			resultImage.save(bytes_io, "JPEG")
			bytes_io.seek(0)
			print("Sending reply")
			update.message.reply_photo(photo = bytes_io)
			print("Done!")


def main() -> None:
	"""Start the bot."""
	# Create the Updater with your bot's token.
	updater = Updater(TOKEN)

	# Get the dispatcher to register handlers
	dispatcher = updater.dispatcher

	# on different commands - answer in Telegram
	dispatcher.add_handler(CommandHandler("start", start))
	dispatcher.add_handler(CommandHandler("help", help_command))
	dispatcher.add_handler(CommandHandler("contribute", contribute_command))

	# on non command (i.e. message)
	dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, replyToText))

	# Start the Bot (use polling only if dev env)
	# updater.start_polling()
	PORT = int(os.environ.get("PORT", "8443"))
	updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url="https://post-to-image-telegram-bot.herokuapp.com/"+TOKEN)

	# Run the bot until you press Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT. This should be used most of the time, since
	# start_polling() and start_webhook are non-blocking and will stop
	# the bot gracefully.
	updater.idle()


if __name__ == '__main__':
	main()
