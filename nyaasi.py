# -*- coding: utf-8 -*-
#VERSION: 2.0
#AUTHORS: Maxime (custom plugin)

# Improved Nyaa.si search plugin for qBittorrent
# Fixes issues with the original plugin not fetching all results

import re
from html.parser import HTMLParser

try:
    from novaprinter import prettyPrinter
    from helpers import retrieve_url
except ModuleNotFoundError:
    pass


class nyaasi(object):
    """Search plugin for nyaa.si"""

    url = 'https://nyaa.si'
    name = 'Nyaa.si'

    supported_categories = {
        'all': '0_0',
        'anime': '1_0',
        'music': '2_0',
        'books': '3_0',
        'tv': '4_0',
        'movies': '4_0',
        'pictures': '5_0',
        'software': '6_0',
    }

    class NyaaParser(HTMLParser):
        """Parse nyaa.si search results page."""

        def __init__(self, results, base_url):
            super().__init__()
            self.results = results
            self.base_url = base_url
            self.current_item = None
            self.in_row = False
            self.td_index = -1
            self.in_td = False
            self.current_data = ''
            self.found_name = False
            self.found_link = False

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)

            if tag == 'tr':
                class_val = attrs_dict.get('class', '')
                if 'default' in class_val or 'success' in class_val or 'danger' in class_val:
                    self.in_row = True
                    self.current_item = {}
                    self.td_index = -1
                    self.found_name = False
                    self.found_link = False

            elif tag == 'td' and self.in_row:
                self.td_index += 1
                self.in_td = True
                self.current_data = ''

                # Column 1 has the timestamp attribute
                if self.td_index == 4:
                    timestamp = attrs_dict.get('data-timestamp', '-1')
                    try:
                        self.current_item['pub_date'] = int(timestamp)
                    except (ValueError, TypeError):
                        self.current_item['pub_date'] = -1

            elif tag == 'a' and self.in_row:
                href = attrs_dict.get('href', '')

                # Column 1 (index 1): torrent name link
                if self.td_index == 1 and not self.found_name:
                    if href.startswith('/view/') and 'title' in attrs_dict:
                        self.current_item['name'] = attrs_dict['title']
                        self.current_item['desc_link'] = self.base_url + href
                        self.current_item['engine_url'] = self.base_url
                        self.found_name = True

                # Column 2 (index 2): download links (magnet and .torrent)
                elif self.td_index == 2 and not self.found_link:
                    if href.startswith('magnet:?'):
                        self.current_item['link'] = href
                        self.found_link = True
                    elif href.endswith('.torrent'):
                        # Fallback to .torrent if no magnet yet
                        if 'link' not in self.current_item:
                            self.current_item['link'] = self.base_url + href

        def handle_data(self, data):
            if self.in_td and self.in_row:
                self.current_data += data.strip()

        def handle_endtag(self, tag):
            if tag == 'td' and self.in_row:
                self.in_td = False

                # Column 3 (index 3): size
                if self.td_index == 3:
                    self.current_item['size'] = self.current_data

                # Column 5 (index 5): seeders
                elif self.td_index == 5:
                    try:
                        self.current_item['seeds'] = int(self.current_data)
                    except ValueError:
                        self.current_item['seeds'] = -1

                # Column 6 (index 6): leechers
                elif self.td_index == 6:
                    try:
                        self.current_item['leech'] = int(self.current_data)
                    except ValueError:
                        self.current_item['leech'] = -1

            elif tag == 'tr' and self.in_row:
                self.in_row = False
                # Validate we have all required fields
                if self.current_item and 'name' in self.current_item and 'link' in self.current_item:
                    # Set defaults for missing fields
                    self.current_item.setdefault('seeds', -1)
                    self.current_item.setdefault('leech', -1)
                    self.current_item.setdefault('size', '-1')
                    self.current_item.setdefault('pub_date', -1)
                    self.current_item.setdefault('engine_url', self.base_url)
                    self.current_item.setdefault('desc_link', self.base_url)
                    self.results.append(self.current_item)
                self.current_item = None

    def search(self, what, cat='all'):
        """
        Search nyaa.si for torrents.

        Parameters:
            what: search query (already URL-encoded with + for spaces)
            cat: category name from supported_categories
        """
        category = self.supported_categories.get(cat, '0_0')
        page = 1
        max_pages = 10  # safety limit

        while page <= max_pages:
            url = "{base}/?f=0&c={cat}&q={query}&s=seeders&o=desc&p={page}".format(
                base=self.url,
                cat=category,
                query=what,
                page=page
            )

            try:
                html = retrieve_url(url)
            except Exception:
                break

            if not html:
                break

            results = []
            parser = self.NyaaParser(results, self.url)
            parser.feed(html)
            parser.close()

            # No results on this page means we've reached the end
            if not results:
                break

            for item in results:
                prettyPrinter(item)

            # Nyaa.si shows 75 results per page
            if len(results) < 75:
                break

            page += 1
