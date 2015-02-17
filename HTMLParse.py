from HTMLParser import HTMLParser

class MyHTMLParser(HTMLParser):

	def __init__(self):
		HTMLParser.__init__(self)
		self.anchors = []

	def handle_starttag(self, tag, attrs):
		if tag == "a":
			for attr in attrs:
				if attr[0] == "href":
					# print attr[1]
					self.anchors.append(str(attr[1]))
