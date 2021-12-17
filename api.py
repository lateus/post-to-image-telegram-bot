# TODO:
# - Telegram bot
# - Add options like size, effect, banner, theme
# - With a photo, use as background

import tweepy, requests, html, re
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

def tweetToImage(background: Image.Image, profile: Image.Image, width: int, height: int, title: str, user: str, content: str, darkMode: bool = False):
	if width <= 0:
		width = background.size[0]
	if height <= 0:
		height = background.size[1]
	print("- Fitting background to " + str(width) + "x" + str(height))
	fittedImage = ImageOps.fit(background, (width, height))
	print("- Converting background to RGBA")
	rgbaBackgroundImage = fittedImage.convert('RGBA')
	print("- Blurring background with radius 5")
	blurredImage = blurRgbaImage(rgbaBackgroundImage, 5)
	print("- Loading social media logo")
	originalSocialImage  = loadImage('twitter.png')

	textColor = '#FFFFFF' if darkMode else '#000000'
	secondaryTextColor = '#FFFFFF' if darkMode else '#333333'
	print("- Loading fonts")
	titleFont = ImageFont.truetype('fonts/Quicksand/static/Quicksand-Medium.ttf', 36)
	userFont = ImageFont.truetype('fonts/Quicksand/static/Quicksand-Regular.ttf', 20)
	contentFont = ImageFont.truetype('fonts/Quicksand/static/Quicksand-Medium.ttf', 26)

	# in all cases, use supersampling, otherwise you'll get a pixelated result

	# the rectangle
	print("- Creating the rectangle")
	supersampleFactor = 3
	rectangleMargin = 40
	rectangleWidth = blurredImage.size[0] - 2*rectangleMargin
	rectangleX = int((blurredImage.size[0] - rectangleWidth)/2)
	# the height is calculated using dimensions that will be set later. keep an eye on this:
	rectangleHeight = ImageDraw.Draw(background).textsize(getWrappedText(content, contentFont, (rectangleX + rectangleWidth - 20) - (rectangleX + 20 + 80)), contentFont)[1] + 80 + 40
	rectangleY = int((blurredImage.size[1] - rectangleHeight)/2)
	rectangleSize = (rectangleWidth, rectangleHeight)
	rectangleBoundingBox = (rectangleX, rectangleY, rectangleX + rectangleWidth, rectangleY + rectangleHeight)
	rectangleRadius = 16
	rectangleColor = (0x00, 0x00, 0x00) if darkMode else (0xFF, 0xFF, 0xFF)
	rectangleOpacity = int(0.6 * 0xFF)
	overlayImage = Image.new('RGBA', (blurredImage.size[0]*supersampleFactor, blurredImage.size[1]*supersampleFactor), rectangleColor+(0,))
	drawOverlayImage = ImageDraw.Draw(overlayImage)
	drawOverlayImage.rounded_rectangle( (rectangleX*supersampleFactor, rectangleY*supersampleFactor, rectangleX*supersampleFactor + rectangleWidth*supersampleFactor, rectangleY*supersampleFactor + rectangleHeight*supersampleFactor), radius=rectangleRadius*supersampleFactor, fill=rectangleColor+(rectangleOpacity,) )
	overlayImage = overlayImage.resize(blurredImage.size, resample=Image.ANTIALIAS)
	resultImage = Image.alpha_composite(blurredImage, overlayImage)

	# the profile icon
	print("- Creating the profile icon")
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

	# the social icon
	print("- Creating the social media icon")
	socialIconSize = (42, 42)
	socialIconX = rectangleX + rectangleWidth - socialIconSize[0] - 20
	socialIconY = rectangleY + 20
	socialIconBoundingBox = (socialIconX, socialIconY, socialIconX + socialIconSize[0], socialIconY + socialIconSize[1])
	socialIconImage = originalSocialImage.resize(socialIconSize, resample=Image.ANTIALIAS)
	resultImage.paste(socialIconImage, socialIconBoundingBox, socialIconImage)

	# the title
	print("- Creating the title")
	titleDraw = ImageDraw.Draw(resultImage)
	titleDraw.text(xy=(profileIconX + profileIconSize[0] + 10, profileIconY + 2), text=title, font=titleFont, fill=textColor)

	# the username or link
	print("- Creating the username")
	userDraw = ImageDraw.Draw(resultImage)
	userDraw.text(xy=(profileIconX + profileIconSize[0] + 20, profileIconY + 42), text=user, font=userFont, fill=secondaryTextColor)

	# the text
	print("- Creating the content")
	availableWidth = (rectangleX + rectangleWidth) - (profileIconX + profileIconSize[0]) - 20
	multilineContent = getWrappedText(content, contentFont, availableWidth)
	contentDraw = ImageDraw.Draw(resultImage)
	contentDraw.text(xy=(profileIconX + profileIconSize[0], profileIconY + profileIconSize[1]), text=multilineContent, font=contentFont, fill=textColor)

	# wrapping up
	print("- Converting the final image back to RGB")
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

	resultImage = tweetToImage(backgroundImage, profileImage, 1280, 720, title, user, content)
	resultImage.save('result_light.jpg', quality=100)
	resultImage = tweetToImage(backgroundImage, profileImage, title, user, content, True)
	resultImage.save('result_dark.jpg', quality=100)

if __name__ == '__main__':
	main()