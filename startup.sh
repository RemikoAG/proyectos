#!/bin/bash

# Dar permisos de ejecución al binario wkhtmltopdf si está en la raíz del proyecto
chmod 755 ./wkhtmltopdf

# Exportar la ruta del ejecutable para que pdfkit lo encuentre
export PATH=$PATH:/home/site/wwwroot

# Ejecutar la aplicación con gunicorn
gunicorn app:app --bind=0.0.0.0 --timeout 300
