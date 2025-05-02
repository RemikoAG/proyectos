from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import bcrypt
import pyodbc

# Creamos el Blueprint
auth_bp = Blueprint('auth', __name__)

# Conexión a la base de datos
conexion = pyodbc.connect(
    "DRIVER={SQL Server};SERVER=DESKTOP-IS2KC0A\\SQLEXPRESS;DATABASE=cotizacion;Trusted_Connection=yes"
)

# 🔹 Ruta de Login
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        idusuario = request.form['idusuario'].strip()
        contrasena = request.form['contrasena'].strip()

        cursor = conexion.cursor()
        cursor.execute("""
            SELECT idusuario, contrasena_hash, rol, activo, fecha_reactivacion
            FROM usuarios WHERE idusuario = ?
        """, (idusuario,))
        usuario = cursor.fetchone()

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

        # Validar duplicado
        cursor = conexion.cursor()
        cursor.execute("SELECT idusuario FROM usuarios WHERE idusuario = ?", (idusuario,))
        if cursor.fetchone():
            flash("❌ El ID de usuario ya existe.", "danger")
            return redirect(url_for('auth.registrar_usuario'))

        # Encriptar contraseña
        contrasena_hash = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insertar en la base de datos
        cursor.execute("""
            INSERT INTO usuarios (idusuario, nombres, apellidos, contrasena_hash, rol, activo, fecha_reactivacion)
            VALUES (?, ?, ?, ?, ?, 1, GETDATE())
        """, (idusuario, nombres, apellidos, contrasena_hash, rol))
        conexion.commit()

        flash(f"✅ Usuario '{idusuario}' registrado correctamente.", "success")
        return redirect(url_for('gestionar_usuarios'))

    return render_template('registro_usuario.html')
