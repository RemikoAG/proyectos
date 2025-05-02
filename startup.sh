#!/bin/bash

# Instalar dependencias para wkhtmltopdf
apt-get update
apt-get install -y fontconfig xfonts-base xfonts-75dpi curl

# Descargar wkhtmltopdf 0.12.6 versión estática (compatible con Azure Linux)
curl -L -o wkhtmltox.tar.xz https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.amd64.tar.xz

# Extraer y mover el ejecutable
tar -xf wkhtmltox.tar.xz
cp wkhtmltox/bin/wkhtmltopdf /usr/local/bin/wkhtmltopdf
chmod +x /usr/local/bin/wkhtmltopdf

# Iniciar tu app Flask con Gunicorn
exec gunicorn app:app
