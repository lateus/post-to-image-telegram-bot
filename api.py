# TODO:
# - Telegram bot
# - Add options like size, effect, banner, theme
# - With a photo, use as background

import tweepy, requests, html, re, datetime
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont

def setupTwitterAccess(consumer_key: str, consumer_secret: str, access_token: str, access_token_secret: str):
	auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
	auth.set_access_token(access_token, access_token_secret)
	return tweepy.API(auth)

def loadImage(filename: str):
	return Image.open(filename, 'r')

def resizeImage(image: Image.Image, size): # tuple
	return image.resize(size, resample=Image.ANTIALIAS)

def blurRgbaImage(rgbaImage: Image.Image, radius: int):
	return rgbaImage.filter(ImageFilter.GaussianBlur(radius))

def getWrappedText(text: str, font: ImageFont.ImageFont, width: int):
	lines = ['']
	for word in text.split():
		line = f'{lines[-1]} {word}'.strip()
		if font.getlength(line) <= width:
			lines[-1] = line
		else:
			lines.append(word)
	return '\n'.join(lines)

def hasTransparency(img):
    if img.mode == "P":
        transparent = img.info.get("transparency", -1)
        for _, index in img.getcolors():
            if index == transparent:
                return True
    elif img.mode == "RGBA":
        extrema = img.getextrema()
        if extrema[3][0] < 255:
            return True

    return False


def deEmojify(text):
    regrex_pattern = re.compile(pattern = "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U00010000-\U0010ffff"
        u"\ufe0f" # dingbats
                           "]+", flags = re.UNICODE)
    return regrex_pattern.sub(r'',text)

def tweetToImage(background: Image.Image, profile: Image.Image, width: int, height: int, blurRadius: int, title: str, user: str, content: str, creationDate: str, additionalFooter: str = "", mediaImages: [] = [], blurMedia: bool = False, darkMode: bool = False):
	if width <= 0:
		width = background.size[0]
	if height <= 0:
		height = background.size[1]
	if blurRadius <= 0:
		blurRadius = 5
	print("- Fitting background to " + str(width) + "x" + str(height))
	fittedImage = ImageOps.fit(background, (width, height)) if width != background.size[0] or height != background.size[1] else background
	print("- Converting background to RGBA")
	rgbaBackgroundImage = fittedImage.convert('RGBA')
	print("- Blurring background with radius " + str(blurRadius))
	blurredImage = blurRgbaImage(rgbaBackgroundImage, blurRadius)
	print("- Loading media")
	mediaImage1 = None if not mediaImages else mediaImages[0]
	mediaImage2 = None if len(mediaImages) <= 1 else mediaImages[1]
	print("- Loading social media logo")
	originalSocialImage = loadImage('twitter.png')

	textColor = "#FFFFFF" if darkMode else "#000000"
	secondaryTextColor = "#FFFFFF" if darkMode else "#333333"
	footerTextColor = "#777777" if darkMode else "#555555"
	print("- Loading fonts")
	titleFont = ImageFont.truetype('fonts/Quicksand/Quicksand-Medium.ttf', 36)
	userFont = ImageFont.truetype('fonts/Quicksand/Quicksand-Regular.ttf', 20)
	contentFont = ImageFont.truetype('fonts/Quicksand/Quicksand-Medium.ttf', 26)
	dateFont = ImageFont.truetype('fonts/Quicksand/Quicksand-Regular.ttf', 14)
	footerFont = ImageFont.truetype('fonts/SourceCodePro/SourceCodePro-Regular.ttf', 14)

	# in all cases, use supersampling, otherwise you'll get a pixelated result

	# the rectangle
	# print("- Creating the rectangle")
	supersampleFactor = 3
	rectangleMargin = 40
	rectangleWidth = blurredImage.size[0] - 2*rectangleMargin
	rectangleX = (blurredImage.size[0] - rectangleWidth)//2
	# the height is calculated using dimensions that will be set later. keep an eye on this:
	contentHeight = ImageDraw.Draw(background).textsize(getWrappedText(content, contentFont, (rectangleX + rectangleWidth - 20) - (rectangleX + 20 + 80)), contentFont)[1]
	rectangleHeight = contentHeight + 80 + rectangleMargin # 80 is due to the profile icon
	if mediaImage1:
		maxMediaWidth  = rectangleWidth - rectangleMargin
		maxMediaHeight = height - rectangleHeight - 2*rectangleMargin
		if maxMediaWidth <= 0 or maxMediaHeight <= 0:
			mediaImage1 = None
		elif maxMediaWidth < mediaImage1.size[0] or maxMediaHeight < mediaImage1.size[1]:
			mediaImage1 = ImageOps.fit(mediaImage1, (maxMediaWidth if maxMediaWidth < mediaImage1.size[0] else mediaImage1.size[0], maxMediaHeight if maxMediaHeight < mediaImage1.size[1] else mediaImage1.size[1]))
		# if mediaImage2 and (maxMediaWidth < mediaImage2.size[0] or maxMediaHeight < mediaImage2.size[1]):
			# mediaImage2 = ImageOps.fit(mediaImage2, (maxMediaWidth if maxMediaWidth < mediaImage2.size[0] else mediaImage2.width, maxMediaHeight if maxMediaHeight < mediaImage2.size[1] else mediaImage2.size[1]))
		if mediaImage1:
			rectangleHeight += mediaImage1.size[1] + rectangleMargin//2 # max(mediaImage1.size[1], mediaImage2.size[1])
	rectangleY = (blurredImage.size[1] - rectangleHeight)//2
	rectangleSize = (rectangleWidth, rectangleHeight)
	rectangleBoundingBox = (rectangleX, rectangleY, rectangleX + rectangleWidth, rectangleY + rectangleHeight)
	rectangleRadius = 16
	rectangleColor = (0x00, 0x00, 0x00) if darkMode else (0xFF, 0xFF, 0xFF)
	rectangleOpacity = int(0.6 * 0xFF)
	overlayImage = Image.new('RGBA', (blurredImage.size[0]*supersampleFactor, blurredImage.size[1]*supersampleFactor), rectangleColor+(0,))
	drawOverlayImage = ImageDraw.Draw(overlayImage)
	drawOverlayImage.rounded_rectangle( (rectangleX*supersampleFactor, rectangleY*supersampleFactor, (rectangleX + rectangleWidth)*supersampleFactor, (rectangleY + rectangleHeight)*supersampleFactor), radius=rectangleRadius*supersampleFactor, fill=rectangleColor+(rectangleOpacity,) )
	overlayImage = overlayImage.resize(blurredImage.size, resample=Image.ANTIALIAS)
	resultImage = Image.alpha_composite(blurredImage, overlayImage)

	# the profile icon
	# print("- Creating the profile icon")
	profileIconSize = (80, 80)
	profileIconX = rectangleX + 20
	profileIconY = rectangleY + 20
	profileIconBoundingBox = (profileIconX, profileIconY, profileIconX + profileIconSize[0], profileIconY + profileIconSize[1])
	profileIconImage = profile.resize(profileIconSize, resample=Image.ANTIALIAS)
	maskImage = Image.new('L', profile.size)
	maskDraw = ImageDraw.Draw(maskImage)
	maskDraw.ellipse((0, 0) + profile.size, fill='white')
	maskImage = maskImage.resize(profileIconSize, resample=Image.ANTIALIAS)
	resultImage.paste(profileIconImage, profileIconBoundingBox, maskImage)

	# the media (if any)
	if mediaImage1:
		isTransparent = hasTransparency(mediaImage1)
		if not isTransparent:
			maskImage = Image.new("L", mediaImage1.size if blurMedia else (mediaImage1.size[0]*supersampleFactor, mediaImage1.size[1]*supersampleFactor), 0)
			maskDraw = ImageDraw.Draw(maskImage)
			if blurMedia:
				maskDraw.rectangle((20, 20, maskImage.size[0] - 20, maskImage.size[1] - 20), fill='white')
				maskImage = maskImage.filter(ImageFilter.GaussianBlur(10))
			else:
				maskDraw.rounded_rectangle(((0, 0), maskImage.size), radius=rectangleRadius*supersampleFactor, fill='white')
				maskImage = maskImage.resize(mediaImage1.size, resample=Image.ANTIALIAS)
		mediaImage1X = rectangleX + (rectangleWidth - mediaImage1.size[0])//2
		mediaImage1Y = profileIconY + profileIconSize[1] + contentHeight + rectangleMargin//2
		mediaImage1BoundingBox = (mediaImage1X, mediaImage1Y, mediaImage1X + mediaImage1.size[0], mediaImage1Y + mediaImage1.size[1])
		resultImage.paste(mediaImage1, mediaImage1BoundingBox, mediaImage1 if isTransparent else maskImage)

	# the social icon
	# print("- Creating the social media icon")
	socialIconSize = (42, 42)
	socialIconX = rectangleX + rectangleWidth - socialIconSize[0] - 20
	socialIconY = rectangleY + 20
	socialIconBoundingBox = (socialIconX, socialIconY, socialIconX + socialIconSize[0], socialIconY + socialIconSize[1])
	socialIconImage = originalSocialImage.resize(socialIconSize, resample=Image.ANTIALIAS)
	resultImage.paste(socialIconImage, socialIconBoundingBox, socialIconImage)

	# the title
	# print("- Creating the title")
	titleDraw = ImageDraw.Draw(resultImage)
	titleDraw.text(xy=(profileIconX + profileIconSize[0] + 10, profileIconY + 2), text=title, font=titleFont, fill=textColor)

	# the username or link
	# print("- Creating the username")
	userDraw = ImageDraw.Draw(resultImage)
	userDraw.text(xy=(profileIconX + profileIconSize[0] + 20, profileIconY + 42), text=user, font=userFont, fill=secondaryTextColor)

	# the text
	# print("- Creating the content")
	availableWidth = (rectangleX + rectangleWidth) - (profileIconX + profileIconSize[0]) - 20
	multilineContent = getWrappedText(content, contentFont, availableWidth)
	contentDraw = ImageDraw.Draw(resultImage)
	contentDraw.text(xy=(profileIconX + profileIconSize[0], profileIconY + profileIconSize[1]), text=multilineContent, font=contentFont, fill=textColor)

	# the date
	# print("- Creating the date")
	dateDraw = ImageDraw.Draw(resultImage)
	dateDraw.text(xy=(profileIconX, rectangleY + rectangleHeight - rectangleMargin//2), text=creationDate, font=dateFont, fill=footerTextColor)

	# the footer
	# print("- Creating the footer")
	footerDraw = ImageDraw.Draw(resultImage)
	footerDraw.text(xy=(rectangleX + rectangleWidth - footerFont.getlength(additionalFooter) - rectangleMargin//2, rectangleY + rectangleHeight - rectangleMargin//2), text=additionalFooter, font=footerFont, fill=footerTextColor)

	# wrapping up
	# print("- Converting the final image back to RGB")
	resultImage = resultImage.convert('RGB')
	return resultImage


def main():
	api = setupTwitterAccess("QTisT5HlQgV5gJGJbWCOu7MLd", "2CKN9B0nzCKNzl2HXXRd0JkcasLnnJjcLrvmezDalw3lsTrpbX", "1073450779934105604-5cpRtgHDB85bhKThhXuZzJdAf2cxlz", "LMB4ttBqpjOVJI6ZPiFCdn2BPMV1jQbYO4mCqIGmRBwhP")
	statusId = 1470804241740619781 # mika, with image # 1302816890323185666 me #1470703708677840896 elon #1470682568257413128 axie
	status = api.get_status(statusId, tweet_mode='extended')
	profileUrl = status.user.profile_image_url.replace("_normal", "")
	bannerUrl = status.user.profile_banner_url
	title = deEmojify(status.user.name)#'Yo uso mi nasobuco'
	user = "@" + status.user.screen_name#'@YoUsoMiNasobuco'
	content = html.unescape(deEmojify(status.full_text))#"Para comprar algo en Cuba no solamente hay que tener el dinero sino que hay que tener el dinero exacto porque no hay menudo pa' vuelto."
	profileImage = loadImage(requests.get(profileUrl, stream=True).raw)
	backgroundImage = loadImage(requests.get(bannerUrl, stream=True).raw)
	creationDate = status.created_at
	additionalFooter = "t.me/TweetToImage_bot"
	print("Getting media")
	mediaImages = []
	for media in status.entities["media"]:
		mediaUrl = media["media_url"]
		print("- Found media: " + str(mediaUrl))
		mediaImages.append(loadImage(requests.get(mediaUrl, stream=True).raw))
	resultImage = tweetToImage(backgroundImage, profileImage, 800, 800, 5, title, user, content, "{:%b %d, %Y}".format(creationDate), additionalFooter, mediaImages)
	resultImage.save('result_light.jpg', quality=100)
	resultImage = tweetToImage(backgroundImage, profileImage, 800, 800, 5, title, user, content, "{:%b %d, %Y}".format(creationDate), additionalFooter, mediaImages, False, True)
	resultImage.save('result_dark.jpg', quality=100)

if __name__ == '__main__':
	main()