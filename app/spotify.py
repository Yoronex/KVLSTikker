from app import app
from spotipy import Spotify, oauth2, SpotifyException
from flask import render_template, redirect, url_for, flash
import os
import wget


spotify_token = None
sp = None
current_user = ""
SPOTIPY_CLIENT_ID = 'e81cc50c967a4c64a8073d678f7b6503'
SPOTIPY_CLIENT_SECRET = 'c8d84aec8a6d4197b5eca4991ba7694b'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:5000/spotifylogin'
SCOPE = 'user-read-playback-state user-modify-playback-state user-read-currently-playing'
CACHE = '.spotipyoauthcache'
sp_oauth = oauth2.SpotifyOAuth(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE, cache_path=CACHE)


def logout():
    global sp, current_user
    sp = None
    current_user = ""

    if os.path.exists(CACHE):
        os.remove(CACHE)


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
        return redirect(url_for('index'))

    else:
        return redirect(sp_oauth.get_authorize_url())


def renew():
    global sp

    token_info = sp_oauth.get_cached_token()

    if token_info:
        # print("Found cached token!")
        access_token = token_info['access_token']
        sp = Spotify(access_token)
        return True
    else:
        logout()
        return False


def current_playback():
    global sp, current_user

    if sp is None:
        return None

    #  Sometimes throws "spotipy.client.SpotifyException The access token expired"
    try:
        results = sp.current_playback()
    except SpotifyException:
        print("SpotifyException caught!")
        if renew() is False:
            print("Had to log out :(")
            return None
        else:
            print("Successfully relogged!")

    try:
        results = sp.current_playback()
    except SpotifyException:
        logout()
        return

    if results is None:
        return results

    if results['item']['album']['id'] + ".jpg" not in os.listdir(app.config['ALBUM_COVER_FOLDER']):
        wget.download(results['item']['album']['images'][0]["url"],
                      app.config['ALBUM_COVER_FOLDER'] + "/" + results['item']['album']['id'] + ".jpg")

    return results
