from app import app, socketio

#app.run(host='0.0.0.0')
if __name__ == '__main__':
    # socketio.run(app, debug=True)
    socketio.run(app, host='0.0.0.0')
    # app.run(debug=True)