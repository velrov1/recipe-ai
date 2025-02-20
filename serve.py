from waitress import serve
from app import app

if __name__ == '__main__':
    # You can change the host to '0.0.0.0' to make it accessible from other devices on your network
    serve(app, host='0.0.0.0', port=8080)
