# -*- coding: utf-8 -*-
#VERSION: 1.0
#AUTHORS: Maxime (custom plugin)

# YTS.gg search plugin for qBittorrent
# Uses the YTS JSON API for reliable results

import json
from urllib.parse import quote_plus

try:
    from novaprinter import prettyPrinter
    from helpers import retrieve_url
except ModuleNotFoundError:
    pass


class ytsgg(object):
    """Search plugin for yts.gg (YIFY movies)"""

    url = 'https://yts.gg'
    name = 'YTS.gg'

    # YTS only has movies
    supported_categories = {
        'all': '',
        'movies': '',
    }

    # Trackers for magnet link construction
    trackers = [
        'udp://open.demonii.com:1337/announce',
        'udp://tracker.openbittorrent.com:80',
        'udp://tracker.coppersurfer.tk:6969',
        'udp://glotorrents.pw:6969/announce',
        'udp://tracker.opentrackr.org:1337/announce',
        'udp://torrent.gresille.org:80/announce',
        'udp://p4p.arenabg.com:1337',
        'udp://tracker.leechers-paradise.org:6969',
    ]

    def _build_magnet(self, torrent_hash, name):
        """Build a magnet link from hash and movie name."""
        encoded_name = quote_plus(name)
        tracker_params = ''.join(['&tr=' + t for t in self.trackers])
        return "magnet:?xt=urn:btih:{hash}&dn={name}{trackers}".format(
            hash=torrent_hash,
            name=encoded_name,
            trackers=tracker_params
        )

    def _size_to_bytes(self, size_str, size_unit):
        """Convert size string and unit to bytes."""
        try:
            size = float(size_str)
        except (ValueError, TypeError):
            return -1

        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'TB': 1024 * 1024 * 1024 * 1024,
        }
        return int(size * multipliers.get(size_unit, 1))

    def search(self, what, cat='all'):
        """
        Search YTS for movies.

        Parameters:
            what: search query (already URL-encoded with + for spaces)
            cat: category name from supported_categories
        """
        page = 1
        limit = 50  # max allowed by API
        max_pages = 5  # safety limit (250 results max)

        while page <= max_pages:
            api_url = (
                "{base}/api/v2/list_movies.json"
                "?query_term={query}"
                "&limit={limit}"
                "&page={page}"
                "&sort_by=seeds"
                "&order_by=desc"
            ).format(
                base=self.url,
                query=what,
                limit=limit,
                page=page
            )

            try:
                response = retrieve_url(api_url)
            except Exception:
                break

            if not response:
                break

            try:
                data = json.loads(response)
            except (json.JSONDecodeError, ValueError):
                break

            if data.get('status') != 'ok':
                break

            movies_data = data.get('data', {})
            movie_count = movies_data.get('movie_count', 0)
            movies = movies_data.get('movies', [])

            if not movies:
                break

            for movie in movies:
                title = movie.get('title_long', movie.get('title', 'Unknown'))
                movie_url = movie.get('url', self.url)
                date_uploaded = movie.get('date_uploaded_unix', -1)
                torrents = movie.get('torrents', [])

                for torrent in torrents:
                    torrent_hash = torrent.get('hash', '')
                    quality = torrent.get('quality', '')
                    torrent_type = torrent.get('type', '')
                    size_bytes = torrent.get('size_bytes', 0)
                    seeds = torrent.get('seeds', 0)
                    peers = torrent.get('peers', 0)

                    if not torrent_hash:
                        continue

                    # Build descriptive name: "Movie Title (Year) [Quality] [Type]"
                    name = "{title} [{quality}]".format(
                        title=title,
                        quality=quality
                    )
                    if torrent_type:
                        name += " [{type}]".format(type=torrent_type)

                    magnet = self._build_magnet(torrent_hash, title)

                    result = {
                        'link': magnet,
                        'name': name,
                        'size': str(size_bytes) if size_bytes else '-1',
                        'seeds': seeds,
                        'leech': peers,
                        'engine_url': self.url,
                        'desc_link': movie_url,
                        'pub_date': date_uploaded if date_uploaded else -1,
                    }

                    prettyPrinter(result)

            # Check if there are more pages
            if page * limit >= movie_count:
                break

            page += 1
