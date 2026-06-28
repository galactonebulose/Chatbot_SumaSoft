import httpx
from html.parser import HTMLParser

class GoogleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_g = False
        self.depth = 0
        self.current_text = []
        self.results = []
        self.in_title = False
        self.in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # In desktop user agent, each result is typically in a div with class containing 'g' or 'tW38zb' or similar
        # Let's inspect class attributes
        cls = attrs_dict.get("class", "")
        
        # Let's track when we are inside result titles or snippets
        # Usually titles are in h3 tags
        if tag == "h3":
            self.in_title = True
            self.current_text = []
            
        # Snippets are usually in divs with class containing 'VwiC3b' or similar
        elif tag == "div" and ("VwiC3b" in cls or "yDnd3b" in cls or "BNeawe" in cls):
            self.in_snippet = True
            self.current_text = []

    def handle_data(self, data):
        if self.in_title or self.in_snippet:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "h3" and self.in_title:
            self.in_title = False
            title = "".join(self.current_text).strip()
            if title:
                self.results.append({"type": "title", "text": title})
        elif tag == "div" and self.in_snippet:
            self.in_snippet = False
            snippet = "".join(self.current_text).strip()
            if snippet:
                self.results.append({"type": "snippet", "text": snippet})

url = "https://www.google.com/search?q=mumbai+weather+today"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
r = httpx.get(url, headers=headers)
parser = GoogleParser()
parser.feed(r.text)
for r in parser.results[:15]:
    print(r)
