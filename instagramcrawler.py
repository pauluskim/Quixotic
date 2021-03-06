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

# python instagramcrawler.py -c -q '#마이홍' -d './myhong' -n 50

# HOST
HOST = 'http://www.instagram.com'
# SELENIUM CSS SELECTOR
CSS_LOAD_MORE = "a._8imhp._glz1g"
CSS_RIGHT_ARROW = "a[class='_3a693 coreSpriteRightPaginationArrow']"
CSS_LEFT_ARROW = "a[class='_jra99 coreSpriteLeftPaginationArrow']"
FIREFOX_FIRST_POST_PATH = "//div[contains(@class, '_mck9w _gvoze _f2mse')]"
TIME_TO_CAPTION_PATH = "../../../div/ul/li/span"


# FOLLOWERS/FOLLOWING RELATED
CSS_EXPLORE = "a[href='/explore/']"
CSS_LOGIN = "a[href='/accounts/login/']"
CSS_FOLLOWERS = "a[href='/{}/followers/']"
CSS_FOLLOWING = "a[href='/{}/following/']"
FOLLOWER_PATH = "//div[contains(text(), 'Followers')]"
XPATH_FOLLOWERS_COUNT = '//*[contains(concat( " ", @class, " " ), concat( " ", "_bnq48", " " )) and (((count(preceding-sibling::*) + 1) = 2) and parent::*)]//*[contains(concat( " ", @class, " " ), concat( " ", "_fd86t", " " ))]'
CSS_FOLLOWERS_COUNT = '._218yx:nth-child(2) ._bkw5z'

CSS_NUM_PHOTO_LIKE = "._nzn1h span"
CSS_USER_ID = "._iadoq"
CSS_NUM_VIEW = "._m5zti span"
CSS_NUM_VIDEO_LIKE = "._m10kk span"
CSS_PLACE = "._60iqg"

# JAVASCRIPT COMMANDS
SCROLL_UP = "window.scrollTo(0, 0);"
SCROLL_DOWN = "window.scrollTo(0, document.body.scrollHeight);"

class url_change(object):
    """
        Used for caption scraping
    """
    def __init__(self, prev_url):
        self.prev_url = prev_url

    def __call__(self, driver):
        return self.prev_url != driver.current_url 
class InstagramCrawler(object):
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
            # Scroll down until target number photos is reached
            #self.scroll_to_num_of_posts(number)

            # Scrape photo links
            #self.scrape_photo_links(number, is_hashtag=query.startswith("#"))
            # Scrape captions if specified
            if caption is True:
                if query.startswith("#"):
                    number_posts = WebDriverWait(
                            self._driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "._fd86t"))
                                    ).text
                    number = self.refine_number_letters(number_posts) 


                self.click_and_scrape_captions(number, query)

        elif crawl_type in ["followers", "following"]:
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

        if not query.startswith('#'):
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

    def scroll_to_num_of_posts(self, number):
        # Get total number of posts of page
        num_info = re.search(r'\], "count": \d+',
                             self._driver.page_source).group()
        num_of_posts = int(re.findall(r'\d+', num_info)[0])
        print("posts: {}, number: {}".format(num_of_posts, number))
        number = number if number < num_of_posts else num_of_posts

        # scroll page until reached
        loadmore = WebDriverWait(self._driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "._bkw5z"))
        )
        loadmore.click()

        num_to_scroll = int((number - 12) / 12) + 1
        for _ in range(num_to_scroll):
            self._driver.execute_script(SCROLL_DOWN)
            time.sleep(0.2)
            self._driver.execute_script(SCROLL_UP)
            time.sleep(0.2)

    def scrape_photo_links(self, number, is_hashtag=False):
        print("Scraping photo links...")
        encased_photo_links = re.finditer(r'src="([https]+:...[\/\w \.-]*..[\/\w \.-]*'
                                          r'..[\/\w \.-]*..[\/\w \.-].jpg)', self._driver.page_source)

        photo_links = [m.group(1) for m in encased_photo_links]

        print("Number of photo_links: {}".format(len(photo_links)))

        begin = 0 if is_hashtag else 1

        self.data['photo_links'] = photo_links[begin:number + begin]

    def korean_detection(self):
        try:
            time_element = WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "time"))
            )
            caption = time_element.find_element_by_xpath(
                TIME_TO_CAPTION_PATH).text
        except NoSuchElementException:  # Forbidden
            print("Caption not found in the {} photo".format(post_num))
            caption = ""
        if detect(caption) == 'ko':
            return True
        else:
            return False
        
    def click_and_scrape_captions(self, number, query):
        print("Scraping captions...")
        captions = set()
        num_of_influ = 0 

        for post_num in range(number):
            sys.stdout.write("\033[F")
            print("Scraping captions {} / {}".format(post_num+1,number))
            if post_num == 0:  # Click on the first post
                # Chrome
                # self._driver.find_element_by_class_name('_ovg3g').click()
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

            try:
                num_photo_like = self._driver.find_element_by_css_selector(CSS_NUM_PHOTO_LIKE).text
                num_video_like = "Photo"
                num_video_view = ""
            except:
                try:
                    video_toggle = self._driver.find_element_by_css_selector(CSS_NUM_VIEW)
                    video_toggle.click()
                    num_video_view = video_toggle.text
                    num_video_like = self._driver.find_element_by_css_selector(CSS_NUM_VIDEO_LIKE).text
                    num_photo_like = 'Video'
                except:
                    num_photo_like = "No Like" 
                    num_video_like = "No Like"
                    num_video_view = "No Like"
            try:
                place = self._driver.find_element_by_css_selector(CSS_PLACE).text
            except:
                place = "NoComment"

            #captions = self._driver.find_element_by_css_selector('._ezgzd:nth-child(1)').text
            current_url = self._driver.current_url

            num_followers = self.num_followers(user_id)
            if num_followers >= 1000:
                num_of_influ += 1

                file_path = "/Users/jack/roka/InstagramCrawler/"+query+"/"

                if not os.path.exists(file_path):
                    os.makedirs(file_path)

                with open(file_path+"influ_with_meta_ver.ko.xls", 'a') as influ_file:
                    #user = "user_id: " + user_id
                    #num_foll = "Number of followers: " + str(num_followers)
                    #like_line = "LIKE: "+str(num_like)
                    #place_line = "Place: " + place
                    #caption_line = "Contents" + captions
                    #url_addr  = "URL: \n" + current_url
                    line = "\t".join((str(num_of_influ), user_id, str(num_followers), str(num_photo_like), str(num_video_view), str(num_video_like), place, current_url, '\n'))
                    influ_file.write(line)


    def num_followers(self, user_id):
        checker = InstagramCrawler()


        while True:
            try:
                checker.browse_target_page(user_id)
                num_followers = WebDriverWait(checker._driver, 1).until(
                    EC.presence_of_element_located(
                        (By.XPATH, XPATH_FOLLOWERS_COUNT))
                ).text
                break
            except:
                try:
                    error_msg = WebDriverWait(checker._driver, 1).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h2'))).text
                    if error_msg == '죄송합니다. 페이지를 사용할 수 없습니다.': break
                    else:break 
                except:
                    continue

        num_followers = self.refine_number_letters(num_followers) 

        checker.quit()  
        return num_followers

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
        follow_ele.click()

        title_ele = WebDriverWait(self._driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, FOLLOW_PATH))
        )
        List = title_ele.find_element_by_xpath(
            '..').find_element_by_tag_name('ul')
        List.click()

        # Loop through list till target number is reached
        num_of_shown_follow = len(List.find_elements_by_xpath('*'))

        while len(List.find_elements_by_xpath('*')) < number:
            element = List.find_elements_by_xpath('*')[-1]
            # Work around for now => should use selenium's Expected Conditions!
            try:
                element.send_keys(Keys.PAGE_DOWN)
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

    crawler = InstagramCrawler()
    crawler.crawl(dir_prefix=args.dir_prefix,
                  query=args.query,
                  crawl_type=args.crawl_type,
                  number=args.number,
                  caption=args.caption,
                  authentication=args.authentication)


if __name__ == "__main__":
    main()
