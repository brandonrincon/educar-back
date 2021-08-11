import sqlite3
import uuid
import io
import csv

from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, Response
from flask import g

app = Flask(__name__)
DATABASE = './database.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    return db


def generar_pin(string_length=10):
    random = str(uuid.uuid4())
    random = random.upper()
    random = random.replace("-", "")
    return random[0:string_length]


def generar_pin_grado(grado, colegio_id, grados):
    for i in range(grado["estudiantes"]):
        fila = {
            "pin": generar_pin(),
            "grado": grado["grado"],
            "curso": grado["curso"],
            "colegio": colegio_id
        }
        insertar_pin_db(fila)
        grados.append(fila)


def insertar_pin_db(content):
    db = get_db()
    try:
        db.execute(
            'insert into pin (pin,grado,curso,colegio) values (?,?,?,?)',
            (
                content['pin'],
                content['grado'],
                content['curso'],
                content['colegio'],
            )
        )
        db.commit()
    except:
        db.rollback()
    finally:
        return


def convertir_csv(grados):
    output = io.StringIO()
    writer = csv.writer(output)
    header = ['PIN, GRADO, CURSO, COLEGIO']
    writer.writerow(header)
    for row in grados:
        line = [row['pin'] + ','
                + row['grado'] + ','
                + row['curso'] + ','
                + row['colegio']
                ]
        writer.writerow(line)
    output.seek(0)
    return output


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


@app.route('/usuario/store', methods=['POST'])
def registrarUsuario():
    db = get_db()
    content = request.json
    clave = content['clave']
    clave = generate_password_hash(clave)
    try:
        db.execute(
            "insert into usuario (nombre,apellido,correo,clave,pin,activo,colegio,curso,grado)values(?,?,?,?,?,?,?,?,?)",
            (
                content['nombre'],
                content['apellido'],
                content['correo'],
                clave,
                content['pin'],
                True,
                content['colegio'],
                content['curso'],
                content['grado'],
            )
        )
        db.commit()
    except:
        db.rollback()
        return Response("Error de Creación", status=500, mimetype='application/json')
    finally:
        return Response("Usuario Creado", status=201, mimetype='application/json')


@app.route('/usuario/login', methods=['POST'])
def loginEstudiante():
    db = get_db()
    content = request.json
    clave = content['clave']
    try:
        cur = db.execute(
            "select * from usuario where correo=?",
            [content['correo']]
        )
        rv = cur.fetchone()

        if rv is None:
            return Response("Usuario no registrado", status=403, mimetype='application/json')
        if check_password_hash(rv['clave'], clave):
            if rv["activo"] == 1:
                return jsonify({
                    'nombre': rv["nombre"],
                    'apellido': rv["apellido"],
                    'pin': rv["pin"],
                    'activo': rv["activo"],
                    'colegio': rv["colegio"],
                    'curso': rv["curso"],
                    'grado': rv["grado"],
                })
            return Response("Usuario inactivo", status=403, mimetype='application/json')
        return Response("Usuario o contraseña incorrectas", status=403, mimetype='application/json')
    except:
        db.rollback()
        return Response("Error de Login", status=500, mimetype='application/json')


@app.route('/usuario', methods=['GET'])
def listado_estudiantes():
    db = get_db()
    content = request.json
    db = get_db()
    cur = db.execute(
        'select activo,apellido,correo,curso, grado,id,nombre,pin from usuario'
    )
    cur = cur.fetchall()
    return jsonify(cur)


@app.route('/usuario/active', methods=['PUT'])
def usuario_active():
    db = get_db()
    content = request.json
    try:
        db.execute(
            "update usuario set activo=? where id=?",
            [content['activo'], content['id']]
        )
        db.commit()
        return Response("Actualizacion realizada", status=200, mimetype='application/json')
    except:
        db.rollback()
        return Response("Error de Actualizacion", status=500, mimetype='application/json')


@app.route('/colegio/listado', methods=['POST'])
def listado_colegio():
    content = request.json
    colegio_id = content["colegio"]
    grados = list()
    for grado in content["grados"]:
        generar_pin_grado(grado, colegio_id, grados)
    return Response(convertir_csv(grados),
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=listado.csv"})


@app.route('/pin/<pin>', methods=['GET'])
def consultar_pin(pin):
    db = get_db()
    try:
        cur = db.execute(
            '''select pin.*,c.nombre as nombre_colegio from pin
                join colegio c on pin.colegio = c.id
                where pin.pin=?''',
            (
                pin,
            )
        )
        rv = cur.fetchone()
        if rv is None:
            return Response("Sin resultados", status=201, mimetype='application/json')
        return jsonify({
            'pin': rv["pin"],
            'grado': rv["grado"],
            'curso': rv["curso"],
            'colegio': rv["colegio"],
            'nombre_colegio': rv["nombre_colegio"],
        })
    except:
        db.rollback()
        return Response("Error de consulta", status=500, mimetype='application/json')


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
