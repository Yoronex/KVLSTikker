from app import app
from spotipy import Spotify, oauth2, SpotifyException
from flask import render_template, redirect, url_for, flash
import os
import wget
from datetime import datetime


spotify_token = None
sp = None
current_user = ""
currently_playing_id = ""
CACHE = app.config['SPOTIPY_CACHE']
sp_oauth = oauth2.SpotifyOAuth(app.config['SPOTIPY_CLIENT_ID'], app.config['SPOTIPY_CLIENT_SECRET'],
                               app.config['SPOTIPY_REDIRECT_URI'], scope=app.config['SPOTIPY_SCOPE'], cache_path=CACHE)
history = []

def logout():
    global sp, current_user
    sp = None
    current_user = ""

    #if os.path.exists(CACHE):
    #    os.remove(CACHE)


def set_cache(cache):
    global CACHE, sp_oauth
    CACHE = cache
    sp_oauth = oauth2.SpotifyOAuth(app.config['SPOTIPY_CLIENT_ID'], app.config['SPOTIPY_CLIENT_SECRET'],
                               app.config['SPOTIPY_REDIRECT_URI'], scope=app.config['SPOTIPY_SCOPE'], cache_path=CACHE)
    return


def login(request):
    global sp, current_user
    access_token = ""

    token_info = sp_oauth.get_cached_token()

    if token_info:
        # print("Found cached token!")
        access_token = token_info['access_token']
    else:
        url = request.url
        code = sp_oauth.parse_response_code(url)
        if code:
            # print("Found Spotify auth code in Request URL! Trying to get valid access token...")
            token_info = sp_oauth.get_access_token(code)
            access_token = token_info['access_token']

    if access_token:
        # print("Access token available! Trying to get user information...")
        sp = Spotify(access_token)
        results = sp.current_user()
        current_user = results['display_name']
        flash("Ingelogd op Spotify als {}".format(results['display_name']), "success")
        return redirect(url_for('bigscreen'))

    else:
        return redirect(sp_oauth.get_authorize_url())


def me():
    return sp.current_user()


def renew():
    global sp

    token_info = sp_oauth.get_cached_token()

    if token_info:
        # Retieve token from memory
        access_token = token_info['access_token']
        # Log in again at Spotify
        sp = Spotify(access_token)
        return True
    else:
        # Logout if this is not possible
        logout()
        return False


def current_playback():
    global sp, current_user, currently_playing_id, history

    if sp is None:
        return None

    #  Sometimes throws "spotipy.client.SpotifyException The access token expired"
    try:
        results = sp.current_playback()
    except SpotifyException:
        # Spotify has probably logged out, so we need to log in again
        print("SpotifyException caught!")
        if renew() is False:
            print("Had to log out :(")
            return None
        else:
            print("Successfully relogged!")

        # Retry getting information from Spotify
        try:
            results = sp.current_playback()
        except SpotifyException:
            logout()
            return

    if results is None:
        return results

    if results['currently_playing_type'] == "track":
        # If the album cover has not been downloaded yet, download it
        if results['item']['album']['id'] + ".jpg" not in os.listdir(app.config['ALBUM_COVER_FOLDER']):
            wget.download(results['item']['album']['images'][1]["url"],
                          app.config['ALBUM_COVER_FOLDER'] + "/" + results['item']['album']['id'] + ".jpg")

        # If the currently playing track is not equal to the track we are playing now and if we are a quarter on the
        # track...
        if results['item']['id'] != currently_playing_id and (results['progress_ms'] / results['item']['duration_ms'] > 0.25):
            # Change the currently playing track
            currently_playing_id = results['item']['id']
            # Get all the artist from the track
            artist = ""
            for a in results['item']['artists']:
                artist += a['name']
                artist += ', '
            artist = artist[:-2]
            # Add this track to the history
            history.insert(0, {'title': results['item']['name'],
                               'artist': artist,
                               'end-time': datetime.now()})
            # If we now have more than 10 tracks in history, remove the last one so we have at most 10 tracks.
            if len(history) > 10:
                del history[-1]
        # If the track equals the current track, then change the end time of the track (because we are still playing it)
        elif results['item']['id'] == currently_playing_id:
            history[0]['end-time'] = datetime.now()

    print(results)
    return results
