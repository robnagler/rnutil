# -*- coding: utf-8 -*-
u"""Manipulate amazon music

:copyright: Copyright (c) 2016 Robert Nagler.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function

import bs4
import csv
import os
from pykern import pkio

def playlist_csv(html):
    """Convert a playlist html to a CSV.

    Replaces html suffix and writes that file

    Args:
        html (str): file to open
    """
    out = html.replace('html', 'csv')
    assert out != html, \
        '{}: file does not end in html'
    soup = bs4.BeautifulSoup(pkio.read_text(html), 'html.parser')
    tracks = {}
    for table in soup.find_all('table'):
        for row in table.find_all('tr', 'playlistDetailsListItem'):
            cell = row.find('td', 'title')
            x = row.find('div', 'numberInner')
            if not x:
                continue
            track = x.contents[0]
            tracks[int(track)] = [
                track,
                cell.contents[0],
                cell.find('span', 'artist').find('span').contents[0],
                cell.find('a', 'albumName').find('span').contents[0],
            ]
    with open(out, 'wb') as f:
        c = csv.writer(f)
        c.writerow(['Track', 'Song', 'Artist', 'Album'])
        for k in sorted(tracks.keys()):
            c.writerow(tracks[k])
    return 'Wrote {}'.format(out)

#s = """<tr class="playlistDetailsListItem" style="height:50px;"><td class="hoverColumn"></td> <td class="selectColumn"><input id="cb_96_f34aaa6e-173c-4b9c-87fe-f82d52209367" type="checkbox" class="listItemSelectCheckbox dragDisabled" name="selectedItems" unselectable="on" value="96_f34aaa6e-173c-4b9c-87fe-f82d52209367"> <label for="cb_96_f34aaa6e-173c-4b9c-87fe-f82d52209367" class="icon-check dragDisabled" unselectable="on"></label></td> <td class="trackNumber"><div class="listViewTrackNumber"><div class="number"><div class="numberInner">97</div></div> <span role="button" tabindex="0" aria-label="Play" class="playButton playerIconPlay"></span></div> </td> <td class="trackAlbumArt"><a class="" aria-label="Changes One" href="/my/albums/Changes+One/CHANGES+ONE/DAVID+BOWIE/LIBRARY/ref=dm_wcp_albm_link_up"><span><div class="albumArtWrapper "><img src="https://album-art-storage-us.s3.amazonaws.com/93fbfe1288031ffd1fb104d244a42c95377960791d681357d2439246d5c09f39_110x110.jpg?response-content-type=image%2Fjpeg&amp;x-amz-security-token=FQoDYXdzEHwaDKbZhBAYL7N%2F6W1G7yKsATQ1MqVvN%2B88O1ZVFE3VneANdnrJwEZrNHBke7jPiP23yUdN0VT3M6IxmeDwrWO0nRSvDVcBvOEO79J2E7%2FekLGhbFccOVtspD4dUmRpxWJ6uA99C5xYLv5fGkm9Uvmjpic3PGoarZl1yD2xfUEnI7hv0wXcDPLbHC9L%2FELE5Vmi0E7aTLB6L09CKZDALldA7rvaSDm%2BOKXBoN94AYNNIoghWj2bTNOt10S%2FZrQozOC9vQU%3D&amp;AWSAccessKeyId=ASIAJN3QTSOVIVNZ2QXQ&amp;Expires=1471232045&amp;Signature=Ixi925OVMOf9vHHCyFR8GOxw6IQ%3D" class="renderImage2" style="opacity: 1;"></div></span></a></td><td class="title">Space Oddity<br> <span class="artist"><a href="/my/artists/David+Bowie/DAVID+BOWIE/LIBRARY/ref=dm_wcp_artist_link_up" title="David Bowie"><span>David Bowie</span></a></span> <span class="albumArtistSeparator">-</span> <a class="albumName" aria-label="" href="/my/albums/Changes+One/CHANGES+ONE/DAVID+BOWIE/LIBRARY/ref=dm_wcp_albm_link_up"><span>Changes One</span></a></td><td class="duration"><div class="listViewDurationContextButton "><div class="listViewDuration">5:17</div> <div role="button" tabindex="0" class="listViewContextButton playerIconDotMenu "></div></div></td> <td class="primeStatus"></td> <td class="hoverColumn"></td> </tr>"""
