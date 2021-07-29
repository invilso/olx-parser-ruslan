import requests
from requests.models import parse_url
from bs4 import BeautifulSoup
import json
import pandas as pd
import config
import time

class Parser():
    max_page = 1
    current_page = 1
    filters = []
    filtered_posts = []

    def getPostTitle(self, post):
        soup = BeautifulSoup(post, 'lxml')
        try:
            return soup.find_all("h1", {'data-cy': 'ad_title'})[0].text
        except IndexError:
            return 'Error'

    def getPostPrice(self, post):
        soup = BeautifulSoup(post, 'lxml')
        price_container = soup.find_all("div", {'data-testid': 'ad-price-container'})[0]
        return price_container.find_all("h3")[0].text

    def getPostDescription(self, post):
        soup = BeautifulSoup(post, 'lxml')
        decription_container = soup.find_all("div", {'data-cy': 'ad_description'})[0]
        return decription_container.find_all("div")[0].text

    def getAllPosts(self, page):
        soup = BeautifulSoup(page, 'lxml')
        posts = soup.find_all("a", {'data-cy': 'listing-ad-title'})
        posts_data = []
        for post in posts:
            resp = requests.get(post['href'])
            post_html = resp.text
            if resp.status_code in (200, 201, 202, 203, 204, 205):
                posts_data.append(
                    {
                        'link': post['href'],
                        'title': self.getPostTitle(post_html),
                        'description': self.getPostDescription(post_html),
                        'price': self.getPostPrice(post_html)
                    }
                )
                print('Post '+self.getPostTitle(post_html)+' parsed.')
            else:
                print('Error connection: '+str(resp.status_code))
            time.sleep(1.5)
        return posts_data

    def getMaxPage(self, page):
        soup = BeautifulSoup(page, 'lxml')
        last_page = soup.find_all("a", {'data-cy': 'page-link-last'})[0]
        return last_page.find_all("span")[0].text

    def getPages(self, category):
        pages = []
        while int(self.max_page) >= int(self.current_page):
            resp = requests.get('https://www.olx.ua/'+str(category)+'/?page='+str(self.current_page))
            page = resp.text
            pages.append(self.getAllPosts(page))
            if int(self.current_page) != int(self.max_page) or int(self.max_page) == 1:
                self.max_page = self.getMaxPage(page)
            print('End parsed page: '+str(self.current_page))
            self.current_page = self.current_page + 1
        return pages

    def prepareToNextCategoty(self):
        self.current_page = 1
        self.max_page = 1

    def filterData(self, category):
        filtered = []
        for post in category[0]:
            last_added = ''
            for filter in self.filters:
                check_and = 0
                for word in filter['words']:
                    if word in post['title'].lower() or word in post['description'].lower():
                        check_and = check_and + 1
                if check_and == len(filter["words"]) and last_added != post['title']:
                    last_added = post['title']
                    filtered.append(post)
        return filtered
                        
    def getCategoryes(self, categoryes):
        for category in categoryes:
            for post in self.filterData(self.getPages(category)):
                self.filtered_posts.append(post)
            self.prepareToNextCategoty()
        

class Writer():
    def serializeToWrite(self):
        titles = []
        for post in Parser().filtered_posts:
            titles.append(post['title'])
        links = []
        for post in Parser().filtered_posts:
            links.append(post['link'])
        prices = []
        for post in Parser().filtered_posts:
            prices.append(post['price'])
        return {'TITLE': titles, 'LINKS': links, 'PRICE': prices}

    def write(self):
        dataframe = pd.DataFrame(self.serializeToWrite())
        dataframe.to_excel('./items.xlsx')


class Notifier():
    def write(self):
        with open('posts.json', 'w+') as f:
            f.write(json.dumps(Parser.filtered_posts))

    def read(self):
        with open('posts.json', 'r') as f:
            return json.loads(f.read())

    def prepareToSend(self, post):
        text = f"""
            Новое обьявление на OLX!
            TITLE: {post['title']}
            PRICE: {post['price']}
            DECRIPTION: {post['description']}
            LINK: {post['link']}
        """
        self.send(text)

    def send(self, text):
        data = {'chat_id':config.USER_ID, 'text': text}
        requests.post('https://api.telegram.org/bot'+config.TOKEN+'/sendMessage', data=data)

    def check(self):
        links_old = []
        for post in self.read():
            links_old.append(post['link'])
        for post in Parser().filtered_posts:
            if not post['link'] in links_old:
                self.prepareToSend(post)


class Init():
    def readCategoryes(self):
        with open('categoryes.txt') as f:
            categoryes = []
            for category in f.read().split('\n'):
                category = category.strip(' \t\n\r')
                categoryes.append(category)
        return categoryes


    def readFilters(self):
        with open('filter.txt', encoding='utf-8') as f:
            Parser().filters = []
            for line in f.read().split('\n'):
                line = line.strip(' \t\n\r')
                words = []
                for word in line.split(','):
                    word = word.strip(' \t\n\r')
                    word = word.lower()
                    words.append(word)
                Parser().filters.append({'words': words})
            
    def start(self):
        p = Parser()
        notf = Notifier()
        wr = Writer()

        self.readFilters()
        self.readCategoryes()
        p.getCategoryes(self.readCategoryes())

        wr.write()

        notf.check()
        notf.write()


init = Init()
while True:
    try:
        init.start()
        time.sleep(600)
    except Exception as err:
        print(err)
    