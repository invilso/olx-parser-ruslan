import requests

class Parser():
    max_page = 1
    current_page = 1
    def pages_loop(self):
        while self.max_page >= self.current_page:
            requests.get('https://www.olx.ua/elektronika/?page=2')

class Writer():
