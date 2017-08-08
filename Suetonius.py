#!/usr/bin/python3

#############################################################
#
# Suetonius is meant to be a simple imageboard archiver. It
# identifies thread URLs from the catalog of multiple image
# boards and then downloads every thread in JSON format and
# tags them with metadata before storing them in MongoDB,
# This program is intended to be an uncomplicated way to hold
# imageboard comments for later processing or storage in an
# RDBMS.
#
##############################################################

import requests
from pymongo import MongoClient
import configparser
import json
from fake_useragent import UserAgent
from datetime import datetime
import logging
import pdb

# Load our configuration file
config = configparser.ConfigParser()
config.read('Config.ini')
# Keep a log file of non-serious errors for later autopsy
logging.basicConfig(filename='Error Log',level=logging.DEBUG)

class RequestHandler:
    '''
    This module contains methods used for making and managing request
    objects. These methods should return lists of threads as well as
    JSON objects of threads themselves for database storage.
    '''
    def __init__(self,site,board):
        # Use variables defined in our config
        self.board = board
        self.cat_url = config[site]['catalog_url'].format(board=board)
        self.thread_url_root = config[site]['thread_url']
        self.user_agent = UserAgent().random # Low-effort fingerprinting evasion
        self.headers = {'User-Agent':self.user_agent}

    def get_list_threads(self):
        # Method for reading thread from threads.json page
        response = requests.get(self.cat_url)
        resp_json = json.loads(response.text)
        # There is probably a less dumb way of doing this
        threadlist_tmp = [[row['no'] for row in page['threads']] for page in resp_json]
        threadlist = list()
        for x in threadlist_tmp:
            threadlist += x
        return threadlist

    def get_list_catalog(self):
        # Gets threads from catalog when site does not have threads.json
        response = requests.get(self.cat_url)
        resp_json = json.loads(response.text)
        threadlist = [x['threadId'] for x in resp_json]
        return threadlist

    def get_thread(self,thread_num):
        # HTTP GET request constructed from thread number and URL
        thread_url = self.thread_url_root.format(board=self.board,thread_num=thread_num)
        response = requests.get(thread_url)
        resp_json = json.loads(response.text)
        return resp_json

class MongoHandler:
    '''
    This module contains methods related to creating a connection to
    the MongoDB as well as retrieving, inserting and updating JSONs
    obtained by RequestHandler
    '''
    def __init__(self):
        # Init handles variables consistent across boards.
        self.host = config['DATABASE']['server']
        self.port = int(config['DATABASE']['port'])
        self.dbname = config['DATABASE']['database']
        self.client = MongoClient(self.host,self.port)
        self.db = self.client[self.dbname] # All sites/boards use one DB for now

    def load_collection(self,site):
        # Broken out of init for fault tolerance
        collection = self.db[site]
        return collection

    def insert_thread(self,collection, tagged_thread):
        collection.insert_one(tagged_thread)
        return True

    def update_thread(self,collection,tagged_thread,thread_id):
        collection.replace_one({'_id':thread_id},tagged_thread)
        return True

class ThreadProcessor:
    '''
    This class contains methods needed to provide tagging for the JSON
    objects extracted from the request class. This class will also
    include any future methods used for extracting data from posts or
    site-specific post handling.
    '''

    def __init__(self,thread_data,thread_id,board):
        self.thread_data = thread_data #raw json from chan
        self.thread_id = thread_id
        self.board = board

    def tag(self):
        # Any metadata a thread should be tagged with should go here
        # For now, _id (for indexing), the boardname (to allow sorting)
        # and a timestamp of our last update are all that is included.
        tagged_thread = self.thread_data
        tagged_thread['_id'] = self.thread_id
        tagged_thread['board'] = self.board
        tagged_thread['last update'] = str(datetime.utcnow()) #real men use Z-time
        return tagged_thread

    
################################################################
if __name__ == '__main__':
    # Instantiate a list of imageboards
    site_list = list()
    for key in config:
        if key !='DATABASE' and key !='DEFAULT': #configparser adds a DEFAULT key
            site_list.append(key)
    # Make DB connection
    try:
        db = MongoHandler()
    except:
        # Failing the server connection renders all else moot.
        # Failure should notify the user and exit.
        print('[!] DATABASE CONNECTION FAILED')
        print('[!] VERIFY THE MONGODB SERVER AND CONFIG FILE')
        print('[!] TRY: "netstat -punta" TO FIND LISTENER PORT 27017')
        quit()
    print('%d image boards to archive . . .' % len(site_list))
    counter = 0
    for site in site_list:
        print('%d/%d complete. Current imageboard: %s' %(counter,len(site_list),site))
        counter += 1
        # Retrieve and clean our whitelist of boards
        board_list = config[site]['board_whitelist']
##        pdb.set_trace()
        board_list = board_list.split(',')
        board_list = [x.strip() for x in board_list]
        print('%d boards to process . . .' %len(board_list))
        threadlist_support = bool(int(config[site]['list_type'])) # prestidigitation to get a boolean
        for board in board_list:
            print('\nGetting threads for board: %s' % board)
            logging.debug('CURRENT LOCATION: %s\t%s' % (site,board))
            thread_jsons = list() # container for thread JSON objects
            col = db.load_collection(site) # db collection object
            r = RequestHandler(site,board)
##            pdb.set_trace()
            try:
                # Fetch threads.json if available or catalog.json
                if threadlist_support:
                    threadlist = r.get_list_threads()
                else:
                    threadlist = r.get_list_catalog()
                print('%d Threads to archive . . .' %len(threadlist))
            except:
                # Tell us what failed, and skip to the next loop
                print('[!] FAILED TO FETCH THREADLIST!')
                print('SITE: %s\t|BOARD: %s' % (site,board))
                logging.error('Catalog GET failure SITE: %s\t|BOARD: %s' % (site,board))
                continue
            thread_counter = 0 # Counter to see progress in STDOUT.
            for thread in threadlist:
                progress = int(thread_counter/len(threadlist)*100)
                print('\rPROGRESS: {p}%'.format(p=progress),end='',flush=True)
                thread_counter += 1
##                pdb.set_trace()
                try:
                    # Tag the JSON and append to our list
                    thread_data = r.get_thread(thread)
                    tp = ThreadProcessor(thread_data,thread,board)
                    tagged_thread = tp.tag()
                    thread_jsons.append(tagged_thread)
                except:
                    # We didn't inb4 404. Log and continue
                    logging.warning('Thread GET failure: %s\t|%s\t|%s' % (site,board,thread))
                    continue
            for json_obj in thread_jsons:
##                pdb.set_trace()
                #Test for thread id
                thread_id = json_obj['_id']
                if col.find_one({"_id":thread_id}):
                    try:
                        db.update_thread(col,json_obj,json_obj['_id'])
                    except:
                        logging.error('DB UPDATE ERROR SITE:%s\tTHREAD ID:%s\t|%s'
                                      %(site,json_obj['_id'],err))
                else:
                    try:
                        db.insert_thread(col,json_obj)
                    except Exception as err:
                        print('[!] DB WRITE ERROR! :',err)
                        logging.error('DB WRITE ERROR SITE:%s\tTHREAD ID:%s\t|%s'
                                      %(site,json_obj['_id'],err))
            
    print('Database updated. Exiting . . .')
    quit()
