#!/usr/bin/env python
# -*- coding: utf8 -*-
# ted-scrape.py - Downloads metadata of TED videos and outputs it as a JSON
# file.
# Copyright (C) 2012 Gabriel Rodríguez Alberich <chewie@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import argparse
import os
import sys
import re
import datetime
from lxml import html, etree
import json
import urllib2


_USERAGENT = 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.0.5)' \
             ' Gecko/2008121622 Ubuntu/8.04 (hardy) Firefox/3.0.5'
headers = {'User-Agent': _USERAGENT}

last_url = "http://feeds.feedburner.com/tedtalks_video"
view_url_p = "http://ted.com/talks/view/id/%(video_id)s"
video_re = '<script>q\("talkPage.init",(?P<video_json>.*?)\)<\/script>'
author_re = '<a target="_blank" title="(?P<author_name>.+?)\'s bio" ' \
            'href="/speakers/.*?\.html">Full bio'
date_re = '<strong>Filmed</strong> (?P<filmed_date>.+?) &bull;'
event_re = '<span class="event-name">(?P<event>.+?)</span>'


def main(overwrite=False):
    last_talks = urllib2.urlopen(urllib2.Request(last_url, headers=headers)).\
                    read()
    root = etree.fromstring(last_talks)
    candidate_ids = [int(x.text) for x in root.xpath("//a:talkId",
                     namespaces={'a': 'http://developer.longtailvideo.com/'})]

    if os.path.isfile("ted-scrape.json"):
        with open("ted-scrape.json", "r") as f:
            ted_videos = json.load(f)
            if overwrite:
                 ted_videos = [x for x in ted_videos if x['video_id'] not in
                               candidate_ids]
            video_ids = [x['video_id'] for x in ted_videos]
            # Note: this will work as expected only if the script is executed
            # frequently enough as to not let the RSS feed fill with new talks
            # (currently, more than once every 5 months aprox.)
            missing_ids = [x for x in candidate_ids if x not in video_ids]
    else:
        ted_videos = []
        max_id = max(candidate_ids)
        missing_ids = range(1, max_id + 1)

    for video_id in missing_ids:
        video_dict = {'video_id': video_id}
        print('Downloading video page %(video_id)d...' % video_dict,
              file=sys.stderr)
        video_page = None
        while True:
            try:
                u = urllib2.urlopen(urllib2.Request(view_url_p % video_dict,
                                    headers=headers))
                video_page = u.read()
                break
            except urllib2.HTTPError:
                print("No TED video with id %s. Skipping." % video_id,
                      file=sys.stderr)
                break
            except urllib2.URLError:
                print("Couldn't download web page. Skipping.", file=sys.stderr)
                break
            except urllib2.httplib.BadStatusLine:
                print("BadStatusLine. Retrying...", file=sys.stderr)

        if not video_page:
            continue

        try:
            match = re.search(video_re, video_page)
            video_json = json.loads(match.groupdict()['video_json'])
            video_dict = video_json['talks'][0]
        except AttributeError:
            print("Couldn't parse video page for JSON. Skipping.",
                  file=sys.stderr)
            continue

        video_dict['video_id'] = video_id

        tree = html.fromstring(video_page)

        summary_p = tree.xpath("//p[@class='talk-description']")
        if summary_p:
            summary = etree.tostring(summary_p[0], encoding=unicode,
                                     method="text").strip()
            video_dict['summary'] = summary
        else:
            print("Couldn't parse video page for summary.", file=sys.stderr)

        tags_a = tree.xpath("//ul[@class='talk-topics__list']//a")
        if tags_a:
            tags = [tag.text.strip() for tag in tags_a]
            video_dict['tags'] = tags
        else:
            print("Couldn't parse video page for tags.", file=sys.stderr)

        ted_videos.append(video_dict)

    with open("ted-scrape.json", "w") as f:
        json.dump(ted_videos, f, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='tedtalks.eu downloader'
    )
    parser.add_argument(
        '-o', '--overwrite',
        action='store_true',
        help='overwrite previously downloaded talks (only affects talks ' \
             'present in the RSS feed)'
    )

    args = parser.parse_args()
    if args.overwrite:
        main(overwrite=True)
    else:
        main()

