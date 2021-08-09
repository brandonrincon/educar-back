import sqlite3
from flask import Flask, request, jsonify, Response
from flask import g

app = Flask(__name__)
DATABASE = './database.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.route('/')
def infoApi():
    return jsonify("Api Educar")


@app.route('/colegio/store', methods=['POST'])
def store_colegio():
    db = get_db()
    content = request.json
    try:
        db.execute(
            'insert into colegio (nombre,direccion,ciudad,fecha_vencimiento) values (?,?,?,?)',
            (
                content['nombre'],
                content['direccion'],
                content['ciudad'],
                content['fecha_vencimiento'],
            )
        )
        db.commit()
    except:
        db.rollback()
        return Response("Error de Creación", status=500, mimetype='application/json')
    finally:
        return Response("Colegio Creado", status=201, mimetype='application/json')


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS, PUT, DELETE"
    response.headers[
        "Access-Control-Allow-Headers"] = "Accept, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization"
    return response


if __name__ == '__main__':
    app.run()
