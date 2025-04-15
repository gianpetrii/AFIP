# AFIP Nuestra Parte Extractor

Herramienta que automatiza la extracción de información de la sección "Nuestra Parte" del sitio web de AFIP (Administración Federal de Ingresos Públicos de Argentina).

## Descripción

AFIP Nuestra Parte Extractor es una herramienta simplificada que se enfoca específicamente en extraer información de la sección "Nuestra Parte" del portal de AFIP. Esta sección muestra detalles importantes sobre la situación fiscal del contribuyente.

La herramienta:
- Inicia sesión automáticamente en el portal de AFIP
- Navega directamente a la sección "Nuestra Parte"
- Captura capturas de pantalla completas de la información
- Organiza los resultados por contribuyente en carpetas separadas

## Requisitos

- Python 3.7 o superior
- Google Chrome instalado
- Conexión a Internet
- Sistema operativo Windows, Linux o macOS
- Chromedriver compatible con su versión de Chrome

## Instalación

```bash
# Clonar el repositorio o descargar los archivos
git clone https://github.com/username/afip-nuestra-parte.git
cd afip-nuestra-parte

# Crear entorno virtual
python -m venv venv

# Activar el entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Estructura del archivo de entrada

El programa utiliza un archivo CSV (`clientes.csv`) con el siguiente formato:

```
nombre,cuit,clave_fiscal
"Nombre Apellido","20123456789","contraseña"
```

Cada línea debe contener:
- **nombre**: Nombre completo del contribuyente (se usará para crear la carpeta)
- **cuit**: CUIT sin guiones
- **clave_fiscal**: Clave fiscal para acceder al portal de AFIP

Si no dispone del archivo, el programa creará automáticamente un archivo de ejemplo (`clientes_ejemplo.csv`) que puede editar con sus datos.

## Uso

### Ejecución básica

```bash
python afip_extractor.py
```

### Opciones avanzadas

```bash
# Especificar año a procesar
python afip_extractor.py --year 2023

# Especificar archivo CSV
python afip_extractor.py --file mi_archivo.csv

# Ver ayuda
python afip_extractor.py --help
```

## Resultados

Los resultados se guardan en la carpeta "Resultados", organizados de la siguiente manera:

```
Resultados/
  ├── Nombre del Contribuyente/
  │    └── Nuestra_Parte_[año]_[timestamp]/
  │         ├── captura_01.png
  │         ├── captura_02.png
  │         └── ...
  └── ...
```

## Seguridad

- Las credenciales de AFIP se utilizan únicamente para iniciar sesión y no se almacenan de forma permanente
- Todo el procesamiento se realiza localmente en la máquina del usuario
- No se envía información a servidores externos

## Solución de problemas

### Errores de inicio de sesión

- Verifique que las credenciales sean correctas en el archivo CSV
- Asegúrese de que el contribuyente tenga acceso con clave fiscal nivel 3 o superior
- Revise los archivos de log generados durante la ejecución

### Errores de navegación

- Verifique su conexión a Internet
- Asegúrese de que Chrome esté actualizado
- Compruebe que el chromedriver sea compatible con su versión de Chrome
- Verifique las capturas de pantalla generadas en la carpeta Resultados

### Archivos de log

El programa genera logs detallados en el archivo `afip_extractor.log` que pueden ayudar a diagnosticar problemas.

## Actualización desde versiones anteriores

Si viene de una versión anterior:

1. El formato de archivo principal ahora es CSV en lugar de TXT
2. La columna "clave" ahora se llama "clave_fiscal" para mayor claridad
3. El programa puede convertir automáticamente formatos de archivo antiguos

Para convertir un archivo TXT antiguo a CSV:

```python
from csv_utils import CSVHandler
CSVHandler.convertir_txt_a_csv("ruta_al_archivo.txt", "nuevo_archivo.csv")
``` 