from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, abort, jsonify
from flask_breadcrumbs import register_breadcrumb

from app import stats, socket, spotify, dbhandler, cart
from app.forms import *
from app.models import *
from app.routes import get_usergroups_with_users


@register_breadcrumb(app, '.admin.bigscreen', 'BigScreen', order=2)
@app.route("/admin/bigscreen", methods=['GET', 'POST'])
def bigscreen():
    form_quote = AddQuoteForm()
    form_interrupt = SlideInterruptForm()
    form_spotify = ChooseSpotifyUser()

    if len(dbhandler.biertje_kwartiertje_participants) > 0:
        bk = {'playing': True,
              'participants': [User.query.get(x['user_id']) for x in dbhandler.biertje_kwartiertje_participants],
              'drink': Product.query.get(dbhandler.biertje_kwartiertje_drink).name,
              'playtime': dbhandler.biertje_kwartiertje_time}
    else:
        bk = {'playing': False}

    if form_quote.submit_quote.data and form_quote.validate_on_submit():
        alert = dbhandler.addquote(form_quote.quote.data, form_quote.author.data)
        flash(alert[0], alert[1])

        return redirect(url_for('bigscreen'))
    if form_interrupt.submit_interrupt.data and form_interrupt.validate_on_submit():
        socket.send_interrupt({"name": "Message", "data": form_interrupt.interrupt.data})

        return redirect(url_for('bigscreen'))

    if form_spotify.spotify_submit.data and form_spotify.validate_on_submit():
        if form_spotify.spotify_user.data != '0':
            spotify.set_cache(os.path.join(app.config['SPOTIFY_CACHE_FOLDER'],
                                           '.spotifyoauthcache-' + form_spotify.spotify_user.data))
            return redirect(url_for('api_spotify_login'))
        elif form_spotify.spotify_user.data == "0" and form_spotify.spotify_user_name.data != "":
            spotify.set_cache(os.path.join(app.config['SPOTIFY_CACHE_FOLDER'],
                                           '.spotifyoauthcache-' + form_spotify.spotify_user_name.data))
            return redirect(url_for('api_spotify_login'))

    return render_template('admin/bigscreen.html', title="BigScreen Beheer", h1="BigScreen Beheer",
                           form_quote=form_quote, bk=bk,
                           form_interrupt=form_interrupt, form_spotify=form_spotify,
                           spusername=spotify.current_user), 200


@register_breadcrumb(app, '.admin.bigscreen.quotes', 'Quotes', order=3)
@app.route('/admin/bigscreen/quotes', methods=['GET'])
def admin_quotes():
    if request.remote_addr != "127.0.0.1":
        abort(403)

    if 'all' in request.args:
        quotes = Quote.query.all()
        all_quotes = True
    else:
        quotes = Quote.query.filter(Quote.approved == False).all()
        all_quotes = False

    return render_template('admin/manquotes.html', title="Citaatbeheer", h1="Citaatbeheer", quotes=quotes,
                           all_quotes=all_quotes)


@register_breadcrumb(app, '.admin.bigscreen.quotes.confirm', 'Bevestigen', order=4)
@app.route('/admin/bigscreen/quotes/delete/<int:q_id>')
def admin_quotes_delete(q_id):
    if request.remote_addr != "127.0.0.1":
        abort(403)

    q = Quote.query.get(q_id)
    message = 'quote met ID {} ({}) door {}'.format(str(q.id), q.value, q.author)
    agree_url = url_for('admin_quotes_delete_exec', q_id=q_id)
    return_url = url_for('admin_quotes')
    return render_template('verify.html', title='Bevestigen', message=message, agree_url=agree_url,
                           return_url=return_url)


@app.route('/admin/bigscreen/quotes/delete/<int:q_id>/exec')
def admin_quotes_delete_exec(q_id):
    if request.remote_addr != "127.0.0.1":
        abort(403)

    alert = dbhandler.del_quote(q_id)
    flash(alert[0], alert[1])
    return redirect(url_for('admin_quotes'))


@app.route('/admin/bigscreen/quotes/approve/<int:q_id>')
def admin_quotes_approve(q_id):
    if request.remote_addr != "127.0.0.1":
        abort(403)

    alert = dbhandler.approve_quote(q_id)
    flash(alert[0], alert[1])
    return redirect(url_for('admin_quotes'))


@register_breadcrumb(app, '.admin.bigscreen.bk', 'Biertje Kwartiertje', order=3)
@app.route("/admin/bigscreen/biertjekwartiertje")
def biertje_kwartiertje():
    usergroups = get_usergroups_with_users()
    dinnerid = dbhandler.settings['dinner_product_id']
    products = Product.query.filter(and_(Product.purchaseable == True, Product.id != dinnerid)).all()

    drink = Product.query.get(1)

    already_playing = []
    for i in dbhandler.biertje_kwartiertje_participants:
        for j in range(0, i['amount']):
            already_playing.append({'id': i['user_id'], 'name': User.query.get(i['user_id']).name})

    if len(dbhandler.biertje_kwartiertje_participants) > 0:
        playtime = dbhandler.biertje_kwartiertje_time
    else:
        playtime = 15

    return render_template('admin/biertjekwartiertje.html', title="Biertje Kwartiertje",
                           h1="Biertje kwartiertje instellen", drink=drink, usergroups=usergroups, shared=False,
                           User=User, products=products, already_playing=already_playing, playtime=playtime), 200


@app.route("/admin/bigscreen/biertjekwartiertje/<cart_string>")
def start_biertje_kwartiertje(cart_string):
    old_participants = dbhandler.biertje_kwartiertje_participants
    parsed_cart = cart.parse_cart_string(cart_string, -1)
    dbhandler.biertje_kwartiertje_participants = parsed_cart['orders']

    if len(dbhandler.biertje_kwartiertje_participants) > 0:
        dbhandler.biertje_kwartiertje_time = int(request.args['time'])
        dbhandler.biertje_kwartiertje_drink = int(request.args['drink'])
        # If biertje kwartiertje has not started yet, we need to update it on BigScreen
        if len(old_participants) == 0:
            # Start biertje kwartiertje (aka update it with the time)
            socket.update_biertje_kwartiertje()
    else:
        stop_biertje_kwartiertje()

    return redirect(url_for("bigscreen"))


@app.route("/admin/bigscreen/biertjekwartiertje/stop")
def stop_biertje_kwartiertje():
    dbhandler.biertje_kwartiertje_participants = []
    dbhandler.biertje_kwartiertje_time = 0
    dbhandler.biertje_kwartiertje_drink = -1
    socket.stop_biertje_kwartiertje()
    return redirect(url_for("bigscreen"))


@app.route("/admin/bigscreen/biertjekwartiertje/update")
def update_biertje_kwartiertje():
    socket.update_biertje_kwartiertje()
    return redirect(url_for("bigscreen"))


@app.route('/admin/bigscreen/fireplace')
def bigscreen_toggle_fireplace():
    socket.toggle_fireplace()
    return redirect(url_for('bigscreen'))


@app.route("/api/spotify/login")
def api_spotify_login():
    return spotify.login(request)


@app.route('/api/spotify/logout')
def api_spotify_logout():
    current_user = spotify.current_user
    spotify.logout()
    flash("Spotify gebruiker {} uitgelogd".format(current_user), "success")
    return redirect(url_for('bigscreen'))


@app.route('/api/spotify/covers/<string:id>')
def api_spotify_get_album_cover(id):
    return render_template(url_for('.static', filename='covers/{}.jpg'.format(id)))


@app.route('/api/spotify/currently_playing')
def api_spotify_currently_playing():
    return jsonify(spotify.current_playback())


@app.route('/api/spotify/me')
def api_spotify_user():
    return jsonify(spotify.me())


@app.route('/api/total_alcohol')
def api_total_alcohol():
    begindate = "2019-09-01"
    enddate = "2019-12-31"
    parsedbegin = datetime.strptime(begindate, "%Y-%m-%d")
    parsedend = datetime.strptime(enddate, "%Y-%m-%d")

    ids, values, labels = stats.most_alcohol_drank_by_users(parsedbegin, parsedend)

    return jsonify({"ids": ids,
                    "values": values,
                    "labels": labels})


@app.route('/api/bigscreen/snow')
def api_disable_snow():
    socket.disable_snow()
    return redirect(url_for('bigscreen'))


@app.route('/api/bigscreen/reload')
def api_reload_bigscreen():
    socket.send_reload()
    return redirect(url_for('bigscreen'))
