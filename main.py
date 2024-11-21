from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from PIL import Image, ImageDraw, ImageFont
from barcode import Code128
from barcode.writer import ImageWriter
import aiohttp
import io
import os
from azure.storage.blob import BlobServiceClient, ContentSettings
import asyncio
import logging
import time

# Configuración de FastAPI
app = FastAPI()

# Configuración general
TEMPLATE_PATH = "template/plantilla2.png"
FONT_BOLD_PATH = "font/Poppins-Bold.ttf"
FONT_REGULAR_PATH = "font/Poppins-Regular.ttf"
FECHA_SUFRA = "03 de Diciembre del 2024"
BLOB_ACCOUNT_URL = "https://votacionesalmacenamiento.blob.core.windows.net/"
CONTAINER_NAME = "certificados"
SAS_TOKEN = "sp=racwl&st=2024-11-16T22:36:04Z&se=2025-11-17T23:00:00Z&spr=https&sv=2022-11-02&sr=c&sig=yrGG5iaE7vwIwK3f5WDsd8obOP6aNyLKt%2FktAUBKEMY%3D"

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("CertificateAPI")

# Deshabilitar logs del SKD de Azure
azure_logger = logging.getLogger("azure")
azure_logger.setLevel(logging.WARNING)

# Modelo de datos
class CertificateData(BaseModel):
    numeracion: str
    nombre: str
    identificacion: str
    carrera: str
    rol: str


# Descargar plantilla desde la URL
async def fetch_image_from_url(url: str) -> Image:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise HTTPException(status_code=500, detail="Error al descargar la plantilla.")
            content = await response.read()
            return Image.open(io.BytesIO(content))


# Generar código de barras
def generate_barcode(data: str) -> Image:
    writer = ImageWriter()
    barcode_instance = Code128(data, writer=writer)
    buffer = io.BytesIO()
    options = {'write_text': False}
    barcode_instance.write(buffer, options)
    buffer.seek(0)
    return Image.open(buffer)


# Subir imagen al Blob Storage
async def upload_to_azure_blob(image_data: bytes, blob_name: str) -> str:
    try:
        blob_service_client = BlobServiceClient(account_url=BLOB_ACCOUNT_URL, credential=SAS_TOKEN)
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        blob_client = container_client.get_blob_client(blob=blob_name)
        content_settings = ContentSettings(content_type='image/png')
        blob_client.upload_blob(image_data, overwrite=True, content_settings=content_settings)
        return blob_client.url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir la imagen: {str(e)}")


# Procesar un certificado individual
async def process_certificate(data: CertificateData, template: Image, font_bold, font_regular) -> dict:
    try:
        start_time = time.time()
        logger.info(f"Iniciando proceso para identificación: {data.identificacion}")

        # Copiar plantilla
        template_copy = template.copy()
        draw = ImageDraw.Draw(template_copy)

        # Coordenadas de textos generales
        text_positions = {
            "numeracion": (1600, 245),
            "nombre": (90, 500),
            "identificacion": (90, 710),
            "fecha": (90, 1220),
            "rol": (1480, 1000),
        }

        # Dibujar textos generales
        for key, position in text_positions.items():
            text = FECHA_SUFRA if key == "fecha" else getattr(data, key)
            font = font_regular if key not in ['numeracion', 'rol'] else font_bold
            color = "black" if key not in ['numeracion', 'rol'] else "#3185D6"
            draw.text(position, text, font=font, fill=color)

        # Manejo del texto "carrera"
        carrera = data.carrera
        carrera_primary_position = (90, 925)
        carrera_secondary_position = (90, 1000)

        max_width = 900
        lines = []
        current_line = ""
        for word in carrera.split():
            test_line = f"{current_line} {word}".strip()
            text_bbox = draw.textbbox((0, 0), test_line, font=font_regular)
            text_width = text_bbox[2] - text_bbox[0]
            if text_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        draw.text(carrera_primary_position, lines[0], font=font_regular, fill="black")
        if len(lines) > 1:
            draw.text(carrera_secondary_position, lines[1], font=font_regular, fill="black")

        # Generar código de barras
        barcode_image = generate_barcode(data.identificacion).resize((450, 150))
        barcode_position = (1400, 1100)
        template_copy.paste(barcode_image, barcode_position)

        logger.info(f"Certificado generado para identificación: {data.identificacion} en {time.time() - start_time:.2f} segundos")

        # Guardar imagen en memoria
        image_bytes = io.BytesIO()
        template_copy.save(image_bytes, format='PNG')
        image_bytes.seek(0)

        # Subir al Blob Storage
        upload_start_time = time.time()
        blob_name = f"Certificado_{data.identificacion}.png"
        blob_url = await upload_to_azure_blob(image_bytes.getvalue(), blob_name)
        logger.info(f"Subida de certificado completa para {data.identificacion} en {time.time() - upload_start_time:.2f} segundos")
        logger.info(f"URL lista para identificación {data.identificacion}: {blob_url}")

        return {"identificacion": data.identificacion, "url": blob_url}

    except Exception as e:
        logger.error(f"Error al procesar identificación {data.identificacion}: {e}")
        return {"identificacion": data.identificacion, "error": str(e)}


# Endpoint para generar certificados
@app.post("/api/generateCertificate")
async def generate_certificates(data_list: List[CertificateData]):
    try:
        logger.info(f"Procesando un lote de {len(data_list)} certificados.")

        # Descargar plantilla y fuentes
        template = await fetch_image_from_url(TEMPLATE_PATH)
        font_bold = ImageFont.truetype(FONT_BOLD_PATH, 50)
        font_regular = ImageFont.truetype(FONT_REGULAR_PATH, 50)

        # Procesar cada certificado concurrentemente
        tasks = [process_certificate(data, template, font_bold, font_regular) for data in data_list]
        results = await asyncio.gather(*tasks)

        logger.info("Proceso de generación y subida completado.")
        return JSONResponse(content={"results": results}, status_code=200)

    except Exception as e:
        logger.error(f"Error general en el proceso: {e}")
        raise HTTPException(status_code=500, detail=str(e))
