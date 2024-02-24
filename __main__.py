#************ IMPORTS ************#
import argparse
import multiprocessing.pool
import random
import string
import time
from configparser import ConfigParser
from typing import List

import httpx
import qbittorrentapi
from bs4 import BeautifulSoup
#*********************************#

#************ LOAD CONFIG ************#
config = ConfigParser()
config.read('MagnetScraper/config.ini')
WEB_UI_INFO = dict(config['WEB_UI_INFO'])
WEB_UI_INFO['port'] = int(WEB_UI_INFO['port'])
#*************************************#

#************ UTILITY FUNCTIONS ************#
def parse():
    """Parses and returns command line arguments / options."""
    parser = argparse.ArgumentParser(description="Sends scraped magnet links from URL to qBittorrent client, downloading to SAVE_PATH.")
    parser.add_argument("URL", metavar="\"URL\"", help="URL to be scraped for magnet links.")
    parser.add_argument("SAVE_PATH", metavar="\"SAVE_PATH\"", help="Directory within which to save torrents.")
    parser.add_argument("-o", action='store_true', help="Download torrents one by one.")
    parser.add_argument("-r", action='store_true', help="Remove torrents from client after download.")
    args = parser.parse_args()
    return args.URL, args.SAVE_PATH, args.o, args.r

def get_magnet_links(url: str) -> List[str]:
    soup = BeautifulSoup(httpx.get(url).text, 'html.parser')
    magnets = []
    for link in soup.find_all('a'):
        text = link.get('href')
        if text.startswith("magnet:"): magnets.append(text)
    return magnets

def exit_with_msg(msg):
    print(msg)
    raise SystemExit()

def random_str(length: int):
    """Random string of lowercase letters and digits."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# Overkill for current implementation, but nice idea.
def torrents_add_and_get_hashes(self, **kwargs) -> List[str]:
    """Wraps qbittorrentapi.Client.torrents_add() to also return hashes of added torrents."""
    original_cat = None 
    if 'category' in kwargs: original_cat = kwargs['category']

    temp_cat = "temp" # Generate unique, temporary category.
    while temp_cat in self.torrents_categories(): temp_cat = random_str(length=5)
    kwargs['category'] = temp_cat

    self.torrents_add(**kwargs)
    hashes = [ torrent_info.hash for torrent_info in self.torrents_info(category=temp_cat) ]
    self.torrent_categories.remove_categories(categories=temp_cat)
    if original_cat: self.torrents_set_category(torrent_hashes=hashes, category=original_cat)
    return hashes
qbittorrentapi.Client.torrents_add_and_get_hashes = torrents_add_and_get_hashes
#*******************************************#

class qBittorrentHandler:
    def __init__(self, magnets: List[str], save_path: str, one_by_one: bool):
        self._obo = one_by_one
        self._qb = qbittorrentapi.Client(**WEB_UI_INFO)
        self.verify_login()

        # Different implementation of the below 4 lines via function.
        #self._hashes = self._qb.torrents_add_and_get_hashes(urls=magnets, save_path=save_path, paused=True)

        # Note: A random category is created to use to retrieve the hashes of the added torrents.
        temp_cat = random_str(length=5)
        self._qb.torrents_add(urls=magnets, save_path=save_path, category=temp_cat, is_paused=True)
        self._hashes = [ torrent_info.hash for torrent_info in self._qb.torrents_info(category=temp_cat) ]
        self._qb.torrent_categories.remove_categories(categories=temp_cat)

    def verify_login(self):
        """Authenticates login credentials and times-out in case of error(s)."""
        try:
            with multiprocessing.pool.Pool() as pool:
                pool.apply_async(self._qb.auth_log_in).get(timeout=10)
        except multiprocessing.context.TimeoutError: # If qbittorrent isnt open, program never stops.
            exit_with_msg("Login timeout. Ensure qBittorrent is active.")
        except qbittorrentapi.LoginFailed:
            exit_with_msg("Login failed. Ensure WEB_UI_INFO credentials within config.ini are accurate.")

    def all_complete(self) -> bool:
        """Returns true if all torrents are complete, otherwise returns false."""
        info = self._qb.torrents_info(torrent_hashes=self._hashes)
        return all( [torrent.state == "pausedUP" for torrent in info] )

    def download(self):
        """Torrents will be finished downloading upon return if self._obo flag is true, otherwise no guarantee of completion."""
        if self._obo:
            for hsh in self._hashes:
                self._qb.torrents_resume(torrent_hashes=hsh)
                while self._qb.torrents_info(torrent_hashes=hsh)[0].state != "pausedUP": time.sleep(10)
        else: self._qb.torrents_resume(torrent_hashes=self._hashes)
        
    def delete_all(self):
        """Removes all torrents from qBittorrent client (doesn't delete files)."""
        self._qb.torrents_delete(delete_files=False, torrent_hashes=self._hashes)

#******************* MAIN ************************#
url, save_path, one_by_one, remove = parse()
magnets = get_magnet_links(url)

qbh = qBittorrentHandler(magnets, save_path, one_by_one)
qbh.download()
if remove:
    while not qbh.all_complete(): time.sleep(30)
    qbh.delete_all()
#*************************************************#
