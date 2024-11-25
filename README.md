
# API para Generación de Certificados

## Descripción

Esta API permite generar certificados personalizados en formato de imagen. Cada certificado incluye información proporcionada por el usuario (nombre, rol, identificación, carrera y numeración), además de un código de barras único. Los certificados generados se suben automáticamente a un contenedor en Azure Blob Storage, y la API devuelve la URL pública para cada certificado.

---

## Requisitos

- **Python**: 3.8 o superior
- **Paquetes necesarios** (se instalan con `pip install -r requirements.txt`):
  - `fastapi`
  - `pydantic`
  - `Pillow`
  - `python-barcode`
  - `azure-storage-blob`
  - `aiohttp`

---

## Configuración

### Archivos necesarios

1. **Plantilla del certificado**: Coloca el archivo `plantilla.png` en el directorio `template/`.
2. **Fuentes**:
   - Fuente negrita: `Poppins-Bold.ttf` (directorio `font/`).
   - Fuente regular: `Poppins-Regular.ttf` (directorio `font/`).

---

## Uso

### Ejecución

Ejecuta la aplicación en local con:

```bash
uvicorn main:app --reload
```

Para acceder desde otras computadoras en tu red local, utiliza la IP local de tu máquina. Ejemplo:

```bash
uvicorn main:app --host 192.168.1.100 --port 8000
```

### Endpoint

#### `POST /api/generateCertificate`

**Descripción**: Genera certificados a partir de un lote de datos proporcionado y devuelve las URLs de los certificados generados.

---

### Request Body

El cuerpo de la solicitud debe ser un JSON con una lista de objetos que contengan los siguientes campos:

| Campo           | Tipo   | Requerido | Descripción                                   |
|------------------|--------|-----------|-----------------------------------------------|
| `numeracion`     | string | Sí        | Número único del certificado                  |
| `nombre`         | string | Sí        | Nombre del destinatario del certificado       |
| `identificacion` | string | Sí        | Número de identificación del destinatario     |
| `carrera`        | string | Sí        | Carrera o especialidad                        |
| `rol`            | string | Sí        | Rol o título del destinatario                 |

**Ejemplo de solicitud**:

```json
[
  {
    "numeracion": "001",
    "nombre": "Juan Pérez",
    "identificacion": "1234567890",
    "carrera": "Ingeniería de Software",
    "rol": "Estudiante"
  },
  {
    "numeracion": "002",
    "nombre": "María López",
    "identificacion": "0987654321",
    "carrera": "Ciencias de Datos",
    "rol": "Profesora"
  }
]
```

---

### Respuesta

**Código 200**: Devuelve las URLs públicas de los certificados generados.

**Ejemplo de respuesta**:

```json
{
  "results": [
    {
      "identificacion": "1234567890",
      "url": "https://votacionesalmacenamiento.blob.core.windows.net/certificados/Certificado_1234567890.png"
    },
    {
      "identificacion": "0987654321",
      "url": "https://votacionesalmacenamiento.blob.core.windows.net/certificados/Certificado_0987654321.png"
    }
  ]
}
```

**Código 500**: Error general en el procesamiento de uno o más certificados.

**Ejemplo de error**:

```json
{
  "detail": "Error al cargar recursos: No se encontró la plantilla en la ruta: template/plantilla.png"
}
```

---

## Funcionamiento

### Flujo

1. **Inicio**:
   - La API carga la plantilla (`plantilla.png`) y las fuentes al iniciar el servidor.

2. **Procesamiento**:
   - Cada certificado se genera en memoria utilizando:
     - La plantilla como fondo.
     - Los datos del usuario para dibujar textos.
     - Un código de barras único generado con la identificación del usuario.

3. **Subida**:
   - Los certificados se suben automáticamente a un contenedor de Azure Blob Storage.

4. **Respuesta**:
   - La API devuelve una URL pública para cada certificado generado.

---

## Personalización

### Ajustar el diseño del certificado

1. **Modificar posiciones de texto**:
   - Edita el diccionario `text_positions` en la función `process_certificate`.

2. **Cambiar tamaño del código de barras**:
   - Modifica el método `resize` en `generate_barcode`.

3. **Cambiar ubicación del código de barras**:
   - Ajusta las coordenadas de `barcode_position` en `process_certificate`.

---

## Seguridad

1. **SAS Token**: Mantén el token de acceso seguro (`SAS_TOKEN`). Este permite subir archivos a Azure Blob Storage.
2. **Reglas de firewall**: Limita el acceso al contenedor en Azure para evitar accesos no autorizados.

---

## Logs

Los logs detallan cada paso del proceso, incluyendo:

- Inicio y fin del procesamiento por identificación.
- Tiempo de generación y subida.
- URL generada para cada certificado.

Logs típicos:

```plaintext
2024-11-24 12:00:00 - Plantilla cargada correctamente.
2024-11-24 12:00:01 - Fuentes cargadas correctamente.
2024-11-24 12:00:10 - Iniciando proceso para identificación: 1234567890
2024-11-24 12:00:12 - Certificado generado para identificación: 1234567890 en 2.00 segundos
2024-11-24 12:00:15 - Subida de certificado completa para 1234567890 en 3.00 segundos
2024-11-24 12:00:15 - URL lista para identificación 1234567890: https://votacionesalmacenamiento.blob.core.windows.net/certificados/Certificado_1234567890.png
```

---

## Notas adicionales

- **Despliegue en red local**:
  Usa `--host 0.0.0.0` para que otros dispositivos de tu red puedan acceder a la API.
- **Depuración**:
  Activa más detalles en los logs cambiando el nivel de logs a `DEBUG` en `logging.basicConfig`.

---
