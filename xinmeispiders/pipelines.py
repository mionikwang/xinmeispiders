#!/usr/bin/python
# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import pymongo
import re

from scrapy.exceptions import DropItem
from scrapy import log
from db import db
import json
from bson import json_util
from bson.json_util import dumps


# 给item添加字段
class ScorePipeline(object):
	def process_item(self, item, spider):
		# 打分
		score = 0
		title = item['title']
		brief = item['brief']
		kw = item['kw']
		searchword = json.loads(dumps(db['searchwords'].find_one({"kw": kw})), object_hook=json_util.object_hook)
		item['kwid'] = searchword['_id']
        # 通过main, keyword来打分
		main = re.compile(searchword['main'])
		keyword = re.compile(searchword['keyword'])
		word = re.compile(searchword['word'])
		mt = 3 if main.search(title) else 0
		kt = 2 if keyword.search(title) else 0
		wt = 1 if word.search(title) else 0

		mb = 3 if main.search(brief) else 0
		kb = 2 if keyword.search(brief) else 0
		wb = 1 if word.search(brief) else 0

		score = mt + kt + wt + mb + kb + wb
        # mb = main.search(brief) ? 2: 0

        # if main.search(title) && main.search(brief):
        # 	score = 4
        # elif main.search(title) && not main.search(brief):
        # 	score = 3
        # elif not main.search(title) && main.search(brief):
        # 	score = 2
        # elif not main.search(title) && not main.search(brief):
        # 	score = 0
        
		item['score'] = score
		return item

class MongoDBPipeline(object):

	def __init__(self, mongo_uri, mongo_db):
		self.mongo_uri = mongo_uri
		self.mongo_db = mongo_db

	@classmethod
	def from_crawler(cls, crawler):
		return cls(
			mongo_uri = crawler.settings.get('MONGO_URI'),
			mongo_db = crawler.settings.get('MONGO_DATABASE', 'items')
		)

	def open_spider(self, spider):
		self.client = pymongo.MongoClient(self.mongo_uri)
		self.db = self.client[self.mongo_db]

	def close_spider(self, spider):
		log.msg("Change search words status!", level=log.DEBUG, spider=spider)

		self.client.close()

	def process_item(self, item, spider):
		# for data in item:
		# 	if not data:
		# 		raise DropItem("Missing data!")
		collection_name = item.__class__.__name__
		self.db[collection_name].update({'url': item['url']}, dict(item), upsert=True)
		log.msg("Added to MongoDB database!", level=log.DEBUG, spider=spider)

		return item