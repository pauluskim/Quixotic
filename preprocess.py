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
                
def organize_txt2csv():
    file_path = '/Users/jack/roka/InstagramCrawler/myhong/filtered/influ_with_meta'
    with open(file_path+".txt", 'r') as txt, open(file_path+".xls", 'w') as csv:
        for line in txt:
            line = line.strip()
            element = line.split(': ')[-1]
            if line == '':
                csv.write('\n')
            else:
                csv.write(element+"\t")
            
if __name__ == "__main__":
    organize_txt2csv()
