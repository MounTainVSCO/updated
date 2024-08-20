import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import deque
from channels.generic.websocket import AsyncWebsocketConsumer

class LinkConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        url = data['website']
        print(url)

        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0"
        headers = {"user-agent": user_agent}
        base_url = url
        base_domain = self.custom_url_parse(url)['netloc']
        visited = set()
        queue = deque([url])

        while queue:
            current_url = queue.popleft()

            if current_url in visited:
                continue
            visited.add(current_url)
            print(current_url)
            try:
                response = requests.get(current_url, headers=headers)
                soup = BeautifulSoup(response.content, 'lxml')

                links = [link['href'] for link in soup.find_all('a', href=True)]
                normalized_links = self.normalize(base_url, links)
                for link in normalized_links:
                    parsed_link = self.custom_url_parse(link)
                    if parsed_link['netloc'] == base_domain or parsed_link['netloc'] == '':
                        if link not in visited and link not in queue and '#' not in link and 'redirect' not in link and not link.endswith(('jpg', 'exe', 'docx')):
                            queue.append(link)
                            await self.send(json.dumps([link]))
            except requests.exceptions.RequestException as e:
                await self.send(json.dumps([f"Error fetching {current_url}: {e}"]))

    def custom_url_parse(self, url):
        if '://' in url:
            scheme, rest = url.split('://', 1)
        else:
            scheme, rest = '', url

        if '/' in rest:
            netloc, path = rest.split('/', 1)
            path = '/' + path
        else:
            netloc, path = rest, ''

        if '?' in path:
            path, query = path.split('?', 1)
        else:
            query = ''

        if '#' in path:
            path, fragment = path.split('#', 1)
        else:
            fragment = ''

        if netloc.startswith('www.'):
            netloc = netloc[4:]

        return {
            'scheme': scheme,
            'netloc': netloc,
            'path': path,
            'query': query,
            'fragment': fragment
        }

    def normalize(self, base_url, links):
        normalized_links = []
        for link in links:
            if not self.custom_url_parse(link)['netloc']:
                link = urljoin(base_url, link)
            link = link.rstrip('/')
            normalized_links.append(link)
        return normalized_links
