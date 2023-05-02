from flask import Flask, request, jsonify
from loguru import logger
from database import Database


app = Flask(__name__)
db = Database()


@app.route('/', methods=['POST', 'GET'])
def main():
    """Перехват всех Update Телеграм API"""
    if request.method == 'POST':
        try:
            logger.info('post')
            r = request.get_json()
            return jsonify(r)
        except Exception as e:
            logger.error(e)
            return 'ok'
    else:
        logger.info('get')
        return '<h1>GET</h1>'


if __name__ == '__main__':
    app.run()