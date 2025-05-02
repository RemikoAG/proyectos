#!/bin/bash

# Dar permisos de ejecución al binario wkhtmltopdf
chmod 755 /home/site/wwwroot/wkhtmltopdf

# Agregar la ruta al PATH
export PATH=$PATH:/home/site/wwwroot

# Iniciar la aplicación
gunicorn app:app --bind=0.0.0.0 --timeout 300
