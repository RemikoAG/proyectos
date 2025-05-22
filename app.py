from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from sqlalchemy import create_engine
from sqlalchemy import text
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from datetime import datetime
import os
import requests
import base64
# Force redeploy - clean build


valores_estimados = {}  # ✅ Inicializar variable global

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'
# 👇 Esto asegura que la sesión no se pierda en HTTPS (como en Azure)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


# ------------------- CONEXIÓN A SQL SERVER -------------------

connection_string = os.environ["AZURE_SQL_CONNECTION"]
engine = create_engine(connection_string)



# ------------------- ENTRENAMIENTO MODELO (por material) -------------------
def entrenar_modelo():
    global valores_estimados, ultima_fecha_entrenamiento
    query = "SELECT idmaterial, preciounitario FROM costos"
    df = pd.read_sql_query(query, engine)

    if df.empty:
        print("⚠️ No hay datos en la tabla costos")
        return False

    valores_estimados = {}
    materiales = df['idmaterial'].unique()

    for idmat in materiales:
        df_material = df[df['idmaterial'] == idmat]
        X = df_material[['idmaterial']]
        y = df_material['preciounitario']

        if len(df_material) < 2:
            print(f"⚠️ No hay suficientes datos para entrenar el modelo de idmaterial {idmat}")
            continue

        X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2, random_state=42)

        modelo = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
        modelo.fit(X_train, y_train)

        predicho = modelo.predict([[idmat]])[0]
        valores_estimados[idmat] = round(predicho, 2)

    print("\n🔍 Valores estimados por Random Forest para cada idmaterial:")
    for idmat, val in valores_estimados.items():
        print(f"  idmaterial {idmat}: S/ {val:.2f}")

    ultima_fecha_entrenamiento = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return True

if not entrenar_modelo():
    raise Exception("No se pudo entrenar el modelo por falta de datos.")


# ------------------- FUNCIONES ÚTILES -------------------
def obtener_entero(valor):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return 0

def asignar_id_material(nombre):
    ids = {
        'acero_columna': 2,         # id 2 = acero
        'acero_viga': 2,

        'cemento_cimentacion': 4,   # id 4 = cemento
        'cemento_muro': 4,
        'cemento_columna': 4,
        'cemento_techo': 4,

        'arena_cimentacion': 6,     # id 6 = arena
        'arena_muro': 6,
        'arena_columna': 6,
        'arena_techo': 6,

        'grava_cimentacion': 5,     # id 5 = grava
        'grava_columna': 5,
        'grava_techo': 5,

        'ladrillo_muro': 1,         # id 1 = ladrillo 18 huecos
        'ladrillo_techo': 3         # id 3 = ladrillo techo hueco
    }
    return ids.get(nombre, 0)


# ------------------- RUTA INICIO -------------------
@app.route('/')
def home():
    return render_template('home.html')

# ------------------- COTIZACIÓN -------------------
@app.route('/cotizacion', methods=['GET', 'POST'])
def cotizacion():
    if 'idusuario' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'GET':
        session['hora_inicio_cotizacion'] = datetime.now()

    materiales_por_etapa = {
        'acero': ['acero_columna'],
        'cimentacion': ['cemento_cimentacion', 'arena_cimentacion', 'grava_cimentacion'],
        'muro': ['cemento_muro', 'ladrillo_muro', 'arena_muro'],
        'columna': ['cemento_columna', 'arena_columna', 'grava_columna'],
        'viga': ['acero_viga', 'ladrillo_techo'],
        'techo': ['cemento_techo', 'arena_techo', 'grava_techo']
    }

    if request.method == 'POST':
        print("\n📨 FORMULARIO RECIBIDO:")
        print(request.form.to_dict())

        datos_ingresados = request.form.to_dict()
        print("📨 Datos recibidos del formulario:")
        print(datos_ingresados)

        costos = {}
        cantidades = {}
        total_general = 0
        al_menos_un_valor = False

        for etapa, materiales in materiales_por_etapa.items():
            campos_llenos = sum(1 for m in materiales if datos_ingresados.get(m, '').strip() != '')
            if 0 < campos_llenos < len(materiales):
                flash(f' Debes completar todos los campos de la etapa: {etapa.capitalize()}', 'warning')
                return render_template('cotizacion.html', datos=datos_ingresados)

        for etapa, materiales in materiales_por_etapa.items():
            for material in materiales:
                valor = datos_ingresados.get(material, '')
                cantidad_entero = obtener_entero(valor)
                if cantidad_entero > 0:
                    al_menos_un_valor = True
                id_material = asignar_id_material(material)
                precio_unitario = valores_estimados.get(id_material, 0)
                costo_estimado = round(precio_unitario * cantidad_entero, 2)
                costos[material] = costo_estimado
                cantidades[material] = cantidad_entero
                total_general += costo_estimado

        if not al_menos_un_valor:
            flash(" Debes llenar al menos una etapa para calcular la cotización.", "warning")
            return render_template('cotizacion.html', datos=datos_ingresados)

                        # Cálculo de costos por etapa (para tabla y gráfico)
        costos_etapas = []
        for etapa, materiales in materiales_por_etapa.items():
            suma = sum(costos.get(m, 0) for m in materiales)
            costos_etapas.append(round(suma, 2))

        costos_etapas = [float(x) for x in costos_etapas]  # 🔧 FIX JSON para Jinja

        print("\n🧾 Detalle de costos estimados por material:")
        for material in costos:
            print(f"  {material}: cantidad = {cantidades[material]}, estimado = S/ {costos[material]}")

        print(f"\n📊 Costos por etapa para el gráfico: {costos_etapas}")
        print(f"💰 Total general: S/ {total_general}")

        return render_template(
            'resultado.html',
            costos=costos,
            cantidades=cantidades,
            total=round(total_general, 2),
            costos_etapas=costos_etapas
        )
    
    return render_template('cotizacion.html', datos={})

# ------------------- GUARDAR COTIZACIÓN -------------------
@app.route('/guardar_cotizacion', methods=['POST'])
def guardar_cotizacion():
    if 'idusuario' not in session:
        return redirect(url_for('auth.login'))

    idusuario = session['idusuario']
    datos = request.form.to_dict()

    total_general = float(datos.get('total_general', 0))

    materiales_por_etapa = {
        'acero': ['acero_columna'],
        'cimentacion': ['cemento_cimentacion', 'arena_cimentacion', 'grava_cimentacion'],
        'muro': ['cemento_muro', 'ladrillo_muro', 'arena_muro'],
        'columna': ['cemento_columna', 'arena_columna', 'grava_columna'],
        'viga': ['acero_viga', 'ladrillo_techo'],
        'techo': ['cemento_techo', 'arena_techo', 'grava_techo']
    }

    costos = {}
    cantidades = {}
    costos_etapas = []
    total_general = 0

    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO cotizaciones (idusuario, fecha, total_general)
                OUTPUT INSERTED.idcotizacion
                VALUES (:idusuario, GETDATE(), :total_general)
            """),
            {"idusuario": idusuario, "total_general": total_general}
        )
        idcotizacion = result.fetchone()[0]

        for etapa, materiales in materiales_por_etapa.items():
            suma = 0
            for material in materiales:
                cantidad = obtener_entero(datos.get(f'cantidad_{material}', 0))
                costo_estimado = float(datos.get(f'material_{material}', 0))
                mano_obra = float(datos.get(f'mano_obra_' + etapa, 0))
                total_etapa = costo_estimado + mano_obra
                etapa_nombre = etapa.replace("_", " ").title()

                id_material = asignar_id_material(material)  # ✅ Añade esto antes del INSERT
                conn.execute(
                    text("""
                         INSERT INTO detalle_cotizacion (
                         idcotizacion, etapa, material, cantidad,
                         costo_estimado, mano_obra, total_etapa, idmaterial
                         )
                         VALUES (
                         :idcotizacion, :etapa, :material, :cantidad,
                         :costo_estimado, :mano_obra, :total_etapa, :idmaterial
                         )
                         """),
                         {
                             "idcotizacion": idcotizacion,
                             "etapa": etapa_nombre,
                             "material": material,
                             "cantidad": cantidad,
                             "costo_estimado": costo_estimado,
                             "mano_obra": mano_obra,
                             "total_etapa": total_etapa,
                             "idmaterial": id_material  # ✅ Aquí lo pasas
                             }
                             )
                suma += costo_estimado
                costos[material] = costo_estimado
                cantidades[material] = cantidad

            costos_etapas.append(round(suma, 2))
            total_general += suma
# ✅ Enviar datos al resultado.html para re-render y permitir exportar PDF

# Guardar el ID en sesión para que lo use /resultado
        session['cotizacion_guardada'] = True
        session['ultimo_idcotizacion'] = idcotizacion
        hora_inicio = session.get('hora_inicio_cotizacion')
        hora_fin = datetime.now()
        if hora_inicio:
            print(f"➡️ Llamando a función registrar_indicadores para ID {idcotizacion}")
            registrar_indicadores(idcotizacion, hora_inicio, hora_fin)

        else:
            print("⚠️ No se encontró hora de inicio en la sesión.")
        return redirect(url_for('resultado_cotizacion'))



# ------------------- ADMIN PANEL Y FUNCIONES -------------------
@app.route('/admin')
def admin_panel():
    if 'idusuario' not in session or session.get('rol') != 'admin':
        flash("Acceso restringido al administrador.", "warning")
        return redirect(url_for('home'))
    return render_template('admin_panel.html', fecha_entrenamiento=ultima_fecha_entrenamiento)

@app.route('/entrenar_modelo_manual')
def entrenar_manual():
    if 'idusuario' not in session or session.get('rol') != 'admin':
        flash("Solo el administrador puede reentrenar el modelo.", "danger")
        return redirect(url_for('home'))

    if entrenar_modelo():
        flash(" Modelo reentrenado correctamente.", "success")
    else:
        flash("❌ Error al reentrenar el modelo.", "danger")
    return redirect(url_for('admin_panel'))

@app.route('/admin/usuarios')
def gestionar_usuarios():
    if 'idusuario' not in session or session.get('rol') != 'admin':
        flash("Acceso restringido.", "warning")
        return redirect(url_for('home'))

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT idusuario, nombres, apellidos, rol, activo 
            FROM usuarios 
            WHERE idusuario != 'admin'
        """))
        usuarios = result.fetchall()

    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/admin/cambiar_estado/<idusuario>', methods=['POST'])
def cambiar_estado_usuario(idusuario):
    if 'idusuario' not in session or session.get('rol') != 'admin':
        flash("No autorizado.", "danger")
        return redirect(url_for('home'))

    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT activo FROM usuarios WHERE idusuario = :idusuario"),
            {"idusuario": idusuario}
        )
        estado_actual = result.fetchone()

        if estado_actual:
            nuevo_estado = 0 if estado_actual[0] == 1 else 1
            conn.execute(
                text("UPDATE usuarios SET activo = :estado WHERE idusuario = :idusuario"),
                {"estado": nuevo_estado, "idusuario": idusuario}
            )
            flash(f" Estado del usuario '{idusuario}' actualizado correctamente.", "success")
        else:
            flash(" Usuario no encontrado.", "danger")

    return redirect(url_for('gestionar_usuarios'))

@app.route('/historial_cotizaciones')
def historial_cotizaciones():
    if 'idusuario' not in session or session.get('rol') != 'admin':
        flash("Acceso restringido al administrador.", "danger")
        return redirect(url_for('home'))

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT c.idcotizacion, c.fecha, c.total_general,
                   u.nombres + ' ' + u.apellidos AS nombre_completo
            FROM cotizaciones c
            JOIN usuarios u ON c.idusuario = u.idusuario
            ORDER BY c.fecha DESC
        """))
        cotizaciones = result.fetchall()

    return render_template('historial_cotizaciones.html', cotizaciones=cotizaciones)

@app.route('/detalle_cotizacion/<int:idcotizacion>')
def detalle_cotizacion(idcotizacion):
    if 'idusuario' not in session or session.get('rol') != 'admin':
        flash("Acceso restringido.", "danger")
        return redirect(url_for('home'))

    with engine.connect() as conn:
        cabecera = conn.execute(
            text("""
                SELECT c.idcotizacion, c.fecha, c.total_general, u.nombres, u.apellidos, u.idusuario
                FROM cotizaciones c
                JOIN usuarios u ON c.idusuario = u.idusuario
                WHERE c.idcotizacion = :id
            """),
            {"id": idcotizacion}
        ).fetchone()

        if not cabecera:
            flash("Cotización no encontrada.", "warning")
            return redirect(url_for('historial_cotizaciones'))

        detalles = conn.execute(
            text("""
                SELECT etapa, material, cantidad, costo_estimado, mano_obra, total_etapa
                FROM detalle_cotizacion
                WHERE idcotizacion = :id
            """),
            {"id": idcotizacion}
        ).fetchall()

    return render_template('detalle_cotizacion.html', cabecera=cabecera, detalles=detalles)

# ------------------- HISTORIAL Y PDF -------------------
@app.route('/mis_cotizaciones')
def mis_cotizaciones():
    if 'idusuario' not in session or session.get('rol') != 'usuario':
        flash("Acceso restringido.", "danger")
        return redirect(url_for('home'))

    idusuario = session['idusuario']
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT idcotizacion, fecha, total_general
                FROM cotizaciones
                WHERE idusuario = :idusuario
                ORDER BY fecha DESC
            """),
            {"idusuario": idusuario}
        )
        cotizaciones = result.fetchall()

    return render_template('mis_cotizaciones.html', cotizaciones=cotizaciones)

@app.route('/detalle_mi_cotizacion/<int:idcotizacion>')
def detalle_mi_cotizacion(idcotizacion):
    if 'idusuario' not in session or session.get('rol') != 'usuario':
        flash("Acceso restringido.", "danger")
        return redirect(url_for('home'))

    idusuario = session['idusuario']
    with engine.connect() as conn:
        cabecera = conn.execute(
            text("""
                SELECT idcotizacion, fecha, total_general
                FROM cotizaciones
                WHERE idcotizacion = :id AND idusuario = :idusuario
            """),
            {"id": idcotizacion, "idusuario": idusuario}
        ).fetchone()

        if not cabecera:
            flash("Cotización no encontrada.", "warning")
            return redirect(url_for('mis_cotizaciones'))

        detalles = conn.execute(
            text("""
                SELECT etapa, material, cantidad, costo_estimado, mano_obra, total_etapa
                FROM detalle_cotizacion
                WHERE idcotizacion = :id
            """),
            {"id": idcotizacion}
        ).fetchall()

    return render_template('detalle_mi_cotizacion.html', cabecera=cabecera, detalles=detalles)

# ...

@app.route('/descargar_pdf/<int:idcotizacion>')
def descargar_pdf(idcotizacion):
    print("👉 Entrando a /descargar_pdf")
    print("👤 Usuario en sesión:", session.get('idusuario'))
    if 'idusuario' not in session:
        flash("Debes iniciar sesión para descargar.", "danger")
        return redirect(url_for('home'))

    with engine.connect() as conn:
        cabecera = conn.execute(
            text("""
                SELECT c.idcotizacion, c.fecha, c.total_general, u.idusuario, u.nombres, u.apellidos
                FROM cotizaciones c
                JOIN usuarios u ON c.idusuario = u.idusuario
                WHERE c.idcotizacion = :id
            """),
            {"id": idcotizacion}
        ).fetchone()

        detalles = conn.execute(
            text("""
                SELECT etapa, material, cantidad, costo_estimado, mano_obra, total_etapa
                FROM detalle_cotizacion
                WHERE idcotizacion = :id
            """),
            {"id": idcotizacion}
        ).fetchall()

    if not cabecera:
        flash("Cotización no encontrada.", "warning")
        return redirect(url_for('home'))

    # Render HTML del PDF
    html = render_template('cotizacion_pdf.html', cabecera=cabecera, detalles=detalles)

    # Enviar a PDFShift
    api_key = 'sk_5a155314ce9b4bc1e181c641226dcd2d9ff49e68'
    auth_header = base64.b64encode(f'api:{api_key}'.encode()).decode()
    
    response = requests.post(
        'https://api.pdfshift.io/v3/convert/pdf',
        headers={
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/json'
        },
        json={"source": html}
    )


    if response.status_code != 200:
       print("❌ Error al generar PDF:", response.status_code)
       print("🔍 Respuesta:", response.text)
       flash("Error al generar el PDF. Revisa la clave de API o el contenido HTML.", "danger")
       return redirect(url_for('home'))


    # Devolver PDF al navegador
    pdf = response.content
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="Cotizacion_{idcotizacion}.pdf"'

    return response


@app.route('/resultado')
def resultado_cotizacion():
    if 'idusuario' not in session or 'ultimo_idcotizacion' not in session:
        return redirect(url_for('home'))

    idcotizacion = session['ultimo_idcotizacion']
    with engine.connect() as conn:
        detalles = conn.execute(
            text("""
                SELECT etapa, material, cantidad, costo_estimado, mano_obra, total_etapa
                FROM detalle_cotizacion
                WHERE idcotizacion = :id
            """),
            {"id": idcotizacion}
        ).fetchall()

    etapas = ['acero', 'cimentacion', 'muro', 'columna', 'viga', 'techo']
    costos = {}
    cantidades = {}
    totales_materiales_por_etapa = {etapa: 0.0 for etapa in etapas}
    mano_obras = {etapa: 0.0 for etapa in etapas}
    total_general = 0.0

    for d in detalles:
        etapa_key = d.etapa.lower()
        if etapa_key in totales_materiales_por_etapa:
            totales_materiales_por_etapa[etapa_key] += float(d.costo_estimado)
            mano_obras[etapa_key] = float(d.mano_obra)
        costos[d.material] = float(d.costo_estimado)
        cantidades[d.material] = int(d.cantidad)
        total_general += float(d.total_etapa)

    costos_etapas = [round(totales_materiales_por_etapa[etapa], 2) for etapa in etapas]

    return render_template("resultado.html",
                           costos=costos,
                           cantidades=cantidades,
                           total=round(total_general, 2),
                           costos_etapas=costos_etapas,
                           cotizacion_guardada=True,
                           ultimo_idcotizacion=idcotizacion,
                           mano_obras=mano_obras)

# ------------------- REGISTRO DE BLUEPRINT -------------------
from auth import auth_bp
app.register_blueprint(auth_bp)


def registrar_indicadores(idcotizacion, hora_inicio, hora_fin):
    with engine.connect() as conn:
        detalles = conn.execute(
            text("""
                 SELECT dc.material, dc.cantidad, dc.costo_estimado, dc.idmaterial,
                        (SELECT TOP 1 cr.precio_real
                         FROM costos_reales cr
                         WHERE cr.idmaterial = dc.idmaterial
                         ORDER BY cr.idcosto DESC) AS precio_real
                 FROM detalle_cotizacion dc
                 WHERE dc.idcotizacion = :id
            """),
            {"id": idcotizacion}
        ).fetchall()


        estimado_total = 0.0
        real_total = 0.0

        for fila in detalles:
            print(f"🔍 REGISTRO fila => material: {fila.material}, cantidad: {fila.cantidad}, estimado: {fila.costo_estimado}, idmaterial: {fila.idmaterial}, precio_real: {fila.precio_real}")

            cantidad = fila.cantidad
            estimado = fila.costo_estimado
            real_unitario = fila.precio_real or 0  # Evita errores si viene None

            estimado_total += estimado
            real_total += cantidad * real_unitario

        if real_total == 0:
            print("⚠️ No se puede registrar indicadores: total real es 0")
            return

        tiempo = (hora_fin - hora_inicio).total_seconds()
        error = abs(estimado_total - real_total) / real_total * 100
        precision = (1 - abs(estimado_total - real_total) / max(estimado_total, real_total)) * 100
        print(f"➡️ Registrando indicadores para cotización {idcotizacion}")

        conn.execute(
            text("""
                INSERT INTO indicadores_cotizacion (
                    idcotizacion, hora_inicio, hora_fin, tiempo_segundos,
                    estimado_total, real_total, error_porcentual, precision
                ) VALUES (
                    :idcotizacion, :hora_inicio, :hora_fin, :tiempo,
                    :estimado_total, :real_total, :error, :precision
                )
            """),
            {
                "idcotizacion": idcotizacion,
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
                "tiempo": tiempo,
                "estimado_total": estimado_total,
                "real_total": real_total,
                "error": round(error, 2),
                "precision": round(precision, 2)
            }
        )

        print(f"✅ Indicadores registrados para cotización {idcotizacion}")


# ------------------- RUN -------------------
if __name__ == '__main__':
    app.run()
