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
import time, datetime
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

sys.path.append('/Users/jack/roka/Instagram-API-python')
sys.path.append('/Users/jack/roka/Instagram-API-python/instapi/lib/python2.7/site-packages/')
from InstagramAPI import InstagramAPI
from crawl_followers import *

api = InstagramAPI("_______jack______", "ghdlWk37qkqk*")
api.login() # login


# python instagramcrawler.py -c -q '#마이홍' -d './myhong' -n 50
# python instagramcrawler.py -c -q '#mysteryskulls' -d './mysteryskulls' -n 50

def calculate_engagement_rate(user_id, size):
    do_crawl = True
    num_comments = 0
    num_likes = 0
    num_views = 0
    num_media = 0

    while do_crawl:
        if not 'max_id' in locals(): curl_url = "https://www.instagram.com/"+user_id+"/?__a=1"
        else : curl_url = "https://www.instagram.com/"+user_id+"/?__a=1&max_id="+max_id
        response = requests.get(curl_url)

        if response.status_code == 404: return 'Not current user'
        elif response.status_code == 403:
            # IP Blocking. SO we need to wait.
            print str(progress_num) + " : Have to wait cause of 403 status" 
            time.sleep(200)
            continue
    
        try:
            media_json = response.json()["user"]["media"]
        except:
            pdb.set_trace()
        for node in media_json["nodes"]:
            num_media += 1
            if "likes" in node: num_likes += node["likes"]["count"]
            if "video_views" in node: num_views += node["video_views"]

        if media_json["page_info"]["has_next_page"]:
            max_id = media_json["page_info"]["end_cursor"]
            do_crawl = True
        else: do_crawl = False

    engagement_rate = float(num_comments + num_likes + num_views) / num_media / size

    return engagement_rate


#TODO: 추후 media id와 short code가 불일치하는 녀석들도 잡아내는 코드를 해야함.
def code_to_media_id(short_code):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    media_id = 0;
    for letter in short_code:
        media_id = (media_id*64) + alphabet.index(letter)

    return media_id

def GetcommentersAndRecord(media_id, filename, max_id=''):
    if max_id == '': 
        # First request without next max_id
        api.getMediaComments(str(media_id))
    else: api.getMediaComments(str(media_id), max_id=max_id)
    commenters = api.LastJson

    commenter_set = set()
    with open(filename, 'a') as commenters_recorder:
        try:
            for comment in commenters["comments"]:
                if not comment['user']['username'] in commenter_set:
                    commenters_recorder.write(comment['user']['username']+'\t')
                    commenter_set.add(comment['user']['username'])

        except KeyError:
            # In this case, 400 HTTP status occured.
            # Therefore data were not loaded.
            # {u'status': u'fail', u'message': u'Please wait a few minutes before you try again.'}
            print "Time to wait more than 3 min."
            return maxid

    try:
        return commenters["next_max_id"]
    except KeyError:
        return "End"


class url_change(object):
    """
        Used for caption scraping
    """
    def __init__(self, prev_url):
        self.prev_url = prev_url

    def __call__(self, driver):
        return self.prev_url != driver.current_url 
class TagpostCrawler(object):
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

        WebDriverWait(self._driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CSS_EXPLORE))
        )

    def quit(self):
        self._driver.quit()
    def crawl(self, dir_prefix, query, crawl_type, number, caption, authentication):
        print("dir_prefix: {}, query: {}, crawl_type: {}, number: {}, caption: {}, authentication: {}"
              .format(dir_prefix, query, crawl_type, number, caption, authentication))

        if crawl_type == "photos":
            # Browse target page
            self.browse_target_page(query)

            # Scrape captions if specified
            if caption is True:
                if query.startswith("#"):
                    number_posts = WebDriverWait(
                            self._driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "._fd86t"))
                                    ).text
                    number = self.refine_number_letters(number_posts) 

                self.click_and_scrape_captions(number, query)

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
        
    def click_and_scrape_captions(self, number, query):
        print("Scraping captions...")
        captions = set()
        num_of_influ = 0 

        for post_num in range(number):
            sys.stdout.write("\033[F")
            print("Scraping captions {} / {}".format(post_num+1,number))
            if post_num == 0:  # Click on the first post
                url_before = self._driver.current_url
                self._driver.find_element_by_xpath(
                    FIREFOX_FIRST_POST_PATH).click()
                while True:
                    try:
                        WebDriverWait(self._driver, 0.2).until(
                            url_change(url_before))
                        break
                    except TimeoutException:
                        self._driver.find_element_by_xpath(
                            FIREFOX_FIRST_POST_PATH).click()
                        continue

                if number != 1:  #
                    while True:
                        try:
                            WebDriverWait(self._driver, 0.2).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, CSS_RIGHT_ARROW)
                                )
                            )
                            break
                        except TimeoutException:
                            continue

            elif number != 1:  # Click Right Arrow to move to next post
                url_before = self._driver.current_url
                while True:
                    try:
                        self._driver.find_element_by_css_selector(
                            CSS_RIGHT_ARROW).click()
                        break
                    except NoSuchElementException:
                        try:
                            self._driver.find_element_by_css_selector(
                                CSS_LEFT_ARROW)

                            return
                        except NoSuchElementException:
                            # If there are no left and right arrows, then It should be waited until the arrow appears
                            continue

                        # If there is only left arrow, then this photo is the last one.

                # Wait until the page has loaded
                while True:
                    try:
                        WebDriverWait(self._driver, 0.2).until(
                            url_change(url_before))
                        break
                    except TimeoutException:
                        try:
                            self._driver.find_element_by_css_selector(
                                CSS_RIGHT_ARROW).click()
                            continue
                        except NoSuchElementException:
                            try:
                                self._driver.find_element_by_css_selector(
                                    CSS_LEFT_ARROW)
                                return
                            except NoSuchElementException:
                                # If there are no left and right arrows, then It should be waited until the arrow appears
                                pdb.set_trace()

            time.sleep(1)
            if not self.korean_detection(): continue # If not korean, then click right arrow.

            while True:
                try:
                    user_id = self._driver.find_element_by_css_selector(CSS_USER_ID).text
                    break
                except:  
                    continue

            cur_url = self._driver.current_url
            short_code = cur_url.split("/p/")[-1].split("/")[0]
            media_id = code_to_media_id(short_code)
            api.mediaInfo(media_id)
            created_at = api.LastJson["items"][0]['taken_at']
            if datetime.datetime.fromtimestamp(created_at).year != 2017 : continue

            api.searchUsername(user_id)
            num_followers = api.LastJson['user']['follower_count']
            if num_followers < 1000: continue

            engagement_rate = calculate_engagement_rate(user_id, num_followers)

            dir_path = "./influ_with_engagement_rate/"
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            influ_file = dir_path+query+".txt"
            with open(influ_file, 'a') as f:
                f.write(user_id+"\t"+str(engagement_rate)+"\t"+cur_url+"\n")

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

    crawler = TagpostCrawler()
    crawler.crawl(dir_prefix=args.dir_prefix,
                  query=args.query,
                  crawl_type=args.crawl_type,
                  number=args.number,
                  caption=args.caption,
                  authentication=args.authentication)


if __name__ == "__main__":
    main()





"""
    Crawl commenter and liker
            user_pk = api.LastJson['user']['pk']
            prev_max_id = 0

            dir_path = "./"+query+"_reflected/"
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            reflected_users_file = dir_path+str(short_code)+".txt"
            with open(reflected_users_file, 'a') as f:
                f.write(cur_url+'\n'+user_id+"\n")

            max_id = GetFollowersAndRecord(api, user_pk, reflected_users_file)
            while True:
                if max_id == 'End':break
                elif max_id == prev_max_id: time.sleep(200)

                prev_max_id = max_id
                max_id = GetFollowersAndRecord(api, user_pk, reflected_users_file, maxid=max_id) 

            api.getMediaLikers(media_id)
            likers = api.LastJson['users']
            with open(reflected_users_file, 'a') as f:
                f.write('\n')
                for liker in likers:
                    f.write(liker['username']+"\t")
                f.write('\n')

            prev_max_id = 0
            max_id = GetcommentersAndRecord(media_id, reflected_users_file, max_id='')

            while True:
                if max_id == 'End': break
                elif max_id == prev_max_id: time.sleep(200)

                prev_max_id = max_id
                max_id = GetcommentersAndRecord(media_id, reflected_users_file, max_id=max_id)
"""
