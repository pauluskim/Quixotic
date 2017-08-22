#-*- coding: utf-8 -*-
from __future__ import division
import sys 
reload(sys)
sys.setdefaultencoding('utf-8')

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
FOLLOWER_PATH = "//div[contains(text(), '팔로워')]"
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
