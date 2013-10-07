#!/usr/bin/python
# -*- coding: utf-8 -*-

import csv
import sys
import datetime
import re
import argparse
import os
import glob

import plistlib
import tempfile

import math

import feedparser

import urllib2
import httplib2

from collections import defaultdict
from datetime import datetime

def imagesForPodcastEpisodes():
	rss_url = "http://www.insideactingpodcast.com/feeds/posts/default?alt=rss&max-results=500"
	feed = feedparser.parse(rss_url)

	items = feed["items"]

	url_re = re.compile(r'(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))')
	episode_num_re = re.compile(r'([0-9]{3})')

	podcasts_dict = defaultdict(str)

	def findImageURLInText(text):
		results = url_re.findall(text)
		if results:
			for result_group in results:
				for url in result_group:
					if "jpg" in url:
						return url
		return ""

	def findMediaURLInText(text):
		results = url_re.findall(text)
		if results:
			for result_group in results:
				for url in result_group:
					if "mp3" in url:
						return url
		return ""

	for item in items:
		episode_num = ""
		results = episode_num_re.search(item["title"])
		if results:
			groups = results.groups()
			episode_num = groups[0]

		if episode_num:
			thumbnailUrl = findImageURLInText(item["summary"])
			mediaUrl = findMediaURLInText(item["summary"])
			if not mediaUrl:
				print episode_num + ": has no mediaUrl; " + item["title"] + item["summary"]
					
			podcast = {"thumbnailUrl":thumbnailUrl,"mediaUrl":mediaUrl,"link":item["link"]}
			podcasts_dict[episode_num] = podcast

	return podcasts_dict
	
imagesForPodcastEpisodes()
