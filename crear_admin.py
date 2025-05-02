import pyodbc
import bcrypt

# Conexión a tu base de datos
conexion = pyodbc.connect(
    "DRIVER={SQL Server};SERVER=DESKTOP-IS2KC0A\\SQLEXPRESS;DATABASE=cotizacion;Trusted_Connection=yes"
)
cursor = conexion.cursor()

# Datos del administrador
idusuario = 'admin'
nombres = 'Administrador'
apellidos = 'General'
contrasena = 'admin123'
rol = 'admin'

# Encriptar la contraseña
contrasena_hash = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Verificar si el admin ya existe
cursor.execute("SELECT * FROM usuarios WHERE idusuario = ?", idusuario)
existe = cursor.fetchone()

if existe:
    print("❌ El usuario 'admin' ya existe.")
else:
    cursor.execute("""
        INSERT INTO usuarios (idusuario, nombres, apellidos, contrasena_hash, rol)
        VALUES (?, ?, ?, ?, ?)
    """, idusuario, nombres, apellidos, contrasena_hash, rol)
    conexion.commit()
    print("✅ Usuario 'admin' creado correctamente.")

cursor.close()
conexion.close()
