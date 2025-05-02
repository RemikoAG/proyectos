# Imagen base de Python con Debian
FROM python:3.10-slim

# Instala dependencias de wkhtmltopdf y el mismo wkhtmltopdf
RUN apt-get update && apt-get install -y \
    libxrender1 libjpeg62-turbo libxext6 libx11-6 wkhtmltopdf \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Establece la carpeta donde se ejecutará todo
WORKDIR /app

# Copia todos tus archivos al contenedor
COPY . .

# Instala las dependencias de tu proyecto
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto para la app
EXPOSE 8000

# Comando para iniciar tu app con gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000", "--timeout", "300"]
