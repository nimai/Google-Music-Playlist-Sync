#!/usr/bin/env python

# Copyright (c) 2012, Simon Weber
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of the contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from os import path
from getpass import getpass
from xml.etree.ElementTree import parse
from gmusicapi.api import Api


def init():
    api = Api() 
    
    logged_in = False
    attempts = 0

    while not logged_in and attempts < 3:
        email = raw_input("Email: ")
        password = getpass()

        print "Logging in..."
        logged_in = api.login(email, password)
        if not logged_in:
            print "Log in failed."
        attempts += 1

    return api


def parse_xml(l_pl_path):
    # Parse the playlist XML file
    l_pl = parse(l_pl_path).getroot()

    # Get the list of tracks in the playlists
    l_tracks_elems = l_pl.find("{http://xspf.org/ns/0/}trackList")
    if l_tracks_elems is None:
        print "Error: Malformed or empty playlist."
        exit(1)

    # Convert the XML elements to a dict
    l_tracks = []
    for l_track in l_tracks_elems:
        track = {}
        for field in l_track:
            if field.tag == "{http://xspf.org/ns/0/}title":
                track['title'] = field.text.strip()
            elif field.tag == "{http://xspf.org/ns/0/}creator":
                track['artist'] = field.text.strip()
            elif field.tag == "{http://xspf.org/ns/0/}album":
                track['album'] = field.text.strip()
            elif field.tag == "{http://xspf.org/ns/0/}location":
                track['path'] = field.text.strip()
        l_tracks.append(track)

    return l_tracks


def main():
    # Log in to Google Music
    api = init()

    if not api.is_authenticated():
        print "Sorry, those credentials weren't accepted."
        return

    print "Successfully logged in."

    # Get the playlist file to use
    l_pl_path = raw_input("Path to playlist file: ")

    # Get the filename. This will be used as the playlist name.
    l_pl_name, l_pl_type = path.splitext(l_pl_path)

    # Check that the file extension is xspf
    if l_pl_type != ".xspf":
        print "Error: Playlist must be XSPF format."
        api.logout()
        exit(1);

    # Parse the playlist
    l_tracks = parse_xml(l_pl_path)

    # Check that the playlist has tracks in it
    if len(l_tracks) == 0:
        print "Error: Playlist is empty."
        api.logout
        exit(1)

    # Get all available playlists from Google Music
    r_pls = api.get_all_playlist_ids(False, False)

    # Try to find the playlist if it already exists
    r_pl_id = None
    r_pl_items = r_pls['user'].items()
    for i in range(len(r_pl_items)):
        if r_pl_items[i][0] == l_pl_name:
            # Check if there are multiple playlists with that name
            if type(r_pl_items[i][1]) is list:
                # TODO: Handle multiple playlists with the same name
                print "Found multiple playlists with that name. Defaulting to the first one."
                r_pl_id = r_pl_items[i][1][0]
            else:
                r_pl_id = r_pl_items[i][1]
            print "Found playlist with ID: " + r_pl_id
            break

    # If the playlist wasn't found, create it
    if r_pl_id is None:
        print "Playlist not found on Google Music. Creating it."
        r_pl_id = api.create_playlist(l_pl_name)

    # Get the songs on the playlist
    r_tracks = api.get_playlist_songs(r_pl_id)

    # Get all songs in the library
    r_library = api.get_all_songs()

    # Check if each track in the local playlist is on the Google Music playlist
    for l_track in l_tracks:
        added = False
        # Check if the track is already present in the playlist
        for r_track in r_tracks:
            if l_track['title'] == r_track['title'] and l_track['artist'] == r_track['artist'] and l_track['album'] == r_track['artist']:
                print "Track: \"" + l_track['title'] + "\" already added to playlist."
                added = True
                break

        # Add the track to the playlist
        if not added:
            # Find the song ID
            l_track_id = None
            for r_track in r_library:
                if l_track['title'] == r_track['title'] and l_track['artist'] == r_track['artist'] and l_track['album'] == r_track['album']:
                    l_track_id = r_track['id']
                    break

            # Check if the song wasn't found in the library
            if l_track_id == None:
                print "Error: Track \"" + l_track['title'] + "\" not found in library."
                continue

            # Finally, add the new track to the playlist
            api.add_songs_to_playlist(r_pl_id, l_track_id)
            print "Added track \"" + l_track['title'] + "\" to playlist."

    # Be a good citizen and log out
    api.logout()
    print "All done!"
    exit(0)


if __name__ == '__main__':
    main()