# AFIP Nuestra Parte Extractor - Versión Windows

Herramienta con interfaz gráfica para Windows que automatiza la extracción de información de la sección "Nuestra Parte" del sitio web de AFIP (Administración Federal de Ingresos Públicos de Argentina).

## Descripción

Esta versión para Windows de AFIP Nuestra Parte Extractor ofrece una interfaz gráfica amigable para:
- Seleccionar archivos CSV con contribuyentes
- Extraer información fiscal de la sección "Nuestra Parte" de AFIP
- Visualizar y organizar los resultados

## Requisitos

- Windows 10 o superior
- Python 3.7 o superior
- Google Chrome instalado
- Conexión a Internet

## Instalación

```powershell
# Clonar el repositorio o descargar los archivos
git clone https://github.com/username/afip-nuestra-parte.git
cd afip-nuestra-parte/windows

# Activar el entorno virtual
.\win_env\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

```powershell
# Activar el entorno virtual
.\win_env\Scripts\activate

# Ejecutar la aplicación
python src\main.py
```

Alternativamente, puede ejecutar directamente el archivo `start_afip_extractor.bat` haciendo doble clic en él.

## Estructura del archivo CSV

El programa utiliza un archivo CSV con tres columnas en el siguiente orden:

```
Contribuyente,CUIT,Clave Fiscal
"Juan Perez","20123456789","clave123"
```

El archivo es procesado de la siguiente manera:
- **Primera columna**: Nombre del contribuyente
- **Segunda columna**: CUIT (debe contener solo dígitos)
- **Tercera columna**: Clave fiscal para acceder al portal de AFIP

### Validaciones

El programa realiza las siguientes validaciones al leer el archivo CSV:
- Verifica que cada fila tenga al menos 3 columnas
- Elimina espacios en blanco y saltos de línea en todos los campos
- Valida que el CUIT contenga solo dígitos y tenga 11 dígitos
- Si el CUIT tiene 10 dígitos, se le agrega un 0 al inicio
- Si el CUIT tiene más de 11 dígitos, se trunca a 11
- Ignora filas con nombres vacíos, CUIT inválidos o claves fiscales vacías

## Seguridad

- Las credenciales de AFIP se utilizan únicamente para iniciar sesión y no se almacenan de forma permanente
- Todo el procesamiento se realiza localmente en la máquina del usuario
- No se envía información a servidores externos 