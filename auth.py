from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import bcrypt
from sqlalchemy import create_engine, text
import os

# Creamos el Blueprint
auth_bp = Blueprint('auth', __name__)

# Conexión a la base de datos
connection_string = os.environ["AZURE_SQL_CONNECTION"]
engine = create_engine(connection_string)

# 🔹 Ruta de Login
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        idusuario = request.form['idusuario'].strip()
        contrasena = request.form['contrasena'].strip()

        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT idusuario, contrasena_hash, rol, activo, fecha_reactivacion
                    FROM usuarios WHERE idusuario = :idusuario
                """),
                {"idusuario": idusuario}
            )
            usuario = result.fetchone()

        if usuario:
            activo = usuario[3]
            if activo == 0:
                flash("⚠️ Tu cuenta ha sido desactivada. Contacta al administrador.", "warning")
                return redirect(url_for('auth.login'))

            contrasena_hash = usuario[1]
            if bcrypt.checkpw(contrasena.encode('utf-8'), contrasena_hash.encode('utf-8')):
                session['idusuario'] = usuario[0]
                session['rol'] = usuario[2]
                session['fecha_reactivacion'] = usuario[4].strftime('%Y-%m-%d %H:%M:%S') if usuario[4] else None

                flash(f"Bienvenido {usuario[0]}.", "success")
                return redirect(url_for('admin_panel' if usuario[2] == 'admin' else 'cotizacion'))
            else:
                flash("❌ Contraseña incorrecta.", "danger")
        else:
            flash("❌ Usuario no encontrado.", "danger")

    return render_template('login.html')

# 🔹 Ruta de Logout
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for('auth.login'))

# 🔹 Ruta para registrar usuario (solo admin)
@auth_bp.route('/admin/registrar_usuario', methods=['GET', 'POST'])
def registrar_usuario():
    if 'idusuario' not in session or session.get('rol') != 'admin':
        flash("Acceso restringido al administrador.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        idusuario = request.form['idusuario'].strip()
        nombres = request.form['nombres'].strip()
        apellidos = request.form['apellidos'].strip()
        contrasena = request.form['contrasena'].strip()
        confirmar_contrasena = request.form['confirmar_contrasena'].strip()
        rol = request.form['rol']

        # Validar que no haya campos vacíos
        if not all([idusuario, nombres, apellidos, contrasena, confirmar_contrasena, rol]):
            flash("⚠️ Todos los campos son obligatorios.", "warning")
            return redirect(url_for('auth.registrar_usuario'))

        # Validar contraseñas
        if contrasena != confirmar_contrasena:
            flash("❌ Las contraseñas no coinciden.", "danger")
            return redirect(url_for('auth.registrar_usuario'))

        from sqlalchemy import text
        with engine.begin() as conn:
            # Validar duplicado
            result = conn.execute(
                text("SELECT idusuario FROM usuarios WHERE idusuario = :idusuario"),
                {"idusuario": idusuario}
            )
            if result.fetchone():
                flash("❌ El ID de usuario ya existe.", "danger")
                return redirect(url_for('auth.registrar_usuario'))

            # Encriptar contraseña
            contrasena_hash = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Insertar usuario
            conn.execute(
                text("""
                    INSERT INTO usuarios (idusuario, nombres, apellidos, contrasena_hash, rol, activo, fecha_reactivacion)
                    VALUES (:idusuario, :nombres, :apellidos, :contrasena_hash, :rol, 1, GETDATE())
                """),
                {
                    "idusuario": idusuario,
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "contrasena_hash": contrasena_hash,
                    "rol": rol
                }
            )

        flash(f"✅ Usuario '{idusuario}' registrado correctamente.", "success")
        return redirect(url_for('gestionar_usuarios'))

    return render_template('registro_usuario.html')
