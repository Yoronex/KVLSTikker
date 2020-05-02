from app import spotify, socketio, dbhandler, emailhandler
from app.routes import *


def shutdown_server():
    spotify.logout()
    socketio.stop()


@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    check_if_local_machine()
    check_if_not_view_only()

    if request.args.get('emails') == 'True':
        if dbhandler.overview_emails:
            emailhandler.send_overview_emails()
        elif dbhandler.debt_emails:
            emailhandler.send_debt_emails()
    shutdown_server()
    app.logger.info('Tikker shutting down')
    return render_template('error.html', title="Tikker wordt afgesloten...", h1="Uitschakelen",
                           message="Tikker wordt nu afgesloten. Je kan dit venster sluiten.", gif_url="")


@app.route('/error/403')
def show_401():
    message = "Je bezoekt Tikker niet vanaf de computer waar Tikker op is geïnstalleerd. Je hebt daarom geen toegang tot deze pagina."
    gif = url_for('.static', filename='img/403.mp4')
    return render_template('error.html', title="403", h1="Error 403", message=message, gif_url=gif), 403


@app.route('/error/404')
def show_404():
    message = "Deze pagina bestaat (nog) niet! Klik op het KVLS logo links om terug te gaan naar het hoofdmenu."
    gif = url_for('.static', filename='img/404.mp4')
    return render_template('error.html', title="404", h1="Error 404", message=message, gif_url=gif), 404


@app.route('/error/500')
def show_500():
    message = "Achter de schermen is iets helemaal fout gegaan! Om dit probleem in de toekomst niet meer te zien, stuur aub berichtje naar Roy met wat je aan het doen was in Tikker toen deze foutmelding verscheen, zodat hij opgelost kan worden!"
    gif = url_for('.static', filename='img/500.mp4')
    return render_template('error.html', title="500", h1="Error 500", message=message, gif_url=gif), 500


@app.errorhandler(403)
def no_access_error(error):
    if app.config['VIEW_ONLY']:
        message = "Tikker staat in View-only modus. daarom kun je deze pagina niet bezoeken."
    else:
        message = "Je bezoekt Tikker niet vanaf de computer waar Tikker op is geïnstalleerd. Je hebt daarom geen toegang tot deze pagina."
    gif = url_for('.static', filename='img/403.mp4')
    return render_template('error.html', title="403", h1="Error 403", message=message, gif_url=gif), 403


@app.errorhandler(404)
def not_found_error(error):
    message = "Deze pagina bestaat (nog) niet! Klik op het KVLS logo links om terug te gaan naar het hoofdmenu."
    gif = url_for('.static', filename='img/404.mp4')
    return render_template('error.html', title="404", h1="Error 404", message=message, gif_url=gif), 404


@app.errorhandler(500)
def exception_error(error):
    message = "Achter de schermen is iets helemaal fout gegaan! Om dit probleem in de toekomst niet meer te zien, stuur aub berichtje naar Roy met wat je aan het doen was in Tikker toen deze foutmelding verscheen, zodat hij opgelost kan worden!"
    gif = url_for('.static', filename='img/500.mp4')
    dbhandler.rollback()
    return render_template('error.html', title="500", h1="Error 500", message=message, gif_url=gif), 500


@app.route("/api/ping")
def server_status():
    return jsonify({"pong": "pong"})
