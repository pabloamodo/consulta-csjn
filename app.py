"""
Aplicación web para consultar el estado de una cédula
----------------------------------------------------

Esta aplicación utiliza Flask para exponer una interfaz web sencilla en la
que el usuario introduce el número del código de barras y, al pulsar
"Consultar", se ejecuta la función `consulta_cedula` del módulo
`consulta_cedula`.  El resultado se muestra en la misma página y, si
existe una base de datos MySQL configurada, se guarda automáticamente
en una tabla.

Antes de ejecutar la aplicación debes instalar las dependencias:

.. code-block:: bash

    pip3 install flask mysql-connector-python selenium webdriver-manager beautifulsoup4

La configuración de la base de datos se lee de variables de entorno
(`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` y `DB_TABLE`).  Si
cualquiera de estas variables falta, el guardado en base de datos se
omitirá.

Para desplegar en Hostinger o cualquier servicio con soporte WSGI,
puedes crear un entorno virtual, instalar las dependencias, y configurar
Flask mediante un archivo `wsgi.py` o el propio `app.py`.

Autor: ChatGPT (OpenAI)
Fecha: diciembre de 2025
"""

import os
from flask import Flask, render_template, request, flash, redirect, url_for
import logging

from consulta_cedula import consulta_cedula

try:
    import mysql.connector  # type: ignore
except ImportError:
    mysql = None  # type: ignore

# Configurar logging básico
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
# Debes establecer una clave secreta en producción
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "cambia_esta_clave")


def guardar_en_bd(datos: dict) -> None:
    """
    Guarda el resultado de la consulta en una base de datos MySQL si la
    configuración está disponible.  El nombre de la tabla se toma de
    `DB_TABLE` o por defecto 'cedulas'.

    Parameters
    ----------
    datos : dict
        Diccionario con las claves esperadas: codigo_de_barras, fuero,
        juzgado, zona, fecha_ingreso, fecha_asignacion_zona,
        fecha_devolucion, resultado_diligencia, fecha_disposicion_juzgado.
    """
    # Comprueba que mysql-connector esté disponible
    if mysql is None:
        logging.warning("mysql-connector-python no está instalado. Datos no guardados.")
        return
    cfg = {
        'host': os.environ.get('DB_HOST'),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'database': os.environ.get('DB_NAME'),
    }
    # Si falta alguna clave de configuración, salta el guardado
    if not all(cfg.values()):
        logging.info("Variables de entorno de DB incompletas. Datos no guardados.")
        return
    tabla = os.environ.get('DB_TABLE', 'cedulas')
    try:
        conn = mysql.connector.connect(**cfg)  # type: ignore
        cursor = conn.cursor()
        # Asegura que la tabla exista (puedes ajustarla según tu esquema)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {tabla} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                codigo_de_barras VARCHAR(20) NOT NULL,
                fuero VARCHAR(10),
                juzgado VARCHAR(10),
                zona VARCHAR(10),
                fecha_ingreso VARCHAR(20),
                fecha_asignacion_zona VARCHAR(20),
                fecha_devolucion VARCHAR(20),
                resultado_diligencia VARCHAR(20),
                fecha_disposicion_juzgado VARCHAR(20),
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        insert_sql = f"""
            INSERT INTO {tabla} (codigo_de_barras, fuero, juzgado, zona,
                                 fecha_ingreso, fecha_asignacion_zona,
                                 fecha_devolucion, resultado_diligencia,
                                 fecha_disposicion_juzgado)
            VALUES (%(codigo_de_barras)s, %(fuero)s, %(juzgado)s, %(zona)s,
                    %(fecha_ingreso)s, %(fecha_asignacion_zona)s,
                    %(fecha_devolucion)s, %(resultado_diligencia)s,
                    %(fecha_disposicion_juzgado)s)
        """
        cursor.execute(insert_sql, datos)
        conn.commit()
        logging.info("Registro guardado en base de datos.")
    except Exception as exc:
        logging.error(f"Error guardando en la base de datos: {exc}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    """Página principal con formulario de consulta."""
    resultado = None
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip()
        if not codigo:
            flash('Debe ingresar un número de código de barras.', 'error')
        else:
            # Ejecuta la consulta en modo headless para producción
            try:
                estado = consulta_cedula(codigo, headless=True, timeout=60)
                resultado = estado.to_dict()
                guardar_en_bd(resultado)
            except Exception as exc:
                logging.exception("Error al consultar la cédula")
                flash(f'Error al consultar la cédula: {exc}', 'error')
    return render_template('index.html', resultado=resultado)


if __name__ == '__main__':
    # Ejecuta la aplicación en desarrollo.  En producción se usa un servidor WSGI
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)