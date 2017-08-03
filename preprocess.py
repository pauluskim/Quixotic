#-*- coding: utf-8 -*-
import sys 
reload(sys)
sys.setdefaultencoding('utf-8')

import os

def influencer_candidates():
    posting_people = "/Users/jack/roka/InstagramCrawler/myhong/myhong_hashtag/hashtag_posting_people.txt" 
    candidates_set = set()
    with open(posting_people, 'r') as candidate_post:
        for line in candidate_post:
            candidate = line.strip()
            candidates_set.add(candidate)
    return candidates_set
                
