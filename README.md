# MagnetScraper

## Setup
+ Update config.ini with host, port, username, and password that align with that of your qBittorrent client's WEB UI options.
+ Use -o flag to download torrents one by one, use -r flag to automatically remove torrents from client upon completion (doesn't delete files).
+ Requires httpx, qbittorrentapi, and BeautifulSoup4 libaries.

## Usage
+ Navigate to parent directory of MagnetScraper and run ```python MagnetScraper -h``` to see help interface.
+ If you change the name of the MagnetScraper directory, be sure to update config path within __main__.py accordingly (to ensure config can still be loaded)
+ In the command-line, wrap URL and PATH in quotation marks.
