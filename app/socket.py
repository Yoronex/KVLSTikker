from app import app, socketio, stats, spotify
from flask_socketio import emit


@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my response', {'data': 'Connected'})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')


@socketio.on('spotify', namespace='/test')
def update_spotify_request():
    if spotify.sp is not None:
        emit('spotify update', {'data': spotify.current_playback(), 'logged in': True})
    else:
        emit('spotify update', {'logged in': False})


def send_transaction(message):
    socketio.emit('transaction', {'message': message}, namespace='/test')
