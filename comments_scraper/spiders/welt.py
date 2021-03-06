# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from comments_scraper.items import CommentItem, ArticleItem
import time
import re
import datetime
import json
from ast import literal_eval

class WeltSpider(CrawlSpider):
    name = 'welt'
    allowed_domains = ['welt.de']
    start_urls = ['https://www.welt.de/']

    api_url = "https://api-co.la.welt.de/api/comments?document-id={}&sort=NEWEST"
    parent_url = "https://api-co.la.welt.de/api/comments?document-id={}&parent-id={}&created-cursor={}"
    api_url_more_comments= "https://api-co.la.welt.de/api/comments?document-id={}&created-cursor={}&sort=NEWEST"

    rules = [
        Rule(LinkExtractor(allow=['\/\w*\/\w*\/.*\/.*.html']),
        callback='parse_site',
        follow=True)
    ]

    def parse_site(self, response):
        article_id = self.extract_article_id(response.url)
        url = self.api_url.format(article_id)

        yield Request(url, self.parse_comments, method="GET", priority=1)

        yield self.get_article(response, article_id)

    def parse_comments(self, response):
        #data = json.loads(response.body)
        # Decode UTF-8 bytes to Unicode, and convert single quotes
        print ("parsing comments... on url {}".format(response.url))
        formatted_json = response.body.decode()
        my_json = json.loads(formatted_json)
        comments = my_json['comments']

        for comment in my_json['comments']:
            if comment['childCount'] > 1:
                url = self.parent_url.format(comment['documentId'], comment['id'], comment['created'])
                yield Request(url, self.parse_anwers, method="GET", priority=100)
            yield comment

        if len(comments) >= 10:
            offset = 1
            last_comment = comments[len(comments) - offset]
            while True:
                ''' point the array cursor on the last item without parent
                to make next request on api'''
                try:
                    offset += 1
                    if last_comment['parentId']:
                        last_comment = comments[len(comments) - offset]
                except:
                    break

            url = self.api_url_more_comments.format(last_comment['documentId'], last_comment['created'])
            yield Request(url, self.parse_comments, method="GET", priority=10)

    def parse_anwers(self, response):
        #data = json.loads(response.body)
        # Decode UTF-8 bytes to Unicode, and convert single quotes
        print ("parsing answers... on url {}".format(response.url))

        formatted_json = response.body.decode()
        my_json = json.loads(formatted_json)
        comments = my_json['comments']

        #skip first because its already scraped
        for comment in comments[1:]:
            yield comment

    def get_article(self, response, id):
        time_scraped = time.time()

        article = ArticleItem()
        article['url'] = response.url
        article['date'] = response.xpath("//time[@class='c-publish-date']/@datetime").extract_first()
        article['scraped_time_stamp'] = datetime.datetime.fromtimestamp(time_scraped).strftime('%d.%m.%Y %H:%M')
        article['category'] = self.extract_category_from_url(response.url)
        article['id'] = id
        return article

    def extract_article_id(self, url):
        article = re.search('article(\d+)', url).group(1)
        return re.search('(\d+)', article).group(1)

    def extract_category_from_url(self, url):
        return url.split('/')[3]
