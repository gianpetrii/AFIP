# AFIP Extractor - Versión Linux

Este programa permite automatizar la extracción de datos fiscales de múltiples contribuyentes desde el servicio "Nuestra Parte" de AFIP.

## Requisitos
- Google Chrome debe estar instalado en su sistema
- Conexión a internet para acceder a la página de AFIP

## Instrucciones de instalación
1. Descomprima el archivo descargado
2. Abra una terminal en la carpeta extraída
3. Otorgue permisos de ejecución al programa:
   ```
   chmod +x AFIP_Extractor
   ```

## Instrucciones de uso
1. Prepare un archivo CSV llamado `clientes.csv` con las columnas: nombre,cuit,clave_fiscal
   - Puede usar como referencia el archivo `clientes_ejemplo.csv` incluido
2. Ejecute el programa desde la terminal:
   ```
   ./AFIP_Extractor
   ```
3. Siga las instrucciones que aparecen en pantalla
4. Los resultados se guardarán en la carpeta `AFIP_Resultados` dentro del directorio donde se ejecuta el programa

## Para usuarios de WSL (Windows Subsystem for Linux)
Si está usando WSL, debe realizar estos pasos adicionales:
1. Instale xdotool:
   ```
   sudo apt-get update
   sudo apt-get install -y xdotool
   ```
2. Asegúrese de tener un servidor X configurado para mostrar aplicaciones gráficas

## Solución de problemas
- Si el programa no puede iniciar Google Chrome, verifique que Chrome esté instalado correctamente
- En caso de problemas con las descargas de PDFs, verifique los permisos de escritura en la carpeta actual
- Para más información, revise los logs generados en la carpeta `logs`

## Contacto
Si encuentra problemas o tiene sugerencias, contacte al equipo de desarrollo. 