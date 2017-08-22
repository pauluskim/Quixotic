#-*- coding: utf-8 -*-
from __future__ import division
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import argparse
import codecs
from collections import defaultdict
import json
import os
import re
import sys
import time
try:
    from urlparse import urljoin
    from urllib import urlretrieve
except ImportError:
    from urllib.parse import urljoin
    from urllib.request import urlretrieve

import requests
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import pdb
from preprocess import * 
from langdetect import *
from css_xpath import *
import requests


class url_change(object):
    """
        Used for caption scraping
    """
    def __init__(self, prev_url):
        self.prev_url = prev_url

    def __call__(self, driver):
        return self.prev_url != driver.current_url
class ProfileCrawler(object):
    """
        Crawler class
    """
    def __init__(self):
        self._driver = webdriver.Firefox()
        self.data = defaultdict(list)

    def login(self, authentication=None):
        """
            authentication: path to authentication json file
        """
        self._driver.get(urljoin(HOST, "accounts/login/"))

        if authentication:
            print("Username and password loaded from {}".format(authentication))
            with open(authentication, 'r') as fin:
                auth_dict = json.loads(fin.read())
            # Input username
            username_input = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located((By.NAME, 'username'))
            )
            username_input.send_keys(auth_dict['username'])
            # Input password
            password_input = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located((By.NAME, 'password'))
            )
            password_input.send_keys(auth_dict['password']) # Submit
            password_input.submit()
        else:
            print("Type your username and password by hand to login!")
            print("You have a minute to do so!")

        print("")
        WebDriverWait(self._driver, 60).until( EC.presence_of_element_located((By.CSS_SELECTOR, CSS_EXPLORE))
        )



    def quit(self):
        self._driver.quit()
    def crawl(self, dir_prefix, query, crawl_type, number, caption, authentication):

        if crawl_type in ["followers", "following"]:
            # Need to login first before crawling followers/following
            print("You will need to login to crawl {}".format(crawl_type))
            self.login(authentication)

            # Then browse target page
            assert not query.startswith(
                '#'), "Hashtag does not have followers/following!"
            self.browse_target_page(query)
            # Scrape captions
            self.scrape_followers_or_following(crawl_type, query, number)
        else:
            print("Unknown crawl type: {}".format(crawl_type))
            self.quit()
            return
        # Save to directory
        print("Saving...")

	self.download_and_save(dir_prefix, query, crawl_type)

        # Quit driver
        print("Quitting driver...")
        self.quit()

    def browse_target_page(self, query):
        # Browse Hashtags
        if query.startswith('#'):
            relative_url = urljoin('explore/tags/', query.strip('#'))
        else:  # Browse user page
            relative_url = query

        target_url = urljoin(HOST, relative_url)

        self._driver.get(target_url)

    def korean_detection(self):
        try:
            time_element = WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "time"))
            )
            caption = time_element.find_element_by_xpath(
                TIME_TO_CAPTION_PATH).text
        except NoSuchElementException:  # Forbidden
            print("Caption not found in the {} photo".format(post_num))
            caption = "No caption"

        try:
            if detect(caption) == 'ko':
                return True
            else:
                return False
        except:
            return False

    def scrape_followers_or_following(self, crawl_type, query, number):
        print("Scraping {}...".format(crawl_type))
        if crawl_type == "followers":
            FOLLOW_ELE = CSS_FOLLOWERS
            FOLLOW_PATH = FOLLOWER_PATH
        elif crawl_type == "following":
            FOLLOW_ELE = CSS_FOLLOWING
            FOLLOW_PATH = FOLLOWING_PATH

        # Locate follow list
        follow_ele = WebDriverWait(self._driver, 5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, FOLLOW_ELE.format(query)))
        )

        follow_num = self.refine_number_letters(follow_ele.text.split()[-1])
        number = follow_num
        follow_ele.click()

        title_ele = WebDriverWait(self._driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, FOLLOW_PATH))
        )
        List = title_ele.find_element_by_xpath(
            '..').find_element_by_tag_name('ul')
        List.click()

        num_of_shown_follow = len(List.find_elements_by_xpath('*'))

        
        prev_count = 0 
        trycounter = 100
        while len(List.find_elements_by_xpath('*')) < number:
            sys.stdout.write("\033[F")
            print(" {} / {} scrapped. try counter {} / 100 left".format(prev_count, number, trycounter))
            element = List.find_elements_by_xpath('*')[-1]
            # Work around for now => should use selenium's Expected Conditions!
            r = requests.get('https://www.instagram.com/graphql/query/?query_id=17851374694183129&variables={"id":"1252702687","first":20}')
            if int(r.status_code) == 429: time.sleep(300)
            try:
                element.send_keys(Keys.PAGE_DOWN)
                if prev_count == len(List.find_elements_by_xpath('*')):
                    trycounter -=1
                    time.sleep(0.5)
                    if trycounter <= 0: 
                        break
                else:
                    prev_count = len(List.find_elements_by_xpath('*'))
                    trycounter =100 
            except Exception as e:
                time.sleep(0.1)

        follow_items = []
        for ele in List.find_elements_by_xpath('*')[:number]:
            follow_items.append(ele.text.split('\n')[0])

        self.data[crawl_type] = follow_items

    def download_and_save(self, dir_prefix, query, crawl_type):
        # Check if is hashtag
        dir_name = query.lstrip(
            '#') + '.hashtag' if query.startswith('#') else query

        dir_path = os.path.join(dir_prefix, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        print("Saving to directory: {}".format(dir_path))

        # Save Photos
        for idx, photo_link in enumerate(self.data['photo_links'], 0):
            sys.stdout.write("\033[F")
            print("Downloading {} images to ".format(idx + 1))
            # Filename
            _, ext = os.path.splitext(photo_link)
            filename = str(idx) + ext
            filepath = os.path.join(dir_path, filename)
            # Send image request
            urlretrieve(photo_link, filepath)

        # Save Captions
        #filename = str(idx) + '.txt'
        filepath = os.path.join(dir_path, "hashtag_posting_people.txt")
        with codecs.open(filepath, 'w', encoding='utf-8') as fout:
            for idx, caption in enumerate(self.data['captions'], 0):
                fout.write(caption)

        # Save followers/following
        filename = crawl_type + '.txt'
        filepath = os.path.join(dir_path, filename)
        if len(self.data[crawl_type]):
            with codecs.open(filepath, 'w', encoding='utf-8') as fout:
                for fol in self.data[crawl_type]:
                    fout.write(fol + '\n')

    def refine_number_letters(self, number_letter):
        number_letter = number_letter.replace(",", "")
        if 'k' in number_letter:
            number_letter = number_letter.replace('k', '')
            number_letter = float(number_letter) * 1000
        if '천' in number_letter:
            number_letter = number_letter.replace('천', '')
            number_letter = float(number_letter) * 1000
        return int(number_letter)


def main():
    #   Arguments  #
    parser = argparse.ArgumentParser(description='Instagram Crawler')
    parser.add_argument('-d', '--dir_prefix', type=str,
                        default='./data/', help='directory to save results')
    parser.add_argument('-q', '--query', type=str, default='instagram',
                        help="target to crawl, add '#' for hashtags")
    parser.add_argument('-t', '--crawl_type', type=str,
                        default='photos', help="Options: 'photos' | 'followers' | 'following'")
    parser.add_argument('-n', '--number', type=int, default=12,
                        help='Number of posts to download: integer')
    parser.add_argument('-c', '--caption', action='store_true',
                        help='Add this flag to download caption when downloading photos')
    parser.add_argument('-a', '--authentication', type=str, default=None,
                        help='path to authentication json file')
    args = parser.parse_args()
    #  End Argparse #

    crawler = ProfileCrawler()
    crawler.crawl(dir_prefix=args.dir_prefix,
                  query=args.query,
                  crawl_type=args.crawl_type,
                  number=args.number,
                  caption=args.caption,
                  authentication=args.authentication)

if __name__ == "__main__":
    main()