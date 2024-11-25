from flask import Flask, render_template, request, redirect, url_for, jsonify
from pyzbar.pyzbar import decode
import cv2
import base64
import numpy as np
from datetime import datetime
import pyodbc

app = Flask(__name__)

# Conexión a SQL Server
connection_string = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=DESKTOP-7IUAS0R\\SQLEXPRESS;DATABASE=carrosISI;UID=saa;PWD=12345'
)

def registrar_salida_regreso(qr_code, nombre_tecnico, ultimo_mantenimiento, accion):
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        try:
            ultimo_mantenimiento_dt = datetime.fromisoformat(ultimo_mantenimiento)
        except ValueError as e:
            print(f"Formato de fecha incorrecto en 'ultimo_mantenimiento': {e}")
            return False

        print(f"Registrando con QR code: {qr_code}, Acción: {accion}")

        query_select = "SELECT id, salida, regreso FROM RegistrosAutos WHERE qr_code = ?"
        cursor.execute(query_select, (qr_code,))
        registro_existente = cursor.fetchone()

        if registro_existente:
            if accion == "Salida":
                query_update = "UPDATE RegistrosAutos SET salida = ?, nombre_tecnico = ?, ultimo_mantenimiento = ? WHERE qr_code = ?"
                cursor.execute(query_update, (datetime.now(), nombre_tecnico, ultimo_mantenimiento_dt, qr_code))
            elif accion == "Regreso":
                query_update = "UPDATE RegistrosAutos SET regreso = ?, nombre_tecnico = ?, ultimo_mantenimiento = ? WHERE qr_code = ?"
                cursor.execute(query_update, (datetime.now(), nombre_tecnico, ultimo_mantenimiento_dt, qr_code))
        else:
            if accion == "Salida":
                query_insert = "INSERT INTO RegistrosAutos (qr_code, nombre_tecnico, ultimo_mantenimiento, salida) VALUES (?, ?, ?, ?)"
                cursor.execute(query_insert, (qr_code, nombre_tecnico, ultimo_mantenimiento_dt, datetime.now()))
            else:
                print(f"No se puede registrar regreso sin salida para QR: {qr_code}")
                return False

        conn.commit()
        print("Datos guardados correctamente")
        return True
    except pyodbc.DatabaseError as e:
        print(f"Error de base de datos en registrar_salida_regreso: {e}")
        return False
    except Exception as e:
        print(f"Error general en registrar_salida_regreso: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    registros = []
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query_view = "SELECT TOP (1000) [id], [qr_code], [nombre_tecnico], [ultimo_mantenimiento], [salida], [regreso] FROM [carrosISI].[dbo].[RegistrosAutos]"
        cursor.execute(query_view)
        registros = cursor.fetchall()
    except Exception as e:
        print(f"Error al conectar o consultar la base de datos en index: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

    if request.method == 'POST':
        nombre_tecnico = request.form['nombre_tecnico']
        ultimo_mantenimiento = request.form['ultimo_mantenimiento']
        qr_data = request.form['qr_data']
        accion = request.form['accion']

        print(f"Datos recibidos para registrar: QR Code: {qr_data}, Persona: {nombre_tecnico}, Mantenimiento: {ultimo_mantenimiento}, Acción: {accion}")

        if qr_data and registrar_salida_regreso(qr_data, nombre_tecnico, ultimo_mantenimiento, accion):
            return redirect(url_for('confirmacion', qr_data=qr_data, nombre_tecnico=nombre_tecnico, accion=accion))
        else:
            print("Error en el registro. Datos: ", qr_data, nombre_tecnico, ultimo_mantenimiento, accion)
            return "Error en el registro"

    return render_template('index.html', registros=registros)

@app.route('/lista')
def lista():
    registros = []
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query_view = "SELECT id, qr_code, nombre_tecnico, ultimo_mantenimiento, salida, regreso FROM RegistrosAutos"
        cursor.execute(query_view)
        registros = cursor.fetchall()
        print("Registros obtenidos:", registros)
    except Exception as e:
        print(f"Error al conectar o consultar la base de datos en lista: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

    return render_template('lista.html', registros=registros)

@app.route('/confirmacion')
def confirmacion():
    qr_data = request.args.get('qr_data')
    nombre_tecnico = request.args.get('nombre_tecnico')
    accion = request.args.get('accion')
    return render_template('confirmacion.html', qr_data=qr_data, nombre_tecnico=nombre_tecnico, accion=accion)

@app.route('/escaneo_qr', methods=['POST'])
def escaneo_qr():
    data = request.json
    image_base64 = data['image']
    qr_data = procesar_imagen_qr(image_base64)

    if qr_data:
        return jsonify({'success': True, 'qr_data': qr_data})
    else:
        return jsonify({'success': False, 'message': 'No se detectó ningún QR'})

def procesar_imagen_qr(image_base64):
    image_data = base64.b64decode(image_base64)
    np_arr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    decoded_objects = decode(img)
    for obj in decoded_objects:
        qr_data = obj.data.decode('utf-8')
        return qr_data
    return None

@app.route('/verificar_qr', methods=['POST'])
def verificar_qr():
    data = request.json
    qr_code = data['qr_data']
    
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query = "SELECT nombre_tecnico, ultimo_mantenimiento FROM RegistrosAutos WHERE qr_code = ?"
        cursor.execute(query, (qr_code,))
        resultado = cursor.fetchone()

        if resultado:
            nombre_tecnico, ultimo_mantenimiento = resultado
            return jsonify({
                'exists': True,
                'nombre_tecnico': nombre_tecnico,
                'ultimo_mantenimiento': ultimo_mantenimiento.isoformat() if ultimo_mantenimiento else None
            })
        else:
            return jsonify({'exists': False})

    except Exception as e:
        print(f"Error al verificar QR en la base de datos: {e}")
        return jsonify({'error': 'Error al verificar QR'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/checklist', methods=['GET', 'POST'])
def checklist():
    if request.method == 'POST':
        numero_coche = request.form['numero_coche']
        kilometraje = request.form['kilometraje']
        
        # Create a dictionary with all the new checklist fields
        campos = ['luces', 'antena', 'espejo_derecho', 'espejo_izquierdo', 'cristales', 'emblema', 'llantas', 
                  'tapon_gasolina', 'carroceria_sin_golpes', 'claxon', 'instrumentos_tablero', 'clima', 
                  'limpiadores', 'bocinas', 'espejo_retrovisor', 'cinturones', 'botones_interiores', 
                  'manijas_interiores', 'tapetes', 'vestiduras', 'gato', 'maneral_gato', 'llave_ruedas', 
                  'refacciones', 'herramientas', 'extintor', 'aceite', 'anticongelante', 'liquido_frenos', 
                  'tarjeta_circulacion', 'papeles_seguro', 'licencia_vigente']
        
        valores = {campo: request.form.get(campo, '0') == '1' for campo in campos}
        
        try:
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()
            
            # Build the SQL query dynamically
            campos_sql = ', '.join(campos)
            placeholders = ', '.join(['?' for _ in campos])
            
            query = f"""
            IF EXISTS (SELECT 1 FROM CheckListAutos WHERE numero_coche = ?)
                UPDATE CheckListAutos 
                SET kilometraje = ?, {', '.join([f'{campo} = ?' for campo in campos])}
                WHERE numero_coche = ?
            ELSE
                INSERT INTO CheckListAutos (numero_coche, kilometraje, {campos_sql})
                VALUES (?, ?, {placeholders})
            """
            
            # Prepare the values for the query
            update_values = [numero_coche, kilometraje] + [valores[campo] for campo in campos] + [numero_coche]
            insert_values = [numero_coche, kilometraje] + [valores[campo] for campo in campos]
            
            cursor.execute(query, update_values + insert_values)
            conn.commit()
            return redirect(url_for('checklist', message="Checklist actualizado correctamente"))
        except Exception as e:
            print(f"Error al actualizar el checklist: {e}")
            return redirect(url_for('checklist', error="Error al actualizar el checklist"))
        finally:
            if 'conn' in locals():
                conn.close()
    
    coches = []
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        query = "SELECT numero_coche FROM CheckListAutos"
        cursor.execute(query)
        coches = [row.numero_coche for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error al obtener la lista de coches: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    return render_template('checklist.html', coches=coches, message=request.args.get('message'), error=request.args.get('error'))

@app.route('/get_car_details/<string:numero_coche>')
def get_car_details(numero_coche):
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        query = """
        SELECT numero_coche, kilometraje, luces, antena, espejo_derecho, espejo_izquierdo, 
               cristales, emblema, llantas, tapon_gasolina, carroceria_sin_golpes, claxon, 
               instrumentos_tablero, clima, limpiadores, bocinas, espejo_retrovisor, 
               cinturones, botones_interiores, manijas_interiores, tapetes, vestiduras, 
               gato, maneral_gato, llave_ruedas, refacciones, herramientas, extintor, 
               aceite, anticongelante, liquido_frenos, tarjeta_circulacion, papeles_seguro, 
               licencia_vigente, ultima_actualizacion 
        FROM CheckListAutos 
        WHERE numero_coche = ?
        """
        cursor.execute(query, (numero_coche,))
        car = cursor.fetchone()
        if car:
            return jsonify({
                "numero_coche": car.numero_coche,
                "kilometraje": car.kilometraje or "",
                "luces": bool(car.luces),
                "antena": bool(car.antena),
                "espejo_derecho": bool(car.espejo_derecho),
                "espejo_izquierdo": bool(car.espejo_izquierdo),
                "cristales": bool(car.cristales),
                "emblema": bool(car.emblema),
                "llantas": bool(car.llantas),
                "tapon_gasolina": bool(car.tapon_gasolina),
                "carroceria_sin_golpes": bool(car.carroceria_sin_golpes),
                "claxon": bool(car.claxon),
                "instrumentos_tablero": bool(car.instrumentos_tablero),
                "clima": bool(car.clima),
                "limpiadores": bool(car.limpiadores),
                "bocinas": bool(car.bocinas),
                "espejo_retrovisor": bool(car.espejo_retrovisor),
                "cinturones": bool(car.cinturones),
                "botones_interiores": bool(car.botones_interiores),
                "manijas_interiores": bool(car.manijas_interiores),
                "tapetes": bool(car.tapetes),
                "vestiduras": bool(car.vestiduras),
                "gato": bool(car.gato),
                "maneral_gato": bool(car.maneral_gato),
                "llave_ruedas": bool(car.llave_ruedas),
                "refacciones": bool(car.refacciones),
                "herramientas": bool(car.herramientas),
                "extintor": bool(car.extintor),
                "aceite": bool(car.aceite),
                "anticongelante": bool(car.anticongelante),
                "liquido_frenos": bool(car.liquido_frenos),
                "tarjeta_circulacion": bool(car.tarjeta_circulacion),
                "papeles_seguro": bool(car.papeles_seguro),
                "licencia_vigente": bool(car.licencia_vigente),
                "ultima_actualizacion": car.ultima_actualizacion.isoformat() if car.ultima_actualizacion else ""
            })
        else:
            return jsonify({"error": "Coche no encontrado"}), 404
    except Exception as e:
        print(f"Error al obtener detalles del coche: {e}")
        return jsonify({"error": "Error al obtener detalles del coche"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(port=1433)