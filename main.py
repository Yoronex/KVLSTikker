from app import app, socketio
import sys

if __name__ == '__main__':
    if '-v' in sys.argv:
        app.config['VIEW_ONLY'] = True
        app.logger.info('Tikker starts in view-only mode. Tikker BigScreen is unavailable and it is not possible to '
                        'edit the database, either by adding, changing or deleting data.')
        app.run(host='0.0.0.0')
    else:
        socketio.run(app, host='0.0.0.0')
