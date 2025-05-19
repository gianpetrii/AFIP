# AFIP Nuestra Parte Extractor

Herramienta que automatiza la extracción de información de la sección "Nuestra Parte" del sitio web de AFIP (Administración Federal de Ingresos Públicos de Argentina).

## Nueva estructura del proyecto

Este proyecto ahora se ha reorganizado en dos versiones separadas:

- **Versión Windows**: Interfaz gráfica optimizada para usuarios de Windows
- **Versión Linux**: Interfaz adaptada para entornos Linux

Elija la carpeta correspondiente a su sistema operativo:

- [Versión Windows](./windows/README.md)
- [Versión Linux](./linux/README.md)

## Descripción general

AFIP Nuestra Parte Extractor es una herramienta que se enfoca específicamente en extraer información de la sección "Nuestra Parte" del portal de AFIP. Esta sección muestra detalles importantes sobre la situación fiscal del contribuyente.

La herramienta:
- Inicia sesión automáticamente en el portal de AFIP
- Navega directamente a la sección "Nuestra Parte"
- Extrae y guarda en PDF las tablas de información disponibles
- Organiza los resultados por contribuyente en carpetas separadas

## Requisitos generales

- Python 3.7 o superior
- Google Chrome instalado
- Conexión a Internet

## Estructura del archivo de entrada

El programa utiliza un archivo CSV con el siguiente formato:

```
nombre,cuit,clave_fiscal
"Nombre Apellido","20123456789","contraseña"
```

Cada línea debe contener:
- **nombre**: Nombre completo del contribuyente (se usará para crear la carpeta)
- **cuit**: CUIT sin guiones
- **clave_fiscal**: Clave fiscal para acceder al portal de AFIP

## Versión anterior

La versión anterior del proyecto (anterior a la separación en Windows/Linux) se encuentra en commits anteriores. Si desea acceder a ella, puede usar git para volver a esos commits.

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

## Conversión de formato TXT a CSV

Si tiene datos de contribuyentes en formato TXT (formato antiguo), puede convertirlos al nuevo formato CSV:

```bash
python convertir_txt_a_csv.py mi_archivo.txt
```

## Resultados

Los resultados se guardan en la carpeta "AFIP_Resultados" en el Escritorio, organizados de la siguiente manera:

```
AFIP_Resultados/
  ├── Nombre del Contribuyente/
  │    └── CUIT/
  │         └── año_XXXX/
  │              └── Nombre de la Sección/
  │                   ├── tabla1_icono1.pdf
  │                   ├── tabla2_icono1.pdf
  │                   └── ...
  └── ...
```

## Características adicionales

- **Verificación de carpetas existentes**: Al iniciar, el programa verifica si la carpeta de resultados ya existe y pregunta si desea eliminarla antes de continuar.
- **Manejo de errores de login**: Si hay problemas con las credenciales de un contribuyente, el programa lo registra y continúa con el siguiente.
- **Detección de duplicados**: El programa evita guardar archivos duplicados, optimizando el proceso de extracción.
- **Optimización de velocidad**: Tiempos de espera calibrados para maximizar la velocidad sin comprometer la estabilidad.

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
- Verifique los archivos PDF generados en la carpeta de resultados 