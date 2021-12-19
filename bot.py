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
			'''Send a tweet\'s link to convert it to an image\.'''
		)


def help_command(update: Update, context: CallbackContext) -> None:
	"""Send a message when the command /help is issued."""
	update.message.reply_markdown_v2(
		'''*Help \- Tweet to Image Bot*\n\n'''
		'''_How to use?_\n'''
		'''Send a tweet\'s link\.\n'''
		'''\n__Customization__\n'''
		'''Include some additional options \(separated by spaces\) in the message:\n'''
		'''`w=#` \- Set the width \(example: `w=800` for 800 pixels\)\n'''
		'''`h=#` \- Set the heigth\n'''
		'''`blur=#` \- Set the blur level \(default is 5\)\n'''
		'''`blur_media` \- Blur the edges of the media \(if any\)\n'''
		'''`no_banner` \- Use the profile picture instead of the banner for the background'''
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
			blurRadius = 5
			if " w=" in messageText:
				tempIndex = messageText.rindex(" w=") + len(" w=")
				width = int(''.join(filter(str.isdigit, messageText[tempIndex:tempIndex+4]))) # 0-9999
			if " h=" in messageText:
				tempIndex = messageText.rindex(" h=") + len(" h=")
				height = int(''.join(filter(str.isdigit, messageText[tempIndex:tempIndex+4]))) # 0-9999
			if " blur=" in messageText:
				tempIndex = messageText.rindex(" blur=") + len(" blur=")
				blurRadius = int(''.join(filter(str.isdigit, messageText[tempIndex:tempIndex+2]))) # 0-99
			banner = not " no_banner" in messageText
			blurInMedia = " blur_media" in messageText
			# do the thing
			statusId = int(parsedId)
			status = twitterAPI.get_status(statusId, tweet_mode='extended')
			profileUrl = status.user.profile_image_url.replace("_normal", "")
			bannerUrl = status.user.profile_banner_url if hasattr(status.user, "profile_banner_url") and banner else profileUrl
			title = API.deEmojify(status.user.name)
			user = "@" + status.user.screen_name
			content = html.unescape(API.deEmojify(status.full_text))
			profileImage = API.loadImage(requests.get(profileUrl, stream=True).raw if not status.user.default_profile_image else "twitter_default_profile.jpg")
			backgroundImage = API.loadImage(requests.get(bannerUrl, stream=True).raw if not status.user.default_profile_image else "twitter_default_profile.jpg")
			creationDate = status.created_at
			additionalFooter = "t.me/TweetToImage_bot"
			searchMediaIn = status.entities
			mediaImages = []
			if not "media" in searchMediaIn and hasattr(status, "retweeted_status"):
				searchMediaIn = status.retweeted_status.entities
			if "media" in searchMediaIn:
				for media in searchMediaIn["media"]:
					mediaUrl = media["media_url"]
					print("- Found media: " + str(mediaUrl))
					mediaImages.append(API.loadImage(requests.get(mediaUrl, stream=True).raw))
			resultImage = API.tweetToImage(backgroundImage, profileImage, width, height, blurRadius, title, user, content, "{:%b %d, %Y}".format(creationDate), additionalFooter, mediaImages, blurInMedia, isDark)
			# post the image from memory
			bytes_io = BytesIO()
			bytes_io.name = "tweet.jpeg"
			resultImage.save(bytes_io, "JPEG")
			bytes_io.seek(0)
			caption  = "*- Size:* " + str(width) + "x" + str(height) + "\n"
			caption += "*- Theme:* " + ("Dark" if isDark else "Light") + "\n"
			caption += "*- Custom background:* " + ("Yes" if banner else "No") + "\n"
			caption += "*- Custom footer:* " + ("Yes" if additionalFooter else "No") + "\n"
			caption += "*- Blur radius:* " + str(blurRadius) + "\n"
			caption += "*- Blur in media:* " + ("Yes" if blurInMedia else "No") + "\n\n"
			caption += "_Type /help for customization options._"
			caption = caption.replace('.', '\.').replace('#', '\#').replace('~', '\~').replace('>', '\>').replace('-', '\-').replace('+', '\+').replace('=', '\=').replace('[', '\[').replace(']', '\]').replace('{', '\{').replace('}', '\}').replace('(', '\(').replace(')', '\)').replace('!', '\!').replace('?', '\?').replace('|', '\|')
			update.message.reply_photo(photo = bytes_io, caption=caption, parse_mode = ParseMode.MARKDOWN_V2)
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
