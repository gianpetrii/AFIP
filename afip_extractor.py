#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AFIP Nuestra Parte Extractor

Herramienta que extrae información de la sección "Nuestra Parte" del sitio de AFIP.
"""

import os
import sys
import time
import csv
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import re
import signal
import functools
import threading

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Importar utilidades
from utils.csv_utils import CSVHandler
from utils.file_utils import normalizar_nombre, crear_estructura_carpetas, verificar_archivo_existe

# Intentar importar pyautogui para manejar diálogos nativos
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    # Configurar timeout más largo para operaciones de pyautogui
    pyautogui.PAUSE = 1.0
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("NOTA: Para mejorar el manejo de diálogos de archivos, instale pyautogui: pip install pyautogui")
except Exception as e:
    PYAUTOGUI_AVAILABLE = False
    print(f"NOTA: No se pudo inicializar pyautogui debido a: {e}")
    print("El programa funcionará sin la capacidad de manejar diálogos nativos.")

# Configuración de logging
# Asegurar que la carpeta de logs exista
os.makedirs("logs", exist_ok=True)

# Configurar el formato para los logs
formato_detallado = '%(asctime)s - %(levelname)s - %(message)s'
formato_simple = '%(asctime)s - %(message)s'

# Obtener la fecha actual para el nombre del archivo de log
fecha_actual = datetime.now().strftime("%Y%m%d")
archivo_log_tecnico = "afip_extractor.log"
archivo_log_usuario = os.path.join("logs", f"afip_extractor_{fecha_actual}.log")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format=formato_detallado,
    handlers=[
        logging.FileHandler(archivo_log_tecnico),  # Log técnico detallado
        logging.StreamHandler()  # Salida a consola
    ]
)

# Crear un logger adicional para el usuario con formato más simple
logger_usuario = logging.getLogger("AFIP_Extractor")
logger_usuario.setLevel(logging.INFO)
handler_usuario = logging.FileHandler(archivo_log_usuario)
handler_usuario.setFormatter(logging.Formatter(formato_simple))
logger_usuario.addHandler(handler_usuario)

logger = logging.getLogger("AFIP Extractor")

# Definición de una excepción para el timeout
class ContribuyenteTimeoutError(Exception):
    """Excepción para cuando un contribuyente supera el tiempo máximo de procesamiento."""
    pass

class NuestraParteExtractor:
    def __init__(self):
        """
        Inicializa el extractor de información de AFIP Nuestra Parte.
        Configura las rutas de directorios, verifica el entorno y prepara
        las variables necesarias para el funcionamiento.
        """
        self.directorio_actual = os.getcwd()
        
        # Limpiar el archivo de logs al inicio de una nueva ejecución
        log_file = "afip_extractor.log"
        try:
            # Verificar si el archivo existe antes de limpiarlo
            if os.path.exists(log_file):
                with open(log_file, 'w') as f:
                    f.write("")  # Escribir una cadena vacía para limpiar el archivo
                logger.info("Archivo de logs limpiado al iniciar nueva ejecución")
        except Exception as e:
            print(f"No se pudo limpiar el archivo de logs: {e}")
        
        # Actualizar lista de años desde 2018 hasta el año actual
        current_year = datetime.now().year
        self.años_disponibles = [str(year) for year in range(2018, current_year + 1)]
        
        # Simplificar la estructura de carpetas para evitar rutas demasiado largas
        # Usar carpeta de resultados directamente en el Desktop sin subcarpetas anidadas profundas
        self.output_folder = os.path.join(os.path.expanduser('~'), "Desktop", "AFIP_Resultados")
        
        # Configuración del timeout para el procesamiento de un contribuyente (en segundos)
        # 20 minutos por defecto, ajustable según necesidad
        self.contribuyente_timeout = 20 * 60
        
        # Verificar si estamos en WSL para configuración especial
        self.is_wsl = sys.platform.startswith('linux') and 'microsoft' in os.uname().release.lower()
        if self.is_wsl:
            logger.info("Detectado entorno WSL (Windows Subsystem for Linux)")
            # Verificar si xdotool está instalado
            try:
                result = os.system("which xdotool > /dev/null 2>&1")
                if result != 0:
                    logger.info("xdotool no encontrado, intentando instalarlo...")
                    os.system("sudo apt-get update -y && sudo apt-get install -y xdotool")
                    logger.info("Instalación de xdotool completada")
                else:
                    logger.info("xdotool ya está instalado")
            except:
                logger.warning("No se pudo verificar o instalar xdotool")
        
        # Identificar el directorio del escritorio (Desktop) según el sistema operativo
        if sys.platform.startswith('win'):
            self.desktop_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
        else:  # Linux/macOS
            # Intentar detectar el escritorio en diferentes idiomas
            desktop_candidates = [
                os.path.join(os.path.expanduser('~'), 'Desktop'),
                os.path.join(os.path.expanduser('~'), 'Escritorio'),
                os.path.join(os.path.expanduser('~'), 'desktop')
            ]
            self.desktop_dir = next((d for d in desktop_candidates if os.path.exists(d)), 
                                    os.path.expanduser('~'))  # Usar home como fallback
        
    def setup_driver(self):
        """
        Configura y devuelve el driver de Chrome con opciones optimizadas.
        
        Returns:
            WebDriver: Instancia configurada del WebDriver de Chrome
        """
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Habilitar guardado de PDF directamente
        prefs = {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,  # No abrir PDF en Chrome
            "print.always_print_as_pdf": True,  # Siempre imprimir como PDF
            "print.prefer_pdf_over_print_preview": True,  # Preferir PDF sobre vista previa
            "printing.print_preview_sticky_settings.appState": json.dumps({
                "recentDestinations": [{
                    "id": "Save as PDF",
                    "origin": "local",
                    "account": ""
                }],
                "selectedDestinationId": "Save as PDF",
                "version": 2,
                "isHeaderFooterEnabled": False,
                "isCssBackgroundEnabled": True,
                "scalingType": 3,  # Ajustar a la página
                "scaling": "100"
            })
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        # Detectar sistema operativo para usar el driver correcto
        if sys.platform.startswith('win'):
            driver_path = os.path.join(self.directorio_actual, "chromedriver_win32", "chromedriver.exe")
        elif sys.platform.startswith('linux'):
            driver_path = os.path.join(self.directorio_actual, "chromedriver_linux64", "chromedriver")
        else:  # Darwin (macOS)
            driver_path = os.path.join(self.directorio_actual, "chromedriver_mac64", "chromedriver")
        
        try:
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e:
            logger.error(f"Error al iniciar Chrome: {e}")
            raise
    
    def crear_estructura_carpetas(self, ruta=None):
        """
        Crea la carpeta especificada donde se guardarán los resultados.
        
        Args:
            ruta (str, optional): Ruta de la carpeta a crear. Por defecto, la carpeta principal de resultados.
            
        Returns:
            bool: True si se creó exitosamente, False en caso contrario
        """
        if ruta is None:
            ruta = self.output_folder
        
        return crear_estructura_carpetas(ruta)
    
    def leer_contribuyentes(self, csv_file="clientes.csv"):
        """
        Lee la lista de contribuyentes desde un archivo CSV.
        
        Args:
            csv_file (str): Ruta al archivo CSV con los datos de los contribuyentes
        
        Returns:
            list: Lista de diccionarios con información de contribuyentes
        """
        # Usar la clase CSVHandler para leer contribuyentes
        contribuyentes = CSVHandler.leer_contribuyentes(csv_file)
        
        if not contribuyentes:
            logger.error(f"El archivo {csv_file} está vacío o no tiene el formato correcto")
            raise ValueError(f"El archivo {csv_file} está vacío o no tiene el formato correcto")
                
        logger.info(f"Se leyeron {len(contribuyentes)} contribuyentes del archivo {csv_file}")
        return contribuyentes
    
    def esperar_elemento(self, driver, locator, mensaje="Esperando elemento", max_intentos=5, tiempo_espera=1, clickable=False):
        """
        Espera a que un elemento esté presente en el DOM y visible.
        
        Args:
            driver: WebDriver de Selenium
            locator: Tupla con el tipo de selector y el valor (e.g., (By.ID, "elemento"))
            mensaje: Mensaje para los logs
            max_intentos: Número máximo de intentos
            tiempo_espera: Tiempo de espera entre intentos
            clickable: Si es True, espera a que el elemento sea clickeable
            
        Returns:
            WebElement: El elemento encontrado, o None si no se encuentra
        """
        logger.info(f"{mensaje} (locator: {locator})")
        
        for intento in range(1, max_intentos + 1):
            try:
                if clickable:
                    # Esperar a que el elemento sea clickeable
                    element = WebDriverWait(driver, tiempo_espera).until(
                        EC.element_to_be_clickable(locator)
                    )
                else:
                    # Esperar a que el elemento sea visible
                    element = WebDriverWait(driver, tiempo_espera).until(
                        EC.visibility_of_element_located(locator)
                    )
                logger.info(f"Elemento encontrado en intento {intento}")
                return element
            except TimeoutException:
                logger.warning(f"Timeout esperando elemento en intento {intento}/{max_intentos}")
                if intento == max_intentos:
                    logger.error(f"No se encontró el elemento después de {max_intentos} intentos")
                    return None
            except Exception as e:
                logger.warning(f"Error al buscar elemento en intento {intento}/{max_intentos}: {e}")
                if intento == max_intentos:
                    logger.error(f"Error final al buscar elemento: {e}")
                    return None
        
        return None
    
    def esperar_con_intentos(self, condition_func, mensaje="Esperando condición", max_intentos=5, tiempo_espera=1):
        """
        Espera a que una condición sea verdadera.
        
        Args:
            condition_func: Función que devuelve True cuando la condición se cumple
            mensaje: Mensaje para los logs
            max_intentos: Número máximo de intentos
            tiempo_espera: Tiempo de espera entre intentos
            
        Returns:
            bool: True si la condición se cumplió, False en caso contrario
        """
        logger.info(f"{mensaje}")
        
        for intento in range(1, max_intentos + 1):
            try:
                if condition_func():
                    logger.info(f"Condición cumplida en intento {intento}")
                    return True
                
                logger.warning(f"Condición no cumplida en intento {intento}/{max_intentos}")
                if intento < max_intentos:
                    time.sleep(tiempo_espera)
            except Exception as e:
                logger.warning(f"Error al evaluar condición en intento {intento}/{max_intentos}: {e}")
                if intento < max_intentos:
                    time.sleep(tiempo_espera)
        
        logger.error(f"Condición no cumplida después de {max_intentos} intentos")
        return False
    
    def iniciar_sesion(self, driver, cuit, clave_fiscal):
        """
        Inicia sesión en el sitio de AFIP.
        
        Args:
            driver: WebDriver de Selenium
            cuit: CUIT del contribuyente
            clave_fiscal: Clave fiscal del contribuyente
            
        Returns:
            bool: True si el inicio de sesión fue exitoso, False en caso contrario
        """
        try:
            logger.info(f"Iniciando navegación directamente a la página de login de AFIP")
            # Ir directamente a la URL de login
            driver.get("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
            logger.info(f"URL de login cargada: {driver.current_url}")
            
            # Verificar que la página ha cargado correctamente
            if not self.esperar_url_contenga(driver, "auth.afip.gob.ar", "Esperando página de login"):
                logger.error("No se pudo cargar la página de login")
                return False
                
            logger.info(f"Título de la página: '{driver.title}'")
            
            # PASO 1: Ingresar CUIT
            logger.info("Buscando campo de CUIT...")
            try:
                # Selector exacto basado en el HTML proporcionado
                username_field = self.esperar_elemento(
                    driver, 
                    (By.ID, "F1:username"),
                    mensaje="Esperando campo de CUIT",
                    max_intentos=15
                )
                
                if not username_field:
                    logger.error("No se encontró el campo de CUIT")
                    return False
                    
                logger.info("Campo de CUIT encontrado")
                username_field.clear()
                username_field.send_keys(cuit)
                logger.info(f"CUIT ingresado: {cuit}")
                
                # Buscar el botón "Siguiente"
                siguiente_button = self.esperar_elemento(
                    driver, 
                    (By.ID, "F1:btnSiguiente"),
                    mensaje="Esperando botón Siguiente",
                    clickable=True,
                    max_intentos=15
                )
                
                if not siguiente_button:
                    logger.error("No se encontró el botón Siguiente")
                    return False
                    
                logger.info("Botón 'Siguiente' encontrado, haciendo clic...")
                siguiente_button.click()
                
                # PASO 2: Ingresar contraseña
                logger.info("Buscando campo de contraseña...")
                # La página se recarga, necesitamos esperar el campo de contraseña
                password_field = self.esperar_elemento(
                    driver, 
                    (By.ID, "F1:password"),
                    mensaje="Esperando campo de contraseña",
                    max_intentos=15
                )
                
                if not password_field:
                    logger.error("No se encontró el campo de contraseña")
                    return False
                    
                logger.info("Campo de contraseña encontrado")
                password_field.clear()
                password_field.send_keys(clave_fiscal)
                logger.info("Contraseña ingresada")
                
                # Buscar el botón "Ingresar"
                ingresar_button = self.esperar_elemento(
                    driver, 
                    (By.ID, "F1:btnIngresar"),
                    mensaje="Esperando botón Ingresar",
                    clickable=True,
                    max_intentos=15
                )
                
                if not ingresar_button:
                    logger.error("No se encontró el botón Ingresar")
                    return False
                    
                logger.info("Botón 'Ingresar' encontrado, haciendo clic...")
                ingresar_button.click()
                
                # Esperar redirección al panel principal (varias URLs posibles)
                urls_exitosas = ["portalcf.cloud.afip.gob.ar", "menuPrincipal", "contribuyente"]
                
                # Verificar redirección a cualquiera de las URLs exitosas
                exito = False
                for url in urls_exitosas:
                    if self.esperar_url_contenga(driver, url, f"Esperando redirección a {url}", max_intentos=10):
                        exito = True
                        break
                
                if not exito:
                    logger.error("No se detectó redirección exitosa después del login")
                    return False
                    
                # Verificar si estamos en la página de servicios
                logger.info(f"URL después de login: {driver.current_url}")
                logger.info(f"Inicio de sesión exitoso para el usuario {cuit}")
                
                # En lugar de navegar directamente a la URL de "Nuestra Parte"
                # vamos a usar el buscador principal
                logger.info("Buscando 'Nuestra Parte' en el buscador principal")
                
                try:
                    # Esperar a que el buscador esté disponible
                    buscador = self.esperar_elemento(
                        driver, 
                        (By.ID, "buscadorInput"),
                        mensaje="Esperando buscador principal",
                        max_intentos=15
                    )
                    
                    if not buscador:
                        logger.error("No se encontró el buscador principal")
                        # Intentar navegación alternativa
                        return self.navegacion_alternativa(driver)
                        
                    logger.info("Buscador encontrado")
                    
                    # Hacer clic en el buscador primero para activarlo
                    buscador.click()
                    
                    # Limpiar el campo y escribir "Nuestra Parte"
                    buscador.clear()
                    buscador.send_keys("Nuestra Parte")
                    logger.info("Texto 'Nuestra Parte' ingresado en el buscador")
                    
                    # Verificar que el dropdown de resultados está visible
                    dropdown = self.esperar_elemento(
                        driver, 
                        (By.ID, "resultadoBusqueda"),
                        mensaje="Esperando dropdown de resultados",
                        max_intentos=10
                    )
                    
                    if not dropdown:
                        logger.warning("No se encontró el dropdown de resultados")
                        # Intentar navegación alternativa
                        return self.navegacion_alternativa(driver)
                        
                    logger.info("Dropdown de resultados visible")
                    
                    # Seleccionar el primer resultado
                    primer_resultado = self.esperar_elemento(
                        driver, 
                        (By.CSS_SELECTOR, "#resultadoBusqueda a:first-child"),
                        mensaje="Esperando primer resultado de búsqueda",
                        clickable=True,
                        max_intentos=10
                    )
                    
                    if not primer_resultado:
                        logger.warning("No se encontró el primer resultado de búsqueda")
                        # Intentar navegación alternativa
                        return self.navegacion_alternativa(driver)
                        
                    logger.info("Primer resultado de búsqueda encontrado, haciendo clic...")
                    
                    # Capturar las ventanas actuales antes de hacer clic
                    ventanas_antes = driver.window_handles
                    
                    # Hacer clic en el primer resultado
                    primer_resultado.click()
                    logger.info("Se hizo clic en el primer resultado")
                    
                    # Esperar a que se abra una nueva pestaña y cambiar a ella
                    if not self.esperar_nueva_ventana(driver, ventanas_antes, "Esperando nueva pestaña", max_intentos=10):
                        logger.warning("No se abrió una nueva pestaña")
                        # Intentar navegación alternativa
                        return self.navegacion_alternativa(driver)
                    
                    # Verificar si estamos en la página correcta de Nuestra Parte
                    # Verificamos por fragmentos de URL que podrían indicar que estamos en la página correcta
                    url_actual = driver.current_url
                    urls_validas = ["serviciosjava2.afip.gob.ar/cgpf", "nuestra-parte", "nuestraparte"]
                    
                    if any(fragmento in url_actual.lower() for fragmento in urls_validas):
                        logger.info(f"Navegación exitosa a través del buscador. URL actual: {url_actual}")
                        return True
                    else:
                        logger.error(f"No se pudo navegar a la página de Nuestra Parte. URL actual: {url_actual}")
                        return self.navegacion_alternativa(driver)
                        
                except Exception as e:
                    logger.error(f"Error al buscar 'Nuestra Parte': {e}")
                    return self.navegacion_alternativa(driver)
                
            except TimeoutException as e:
                logger.error(f"Timeout esperando elementos de login: {e}")
                return False
            except Exception as e:
                logger.error(f"Error durante el proceso de login: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error general al iniciar sesión: {e}")
            return False
    
    def procesar_nuestra_parte(self, driver, cuit, año, output_dir):
        """
        Procesa la sección "Nuestra Parte" para el CUIT y año especificados.
        
        Args:
            driver: WebDriver de Selenium
            cuit: CUIT a procesar
            año: Año a procesar
            output_dir: Directorio donde guardar los resultados
        
        Returns:
            bool: True si el proceso fue exitoso, False en caso contrario
        """
        try:
            # Verificar que estamos en la página correcta
            current_url = driver.current_url
            valid_fragments = ["serviciosjava2.afip.gob.ar/cgpf", "nuestra-parte", "nuestraparte"]
            if not any(fragment in current_url.lower() for fragment in valid_fragments):
                logger.warning(f"URL actual '{current_url}' no corresponde a 'Nuestra Parte'")
            
            # Buscar los botones de año directamente sin buscar primero la pestaña
            # Ya que la pestaña podría estar ya seleccionada por defecto
            año_encontrado = False
            
            # Nueva estrategia: Buscar botones con la clase y el atributo data-periodo
            try:
                # Encontrar todos los botones de año con el nuevo selector
                year_buttons = driver.find_elements(By.CSS_SELECTOR, "span.btn-consultar[data-periodo]")
                
                if year_buttons:
                    logger.info(f"Se encontraron {len(year_buttons)} botones de año con el nuevo selector")
                    
                    # Guardar una lista de años disponibles para depuración
                    años_disponibles = [btn.text.strip() for btn in year_buttons]
                    logger.info(f"Años disponibles: {años_disponibles}")
                    
                    # Buscar el botón correspondiente al año requerido
                    for button in year_buttons:
                        periodo = button.get_attribute("data-periodo")
                        if periodo == str(año):
                            logger.info(f"Botón del año {año} encontrado, haciendo clic...")
                            
                            # Hacer scroll al botón y luego hacer clic
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(0.5)  # Reducido de 1 a 0.5
                            driver.execute_script("arguments[0].click();", button)
                            logger.info(f"Se hizo clic en el botón del año {año}")
                            time.sleep(2)  # Reducido de 5 a 2 segundos
                            
                            año_encontrado = True
                            break
                    
                    # Si no se encuentra el año exacto, buscar el más reciente disponible
                    if not año_encontrado:
                        logger.warning(f"No se encontró el año {año}, buscando el año más reciente disponible")
                        # Ordenar los botones por año (de más reciente a más antiguo)
                        year_buttons_sorted = sorted(year_buttons, key=lambda btn: btn.get_attribute("data-periodo"), reverse=True)
                        
                        if year_buttons_sorted:
                            recent_year = year_buttons_sorted[0]
                            año_reciente = recent_year.get_attribute("data-periodo")
                            logger.info(f"Usando el año más reciente disponible: {año_reciente}")
                            
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", recent_year)
                            time.sleep(0.5)  # Reducido de 1 a 0.5
                            driver.execute_script("arguments[0].click();", recent_year)
                            logger.info(f"Se hizo clic en el año más reciente: {año_reciente}")
                            time.sleep(2)  # Reducido de 5 a 2 segundos
                            
                            # Actualizar el año para la carpeta de salida
                            año = año_reciente
                            año_encontrado = True
                else:
                    logger.warning("No se encontraron botones de año con el nuevo selector")
            except Exception as e:
                logger.error(f"Error al buscar botones de año: {e}")
            
            # Si fallamos con el nuevo método, intentar con el método anterior como fallback
            if not año_encontrado:
                logger.warning("Intentando método alternativo para encontrar botones de año")
                try:
                    # Intentar encontrar la pestaña "Información nacional anual" primero
                    tab_selectors = [
                        "a[role='tab']:contains('Información nacional anual')",
                        "a[href='#tabNacional']",
                        "ul.nav-tabs li.active a",
                        "a[role='tab']"
                    ]
                    
                    for selector in tab_selectors:
                        try:
                            tab = driver.find_element(By.CSS_SELECTOR, selector)
                            driver.execute_script("arguments[0].click();", tab)
                            logger.info(f"Se hizo clic en pestaña usando selector: {selector}")
                            time.sleep(1)  # Reducido de 2 a 1
                            break
                        except Exception as e:
                            logger.warning(f"No se encontró pestaña con selector: {selector}")
                            continue
                    
                    # Buscar botones de año con los selectores originales
                    buttons = driver.find_elements(By.CSS_SELECTOR, "button.year-button")
                    visible_buttons = [button for button in buttons if button.is_displayed()]
                    
                    if visible_buttons:
                        # Proceso original para seleccionar el año
                        for button in visible_buttons:
                            if button.text.strip() == str(año):
                                driver.execute_script("arguments[0].click();", button)
                                time.sleep(1)  # Reducido de 2 a 1
                                año_encontrado = True
                except Exception as e:
                    logger.error(f"Error en método alternativo: {e}")
            
            # Si aún no hemos encontrado el año, continuar con lo que esté disponible
            if not año_encontrado:
                logger.warning(f"No se pudo encontrar/seleccionar el año {año}, continuando con lo que esté disponible")
            
            # Procesar secciones de datos
            self.procesar_secciones_datos(driver, output_dir)
            
            return True
            
        except Exception as e:
            logger.error(f"Error al procesar 'Nuestra Parte': {e}")
            return False
    
    def procesar_secciones_datos(self, driver, output_dir):
        """
        Procesa las secciones de datos y guarda la información en archivos.
        
        Args:
            driver: WebDriver de Selenium
            output_dir: Directorio donde guardar los resultados
            
        Returns:
            bool: True si el proceso fue exitoso, False en caso contrario
        """
        # Esperar brevemente a que la página cargue completamente
        logger.info("Esperando brevemente a que la página cargue los elementos básicos...")
        time.sleep(1)  # Reducido de 2 a 1 segundo
        
        # Conjunto para almacenar todas las rutas de archivos guardados y evitar duplicados
        archivos_guardados = set()
        
        try:
            # 1. Encontrar todas las secciones principales usando la estructura del DOM
            secciones_principales = driver.find_elements(By.CSS_SELECTOR, "div.div-container-grey.row")
            logger.info(f"Se encontraron {len(secciones_principales)} secciones principales")
            
            for i, seccion in enumerate(secciones_principales, 1):
                try:
                    # 2. Obtener el nombre de la sección desde el span dentro de col-md-11
                    try:
                        nombre_seccion_elem = seccion.find_element(By.CSS_SELECTOR, "div.col-md-11 > span")
                        nombre_seccion = nombre_seccion_elem.text.strip()
                        logger.info(f"Procesando sección principal {i}/{len(secciones_principales)}: {nombre_seccion}")
                    except Exception as e:
                        nombre_seccion = f"seccion_{i}"
                        logger.info(f"Procesando sección principal {i}/{len(secciones_principales)} sin nombre")
                    
                    # Ignoramos secciones específicas como "Declaraciones juradas del periodo anterior"
                    if "Declaraciones juradas del periodo anterior" in nombre_seccion:
                        logger.info(f"Ignorando sección: {nombre_seccion}")
                        continue
                                
                    # Crear directorio para esta sección
                    seccion_dir = os.path.join(output_dir, self.normalizar_nombre(nombre_seccion))
                    crear_estructura_carpetas(seccion_dir)
                    
                    # 3. Encontrar el container de los iconos y luego los iconos dentro de él
                    try:
                        icon_container = seccion.find_element(By.CSS_SELECTOR, "div.col-md-10.col-sm-10.col-xs-12.center")
                        iconos = icon_container.find_elements(By.CSS_SELECTOR, "div.circleIcon")
                        logger.info(f"Se encontraron {len(iconos)} íconos en la sección {nombre_seccion}")
                    except Exception as e:
                        logger.error(f"Error al buscar iconos en la sección {nombre_seccion}: {e}")
                        continue
                                            
                    # 4. Procesar cada icono/sub-sección
                    for j, icono in enumerate(iconos, 1):
                        try:
                            # Obtener el nombre del ícono desde el párrafo
                            try:
                                nombre_icono_elem = icono.find_element(By.CSS_SELECTOR, "p")
                                nombre_icono = nombre_icono_elem.text.strip()
                                logger.info(f"Procesando ícono {j}/{len(iconos)}: {nombre_icono}")
                            except Exception as e:
                                nombre_icono = f"icono_{j}"
                                logger.info(f"Procesando ícono {j}/{len(iconos)} sin nombre")
                            
                            # Hacer clic en el icono para mostrar su contenido
                            try:
                                # Buscar el elemento i que es clickeable dentro del icono
                                icono_click = icono.find_element(By.CSS_SELECTOR, "i")
                                
                                # Hacer scroll al elemento para asegurarnos de que es visible
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", icono_click)
                                time.sleep(0.5)  # Reducido de 1 a 0.5
                                
                                # Hacer clic mediante JavaScript para evitar problemas de visibilidad/clickeabilidad
                                driver.execute_script("arguments[0].click();", icono_click)
                                logger.info(f"Clic exitoso en ícono {j} de {nombre_icono}")
                                
                                # Esperar a que se carguen los datos
                                time.sleep(1.5)  # Reducido de 3 a 1.5
                            except Exception as e:
                                logger.error(f"Error al hacer clic en ícono {j}: {e}")
                                continue
                            
                            # 5. Encontrar todos los paneles visibles (los que tienen display distinto a none)
                            try:
                                # Primero buscar todos los div a nivel de body que podrían contener las tablas
                                contenedores = driver.find_elements(By.CSS_SELECTOR, "div.container")
                                paneles_visibles = []
                                
                                for contenedor in contenedores:
                                    # Buscar paneles dentro de cada contenedor que no tengan style="display: none;"
                                    paneles = contenedor.find_elements(By.CSS_SELECTOR, "div:not([style*='display: none'])")
                                    for panel in paneles:
                                        # Verificar si el panel contiene un elemento con clase panel-body
                                        panel_body_elems = panel.find_elements(By.CSS_SELECTOR, "div.panel-body.text-center")
                                        for panel_body in panel_body_elems:
                                            if panel_body.is_displayed():
                                                paneles_visibles.append(panel_body)
                                
                                logger.info(f"Se encontraron {len(paneles_visibles)} paneles visibles")
                                
                                # Si no encontramos paneles visibles con el método anterior, intentar otro enfoque
                                if not paneles_visibles:
                                    paneles_visibles = driver.find_elements(By.CSS_SELECTOR, "div.panel-body.text-center")
                                    # Filtrar solo los que están visibles
                                    paneles_visibles = [p for p in paneles_visibles if p.is_displayed()]
                                    logger.info(f"Segundo intento: Se encontraron {len(paneles_visibles)} paneles visibles")
                                
                                # 6. Procesar cada panel visible
                                for k, panel in enumerate(paneles_visibles, 1):
                                    try:
                                        # Obtener el nombre de la tabla desde el h3
                                        try:
                                            titulo_elem = panel.find_element(By.CSS_SELECTOR, "h3")
                                            titulo_tabla = titulo_elem.text.strip()
                                            logger.info(f"Procesando tabla {k}/{len(paneles_visibles)}: '{titulo_tabla}'")
                                        except Exception as e:
                                            titulo_tabla = f"tabla_{k}"
                                            logger.info(f"Procesando tabla {k}/{len(paneles_visibles)} sin título")
                                        
                                        # 7. Encontrar botones de impresión
                                        botones_imprimir = panel.find_elements(By.CSS_SELECTOR, "a.btn-imprimir")
                                        
                                        if not botones_imprimir:
                                            # Intentar una búsqueda más amplia si no encontramos botones
                                            botones_imprimir = panel.find_elements(By.XPATH, ".//a[contains(@class, 'btn-imprimir')]")
                                        
                                        if not botones_imprimir:
                                            # Si aún no encontramos, buscar el i con clase fa-print
                                            print_icons = panel.find_elements(By.CSS_SELECTOR, "i.fa-print")
                                            if print_icons:
                                                # Obtener los elementos padre (a) de los iconos
                                                botones_imprimir = [icon.find_element(By.XPATH, "..") for icon in print_icons]
                                        
                                        logger.info(f"Se encontraron {len(botones_imprimir)} botones de impresión")
                                        
                                        # 8. Procesar cada botón de impresión
                                        for l, boton in enumerate(botones_imprimir, 1):
                                            # Usar sólo el título de la tabla como nombre del archivo
                                            # sin incluir el nombre del ícono para simplificar los nombres
                                            nombre_archivo_base = self.normalizar_nombre(titulo_tabla)
                                            
                                            # Ruta completa del archivo
                                            ruta_completa = os.path.join(seccion_dir, f"{nombre_archivo_base}.pdf")
                                            
                                            # Verificar si este archivo ya fue guardado previamente (evitar duplicados)
                                            if ruta_completa in archivos_guardados:
                                                logger.info(f"Ignorando archivo duplicado: {nombre_archivo_base}")
                                                continue
                                            
                                            # También verificar si el archivo ya existe en disco (puede haber sido guardado en sesiones anteriores)
                                            if os.path.exists(ruta_completa):
                                                logger.info(f"El archivo ya existe en disco, agregando a registro: {nombre_archivo_base}")
                                                archivos_guardados.add(ruta_completa)
                                                continue
                                            
                                            logger.info(f"Guardando PDF para botón {l}/{len(botones_imprimir)}: '{nombre_archivo_base}'")
                                            
                                            try:
                                                # Hacer scroll al botón para que sea visible
                                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
                                                time.sleep(0.5)  # Reducido de 1 a 0.5
                                                
                                                # Hacer clic en el botón de impresión
                                                driver.execute_script("arguments[0].click();", boton)
                                                logger.info(f"Clic exitoso en botón de impresión {l} para {nombre_archivo_base}")
                                                
                                                # Esperar a que se abra la ventana de impresión
                                                ventanas_antes = driver.window_handles
                                                
                                                # Nuestro método modificado siempre devuelve True para no bloquear el proceso
                                                if self.esperar_nueva_ventana(driver, ventanas_antes, f"Esperando ventana de impresión para {nombre_archivo_base}", max_intentos=8):
                                                    # Guardar como PDF
                                                    logger.info(f"Guardando PDF: {ruta_completa}")
                                                    
                                                    # Crear directorio si no existe
                                                    dir_path = os.path.dirname(ruta_completa)
                                                    crear_estructura_carpetas(dir_path)
                                                    
                                                    # Llamar al método de guardado de diálogo
                                                    exito = self.handle_save_dialog(ruta_completa)
                                                    
                                                    # Esperar un momento para que se procese el guardado
                                                    time.sleep(2)  # Reducido de 3 a 2
                                                    
                                                    # Verificar si el archivo se creó correctamente
                                                    if verificar_archivo_existe(ruta_completa, timeout=10):
                                                        logger.info(f"PDF guardado exitosamente: {ruta_completa}")
                                                        # Agregar al conjunto de archivos guardados
                                                        archivos_guardados.add(ruta_completa)
                                                    else:
                                                        logger.warning(f"No se encontró el archivo guardado: {ruta_completa}")
                                                        
                                                        # Verificar si hay archivos similares que podrían haberse guardado
                                                        directorio = os.path.dirname(ruta_completa)
                                                        archivos_similares = [f for f in os.listdir(directorio) if nombre_archivo_base in f]
                                                        if archivos_similares:
                                                            archivo_similar = os.path.join(directorio, archivos_similares[0])
                                                            logger.info(f"Se encontró un archivo similar: {archivo_similar}")
                                                            # Agregar el archivo similar al conjunto
                                                            archivos_guardados.add(archivo_similar)
                                                else:
                                                    logger.warning(f"No se pudo detectar ventana de impresión para {nombre_archivo_base}")
                                            except Exception as e:
                                                logger.error(f"Error procesando botón de impresión {l}: {e}")
                                    except Exception as e:
                                        logger.error(f"Error procesando panel {k}: {e}")
                            except Exception as e:
                                logger.error(f"Error buscando paneles visibles: {e}")
                            
                            # Si es necesario, cerrar la sección actual antes de pasar al siguiente ícono
                            try:
                                cerrar_botones = driver.find_elements(By.CSS_SELECTOR, "a.btn-cerrar")
                                for cerrar in cerrar_botones:
                                    if cerrar.is_displayed():
                                        driver.execute_script("arguments[0].click();", cerrar)
                                        logger.info("Cerrando sección actual antes de continuar")
                                        time.sleep(0.5)  # Reducido de 1 a 0.5
                                        break
                            except Exception as e:
                                logger.warning(f"No se pudo cerrar la sección actual: {e}")
                        except Exception as e:
                            logger.error(f"Error procesando ícono {j}: {e}")
                except Exception as e:
                    logger.error(f"Error procesando sección principal {i}: {e}")
                    
            # Al finalizar, mostrar resumen de archivos guardados
            logger.info(f"Total de archivos únicos guardados: {len(archivos_guardados)}")
            return True
        except Exception as e:
            logger.error(f"Error general procesando secciones de datos: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def procesar_contribuyente(self, contribuyente, año):
        """
        Procesa toda la información de un contribuyente con un timeout general.
        
        Args:
            contribuyente (dict): Diccionario con datos del contribuyente
            año (str): Año a procesar
            
        Returns:
            bool: True si el procesamiento fue exitoso, False en caso contrario
        """
        nombre = contribuyente["nombre"]
        cuit = contribuyente["cuit"]
        clave_fiscal = contribuyente["clave_fiscal"]
        
        logger.info(f"Procesando contribuyente: {nombre}")
        print(f"\nProcesando contribuyente: {nombre} (CUIT: {cuit})")
        
        # Crear carpeta para el contribuyente dentro de la carpeta del año
        año_dir = os.path.join(self.output_folder, str(año))
        path_contribuyente = os.path.join(año_dir, nombre)
        try:
            crear_estructura_carpetas(path_contribuyente)
            logger.info(f"Carpeta creada para contribuyente: {path_contribuyente}")
        except Exception as e:
            logger.error(f"Error al crear carpeta para {nombre}: {e}")
            logger_usuario.info(f"No se pudo crear la carpeta para {nombre}. Error: {e}")
            print(f"Error al crear carpeta para {nombre}. Continuando con el siguiente contribuyente...")
            return False
        
        # Iniciar driver
        driver = None
        
        # Establecer timeout global para este contribuyente
        # Usamos threading.Timer en lugar de signal porque funciona en Windows y es más compatible
        timer = None
        
        try:
            # Crear un temporizador que levantará una excepción si se excede el tiempo
            timeout_event = threading.Event()
            
            # Función que se ejecutará cuando se acabe el tiempo
            def timeout_callback():
                logger.error(f"Timeout de {self.contribuyente_timeout} segundos excedido para {nombre}")
                # Indicar que se ha excedido el tiempo
                timeout_event.set()
                # Intentar cerrar el navegador si existe
                nonlocal driver
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
            
            # Iniciar temporizador
            timer = threading.Timer(self.contribuyente_timeout, timeout_callback)
            timer.daemon = True  # El timer se detendrá si el programa principal termina
            timer.start()
            
            # Iniciar el procesamiento normal
            driver = self.setup_driver()
            logger_usuario.info(f"Navegador iniciado para procesar {nombre}")
            
            # Verificar periódicamente si se ha excedido el tiempo
            def check_timeout():
                if timeout_event.is_set():
                    raise ContribuyenteTimeoutError(f"Tiempo máximo de {self.contribuyente_timeout}s excedido")
            
            # Iniciar sesión
            check_timeout()  # Verificar timeout antes de cada paso importante
            logger_usuario.info(f"Iniciando sesión para {nombre} (CUIT: {cuit})")
            
            try:
                resultado_login = self.iniciar_sesion(driver, cuit, clave_fiscal)
                if not resultado_login:
                    # Verificar si hay mensajes específicos de error en la página
                    error_message = self.detectar_error_login(driver)
                    
                    if "cuit no encontrado" in error_message.lower() or "no existe" in error_message.lower():
                        mensaje_error = f"Error: El CUIT {cuit} no existe o no está registrado en AFIP."
                    elif "clave" in error_message.lower() or "contraseña" in error_message.lower() or "incorrecta" in error_message.lower():
                        mensaje_error = f"Error: La clave fiscal para el CUIT {cuit} es incorrecta."
                    elif "captcha" in error_message.lower():
                        mensaje_error = "Error: No se pudo resolver el captcha de AFIP."
                    elif "bloqueado" in error_message.lower() or "inhabilitado" in error_message.lower():
                        mensaje_error = f"Error: El CUIT {cuit} está bloqueado o inhabilitado temporalmente."
                    elif "sesión" in error_message.lower() or "activa" in error_message.lower():
                        mensaje_error = f"Error: Ya existe una sesión activa para el CUIT {cuit}. Cierre todas las sesiones activas e intente nuevamente."
                    elif "servicio" in error_message.lower() or "disponible" in error_message.lower():
                        mensaje_error = "Error: El servicio de AFIP no está disponible en este momento. Intente más tarde."
                    else:
                        mensaje_error = "Error al iniciar sesión. Verifique las credenciales (CUIT y clave fiscal)."
                    
                    with open(os.path.join(path_contribuyente, "error_login.txt"), "w") as f:
                        f.write(mensaje_error)
                    
                    logger.error(f"Error al iniciar sesión para {nombre}: {error_message}")
                    logger_usuario.info(f"{mensaje_error}")
                    print(f"{mensaje_error}")
                    print(f"Continuando con el siguiente contribuyente...")
                    return False
            except TimeoutException:
                mensaje_error = "Error: La página de AFIP tardó demasiado en responder durante el inicio de sesión."
                with open(os.path.join(path_contribuyente, "error_timeout_login.txt"), "w") as f:
                    f.write(mensaje_error)
                
                logger.error(f"Timeout durante el inicio de sesión para {nombre}")
                logger_usuario.info(mensaje_error)
                print(mensaje_error)
                print(f"Continuando con el siguiente contribuyente...")
                return False
            except Exception as e:
                mensaje_error = f"Error durante el inicio de sesión: {e}"
                with open(os.path.join(path_contribuyente, "error_login_general.txt"), "w") as f:
                    f.write(mensaje_error)
                
                logger.error(f"Error general durante el inicio de sesión para {nombre}: {e}")
                logger_usuario.info(mensaje_error)
                print(mensaje_error)
                print(f"Continuando con el siguiente contribuyente...")
                return False
            
            # Procesar Nuestra Parte
            check_timeout()  # Verificar timeout antes de procesar
            logger_usuario.info(f"Accediendo a la información del año {año} para {nombre}")
            
            try:
                resultado = self.procesar_nuestra_parte(driver, cuit, año, path_contribuyente)
                
                if resultado:
                    logger.info(f"Procesamiento de {nombre} completado exitosamente")
                    logger_usuario.info(f"Información fiscal del año {año} procesada exitosamente para {nombre}")
                    print(f"Procesamiento de {nombre} completado exitosamente")
                    return True
                else:
                    mensaje_error = f"No se pudo obtener la información fiscal del año {año} para {nombre}"
                    with open(os.path.join(path_contribuyente, "error_nuestra_parte.txt"), "w") as f:
                        f.write(mensaje_error)
                    
                    logger.warning(f"No se pudo procesar Nuestra Parte para {nombre}")
                    logger_usuario.info(mensaje_error)
                    print(mensaje_error)
                    print(f"Continuando con el siguiente contribuyente...")
                    return False
            except Exception as e:
                mensaje_error = f"Error al procesar la información fiscal: {e}"
                with open(os.path.join(path_contribuyente, "error_procesamiento.txt"), "w") as f:
                    f.write(mensaje_error)
                
                logger.error(f"Error al procesar Nuestra Parte para {nombre}: {e}")
                logger_usuario.info(mensaje_error)
                print(mensaje_error)
                print(f"Continuando con el siguiente contribuyente...")
                return False
                
        except ContribuyenteTimeoutError:
            mensaje_error = f"Se excedió el tiempo máximo de {self.contribuyente_timeout} segundos para procesar este contribuyente."
            with open(os.path.join(path_contribuyente, "error_timeout.txt"), "w") as f:
                f.write(f"Error: {mensaje_error}")
            
            logger.error(f"Timeout: {mensaje_error}")
            logger_usuario.info(f"Se excedió el tiempo máximo de procesamiento para {nombre}. El proceso se interrumpió por seguridad.")
            print(f"Timeout: Se excedió el tiempo máximo al procesar {nombre}. Continuando con el siguiente contribuyente...")
            return False
        except Exception as e:
            mensaje_error = f"Error inesperado: {e}"
            with open(os.path.join(path_contribuyente, "error_general.txt"), "w") as f:
                f.write(mensaje_error)
            
            logger.error(f"Error general procesando {nombre}: {e}")
            logger_usuario.info(f"Error inesperado al procesar {nombre}: {e}")
            print(f"Error procesando {nombre}: {e}. Continuando con el siguiente contribuyente...")
            return False
        finally:
            # Cancelar el timer si aún está activo
            if timer and timer.is_alive():
                timer.cancel()
                
            # Siempre cerrar el driver cuando termine el procesamiento
            if driver:
                logger.info("Cerrando el navegador")
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning(f"Error al cerrar el navegador: {e}")
                    
    def detectar_error_login(self, driver):
        """
        Intenta detectar mensajes de error específicos en la página de login de AFIP.
        
        Args:
            driver: WebDriver de Selenium
            
        Returns:
            str: Mensaje de error detectado o string vacío si no se detecta error
        """
        try:
            # Intentar encontrar elementos de error conocidos
            error_selectors = [
                "div.mensajeError",
                "div.error",
                "span.error",
                ".alert-danger",
                "#divErrores",
                "#mensajeError"
            ]
            
            for selector in error_selectors:
                try:
                    error_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for error_element in error_elements:
                        if error_element.is_displayed() and error_element.text.strip():
                            return error_element.text.strip()
                except:
                    continue
            
            # Si no se encontró un mensaje de error específico, verificar el título de la página
            # para dar una pista sobre el problema
            if "error" in driver.title.lower() or "problema" in driver.title.lower():
                return f"Error en la página: {driver.title}"
                
            return ""
        except:
            return "Error desconocido durante el inicio de sesión"
    
    def verificar_carpeta_resultados(self, año):
        """
        Verifica si la carpeta del año específico ya existe y pregunta al usuario si desea eliminarla.
        
        Args:
            año (str): El año seleccionado para procesar
        
        Returns:
            bool: True si se puede continuar con la ejecución, False si el usuario decide no eliminar la carpeta
        """
        # Crear la carpeta principal de resultados si no existe
        if not os.path.exists(self.output_folder):
            try:
                os.makedirs(self.output_folder)
                logger.info(f"Carpeta principal de resultados creada: {self.output_folder}")
            except Exception as e:
                logger.error(f"Error al crear la carpeta principal de resultados: {e}")
                print(f"Error al crear la carpeta de resultados: {e}")
                return False
                
        # Verificar si existe la carpeta del año específico
        año_dir = os.path.join(self.output_folder, str(año))
        if os.path.exists(año_dir):
            print(f"\nATENCIÓN: Ya existen resultados para el año {año} en: {año_dir}")
            respuesta = input("¿Desea eliminar estos resultados y continuar? (s/n): ").strip().lower()
            
            if respuesta == 's' or respuesta == 'si' or respuesta == 'y' or respuesta == 'yes':
                try:
                    import shutil
                    shutil.rmtree(año_dir)
                    logger.info(f"Carpeta de resultados del año {año} eliminada: {año_dir}")
                    print(f"Carpeta eliminada. Continuando...")
                    return True
                except Exception as e:
                    logger.error(f"Error al eliminar la carpeta de resultados del año {año}: {e}")
                    print(f"Error al eliminar la carpeta. Continuando de todos modos...")
                    return True
            else:
                logger.info(f"El usuario decidió no eliminar la carpeta de resultados del año {año}. Terminando ejecución.")
                print("Operación cancelada por el usuario.")
                return False
        
        return True
    
    def ejecutar(self, año=None, csv_file=None):
        """Función principal que inicia todo el proceso"""
        try:
            # Mostrar banner e instrucciones
            self.mostrar_banner()
            
            # Mensaje inicial para el usuario
            logger_usuario.info("=== INICIANDO EXTRACTOR DE INFORMACIÓN FISCAL DE AFIP ===")
            logger_usuario.info(f"Fecha y hora de inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            
            # Solicitar año a evaluar si no se proporcionó
            if año is None:
                año = self.solicitar_año()
                
            logger_usuario.info(f"Se procesará el año fiscal: {año}")
            
            # Verificar la carpeta de resultados del año específico
            if not self.verificar_carpeta_resultados(año):
                logger_usuario.info("Operación cancelada por el usuario. No se realizará la extracción.")
                return
            
            # Crear estructura de carpetas para el año
            año_dir = os.path.join(self.output_folder, str(año))
            crear_estructura_carpetas(año_dir)
            logger_usuario.info(f"Carpeta de resultados para el año {año}: {año_dir}")
            
            # Solicitar al usuario que seleccione el archivo CSV si no se proporcionó
            if csv_file is None:
                csv_file = self.seleccionar_archivo_csv()
            
            # Verificar que el archivo CSV existe
            try:
                self.verificar_archivo_clientes(csv_file)
                logger_usuario.info(f"Usando archivo de contribuyentes: {csv_file}")
            except FileNotFoundError:
                logger_usuario.info(f"Error: El archivo '{csv_file}' no existe.")
                print(f"\nError: No se encontró el archivo '{csv_file}'.")
                print("Por favor, asegúrese de que el archivo existe en la ubicación especificada.")
                print("Se ha creado un archivo de ejemplo que puede usar como referencia.")
                return
            except Exception as e:
                logger_usuario.info(f"Error al cargar archivo de contribuyentes: {e}")
                print(f"\nError: No se pudo cargar el archivo de contribuyentes '{csv_file}'.")
                print("Asegúrese de que el archivo exista y tenga formato CSV válido con las columnas: nombre,cuit,clave_fiscal")
                print("Se ha creado un archivo de ejemplo que puede usar como referencia.")
                return
            
            # Leer contribuyentes
            try:
                contribuyentes = self.leer_contribuyentes(csv_file)
                logger_usuario.info(f"Se encontraron {len(contribuyentes)} contribuyentes para procesar")
            except ValueError as e:
                logger_usuario.info(f"Error en el formato del archivo CSV: {e}")
                print(f"\nError en el formato del archivo CSV: {e}")
                print("El archivo debe tener formato CSV válido con las columnas: nombre,cuit,clave_fiscal")
                print("Verifique que todas las columnas estén presentes y que los datos sean correctos.")
                return
            except Exception as e:
                logger_usuario.info(f"Error inesperado al leer contribuyentes: {e}")
                print(f"\nError inesperado al leer contribuyentes: {e}")
                print("Verifique que el archivo CSV tenga el formato correcto.")
                return
            
            # Procesar contribuyentes
            contribuyentes_procesados = 0
            contribuyentes_fallidos = 0
            
            for i, contribuyente in enumerate(contribuyentes, 1):
                nombre = contribuyente["nombre"]
                logger_usuario.info(f"Procesando contribuyente {i}/{len(contribuyentes)}: {nombre}")
                
                if self.procesar_contribuyente(contribuyente, año):
                    contribuyentes_procesados += 1
                    logger_usuario.info(f"✅ Contribuyente {nombre} procesado exitosamente")
                else:
                    contribuyentes_fallidos += 1
                    logger_usuario.info(f"❌ Error al procesar contribuyente {nombre}")
                    
                # Mostrar progreso
                print(f"Contribuyente {i}/{len(contribuyentes)} procesado: {contribuyente['nombre']}")
            
            # Mostrar resumen
            logger.info("==== RESUMEN DE EJECUCIÓN ====")
            logger.info(f"Contribuyentes procesados exitosamente: {contribuyentes_procesados}")
            logger.info(f"Contribuyentes con errores: {contribuyentes_fallidos}")
            logger.info("=============================")
            
            # Registrar resumen en el log del usuario
            logger_usuario.info("")
            logger_usuario.info("==== RESUMEN DE LA EXTRACCIÓN ====")
            logger_usuario.info(f"Total de contribuyentes: {len(contribuyentes)}")
            logger_usuario.info(f"Contribuyentes procesados exitosamente: {contribuyentes_procesados}")
            logger_usuario.info(f"Contribuyentes con errores: {contribuyentes_fallidos}")
            logger_usuario.info(f"Carpeta con los resultados: {os.path.join(self.output_folder, str(año))}")
            logger_usuario.info("=================================")
            
            print("\n\n====================================")
            print(f"EXTRACCIÓN FINALIZADA:")
            print(f"- Contribuyentes procesados: {contribuyentes_procesados}")
            print(f"- Contribuyentes con errores: {contribuyentes_fallidos}")
            print("====================================")
            print(f"Los resultados se encuentran en la carpeta: {os.path.join(self.output_folder, str(año))}")
            print(f"El registro de la operación se encuentra en: {archivo_log_usuario}")
            print("====================================\n")
            
            input("Presione ENTER para finalizar...")
            
        except Exception as e:
            logger.error(f"Error general en la ejecución: {e}")
            logger_usuario.info(f"❌ Error inesperado durante la ejecución: {e}")
            print(f"\nError inesperado: {e}")
            print(f"Se ha generado un archivo de log con los detalles en: {archivo_log_usuario}")
            input("\nPresione ENTER para salir...")
    
    def solicitar_año(self):
        """Solicita y valida el año a evaluar"""
        print("\n==== AFIP EXTRACTOR ====")
        print(f"Años disponibles: {', '.join(self.años_disponibles)}")
        
        while True:
            año = input("¿Qué año desea evaluar? ")
            if año in self.años_disponibles:
                return año
            else:
                print(f"Año no válido. Por favor, elija entre: {', '.join(self.años_disponibles)}")
    
    def mostrar_banner(self):
        """Muestra un banner de bienvenida"""
        banner = """
        ╔═══════════════════════════════════════════╗
        ║          AFIP NUESTRA PARTE               ║
        ║   Sistema de extracción de información    ║
        ║     de "Nuestra Parte" desde AFIP         ║
        ╚═══════════════════════════════════════════╝
        
        """
        print(banner)
        print("INSTRUCCIONES:")
        print("1. Prepare un archivo CSV llamado 'clientes.csv' con las columnas: nombre,cuit,clave_fiscal")
        print("2. El archivo debe tener formato CSV válido con los datos separados por comas")
        print("3. Asegúrese de que el archivo contenga los datos correctos de cada contribuyente")
        print("\nIMPORTANTE: Este programa extrae información de la sección 'Nuestra Parte' de AFIP")
        print("=======================================================================\n")

    def verificar_archivo_clientes(self, csv_file="clientes.csv"):
        """Verifica que exista el archivo de clientes CSV"""
        ruta_listado = os.path.join(self.directorio_actual, csv_file)
        try:
            with open(ruta_listado, "r") as f:
                return ruta_listado
        except FileNotFoundError:
            logger.error(f"El archivo {csv_file} no se encuentra en el directorio actual")
            print(f"ERROR: No se encontró el archivo {csv_file}")
            print("Creando archivo de ejemplo...")
            
            # Crear archivo de ejemplo
            ejemplo_csv = os.path.join(self.directorio_actual, "clientes_ejemplo.csv")
            if CSVHandler.crear_csv_ejemplo(ejemplo_csv):
                print(f"Se creó un archivo de ejemplo en {ejemplo_csv}")
                print("Por favor, edite este archivo con sus datos y renómbrelo a 'clientes.csv'")
                print("Asegúrese de mantener el formato CSV correcto (valores separados por comas)")
            
            raise
        except Exception as e:
            logger.error(f"Error al abrir el archivo de listado: {e}")
            raise

    def handle_save_dialog(self, filename):
        """
        Maneja el diálogo de guardado archivo nativo del sistema.
        
        Args:
            filename: Nombre completo del archivo con ruta (sin extensión .pdf)
        
        Returns:
            bool: True si el manejo parece exitoso, False en caso contrario
        """
        logger.info(f"Intentando guardar como: {filename}")
        
        # Asegurarse de que la ruta tenga la extensión .pdf
        if not filename.lower().endswith('.pdf'):
            filename = f"{filename}.pdf"
            
        logger.info(f"Ruta completa del archivo (longitud: {len(filename)}): {filename}")
        
        # Si estamos en WSL, usar manejador específico que usa xdotool
        if self.is_wsl:
            logger.info("Detectado WSL, usando enfoque específico con xdotool")
            return self.handle_save_dialog_wsl(filename)
        
        # Para sistemas no-WSL, usar enfoque con ActionChains
        try:
            # Crear todos los directorios necesarios en la ruta de destino
            dir_path = os.path.dirname(filename)
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"Directorios creados: {dir_path}")
            except Exception as e:
                logger.warning(f"Error al crear directorios: {e}")
            
            # Esperar un momento antes de interactuar con el diálogo
            logger.info("Esperando a que el diálogo de impresión esté listo")
            time.sleep(3.0)
            
            # Presionar Enter para activar el diálogo de guardar 
            logger.info("Presionando Enter para activar el diálogo de guardado archivo")
            webdriver.ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            
            # Esperar más tiempo a que aparezca el explorador de archivos
            logger.info("Esperando a que aparezca el explorador de archivos")
            time.sleep(3.0)
            
            # Usar el atajo Ctrl+A para seleccionar todo el texto actual
            webdriver.ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            time.sleep(1.0)
            
            # Escribir la ruta completa con extensión .pdf
            logger.info(f"Escribiendo ruta completa: {filename}")
            webdriver.ActionChains(self.driver).send_keys(filename).perform()
            time.sleep(1.5)
            
            # Presionar Enter para guardar (sin esperar confirmación del usuario)
            logger.info("Presionando Enter para guardar")
            webdriver.ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            
            # Esperar más tiempo a que se complete el guardado y se cierren las ventanas
            logger.info(f"Esperando a que se guarde el archivo en: {filename}")
            time.sleep(5.0)
            
            # Verificar si el archivo se guardó correctamente
            if os.path.exists(filename):
                logger.info(f"Archivo guardado correctamente en: {filename}")
                return True
            else:
                logger.warning(f"No se encontró el archivo guardado en: {filename}")
                # Verificar en caso de que se haya guardado con otro nombre similar
                try:
                    dir_files = os.listdir(dir_path)
                    base_name = os.path.basename(filename).lower()
                    matching_files = [f for f in dir_files if f.lower() == base_name]
                    if matching_files:
                        logger.info(f"Se encontró un archivo similar: {os.path.join(dir_path, matching_files[0])}")
                        return True
                except Exception as e:
                    logger.warning(f"Error al verificar archivos similares: {e}")
            
            # Si llegamos aquí, el archivo no se guardó o no pudimos verificarlo
            logger.warning("No se pudo confirmar que el archivo se guardó correctamente")
            return True  # Asumimos que el proceso funcionó para continuar con las siguientes tablas
            
        except Exception as e:
            logger.error(f"Error al manejar diálogo de guardado: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Intentar con Escape para cerrar ambas ventanas (diálogo y ventana de impresión)
            try:
                logger.info("Intentando cerrar diálogo con Escape")
                webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
                webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            except Exception as esc_error:
                logger.warning(f"Error al enviar ESCAPE: {esc_error}")
                
            return True  # Devolvemos True para continuar con otras tablas a pesar del error
    
    def handle_save_dialog_wsl(self, filename):
        """
        Maneja el diálogo de guardado para WSL utilizando xdotool.
        Este método es específico para entornos WSL.
        """
        logger.info(f"WSL: Manejando diálogo de guardado con xdotool")
        try:
            # Presionar Enter para activar el diálogo de guardado archivo
            logger.info("WSL: Presionando Enter para activar el diálogo")
            subprocess.run(["xdotool", "key", "Return"], check=True)
            time.sleep(2.0)  # Esperar a que aparezca el explorador de archivos
            
            # Usar xdotool para seleccionar todo y escribir la ruta
            logger.info(f"WSL: Seleccionando todo el texto con Ctrl+A")
            subprocess.run(["xdotool", "key", "ctrl+a"], check=True)
            time.sleep(0.5)
            
            # Escribir la ruta completa del archivo en el diálogo de guardado
            logger.info(f"WSL: Escribiendo ruta completa: {filename}")
            
            # Crear las carpetas necesarias en la ruta
            dir_path = os.path.dirname(filename)
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"WSL: Se aseguró que el directorio existe: {dir_path}")
            except Exception as e:
                logger.warning(f"WSL: Error al crear directorios: {e}")
            
            # Escribir la ruta - Usamos xdotool para asegurarnos de que funcione en WSL
            logger.info(f"WSL: Escribiendo ruta completa en el diálogo: {filename}")
            subprocess.run(["xdotool", "type", filename], check=True)
            time.sleep(1.0)
            
            # Presionar Enter para guardar (sin esperar confirmación del usuario)
            logger.info("WSL: Presionando Enter para confirmar guardado")
            subprocess.run(["xdotool", "key", "Return"], check=True)
            
            # No es necesario manejar diálogos adicionales o verificar ventanas
            # El guardado y cierre de ventanas ocurre automáticamente
            logger.info("WSL: Esperando a que se complete el guardado y se cierren las ventanas")
            time.sleep(3.0)  # Esperar a que se complete el guardado
            
            # Verificar si el archivo se guardó correctamente (solo para logs)
            if os.path.exists(filename):
                logger.info(f"WSL: Archivo guardado exitosamente en: {filename}")
            else:
                logger.warning(f"WSL: No se encontró el archivo en: {filename}")
                # Verificar en caso de que se haya guardado con otro nombre similar
                try:
                    dir_files = os.listdir(dir_path)
                    base_name = os.path.basename(filename).lower()
                    matching_files = [f for f in dir_files if f.lower().startswith(base_name[:20])]
                    if matching_files:
                        logger.info(f"WSL: Se encontraron archivos similares: {matching_files}")
                except Exception as check_error:
                    logger.warning(f"WSL: Error al verificar archivos similares: {check_error}")
            
            # Asumimos que la ventana de impresión y el explorador se han cerrado
            # y que hemos vuelto automáticamente a la página de tablas
            logger.info("WSL: Se asume que hemos vuelto a la página principal")
            return True
                
        except Exception as e:
            logger.error(f"WSL: Error al manejar diálogo de guardado: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # En caso de error, intentar volver a la página principal
            try:
                # Enviar Escape para cerrar cualquier diálogo abierto
                subprocess.run(["xdotool", "key", "Escape"], check=True)
                time.sleep(0.5)
                subprocess.run(["xdotool", "key", "Escape"], check=True)
                logger.info("WSL: Intento de volver a la página principal después de error")
            except Exception as e2:
                logger.error(f"WSL: Error adicional: {e2}")
            
            # Retornar True para continuar con las siguientes tablas a pesar del error
            return True

    def esperar_nueva_ventana(self, driver, ventanas_antes, mensaje, max_intentos=3):
        """
        Espera a que aparezca una nueva ventana y cambia a ella.
        
        Args:
            driver: El driver de Selenium.
            ventanas_antes: Lista de handles de ventanas antes de la acción.
            mensaje: Mensaje para el log.
            max_intentos: Número máximo de intentos.
            
        Returns:
            bool: True si se pudo cambiar a la nueva ventana, False en caso contrario.
        """
        logger.info(f"{mensaje} (esperando 2 segundos)")
        time.sleep(2)  # Esperar un tiempo inicial
        
        ventanas_despues = driver.window_handles
        nuevas_ventanas = [w for w in ventanas_despues if w not in ventanas_antes]
        
        if nuevas_ventanas:
            nueva_ventana = nuevas_ventanas[0]
            logger.info(f"Detectada nueva ventana. Cambiando a: {nueva_ventana}")
            driver.switch_to.window(nueva_ventana)
            return True
        else:
            logger.warning(f"No se detectaron nuevas ventanas, pero continuaremos igualmente.")
            return True  # Siempre retornamos True para continuar con el proceso
    
    def esperar_url_contenga(self, driver, texto, mensaje="Esperando URL", max_intentos=5):
        """
        Espera a que la URL contenga un texto específico.
        
        Args:
            driver: WebDriver de Selenium
            texto: Texto que debe contener la URL
            mensaje: Mensaje para los logs
            max_intentos: Número máximo de intentos
            
        Returns:
            bool: True si la URL contiene el texto, False en caso contrario
        """
        def _condition():
            return texto in driver.current_url
        
        return self.esperar_con_intentos(
            _condition, 
            mensaje=f"{mensaje} (contiene '{texto}')", 
            max_intentos=max_intentos
        )

    def recuperar_ventana_tablas(self, tablas_url, tablas_handle, ventanas_antes):
        """
        Intenta recuperar la ventana de tablas original después de procesar un PDF.
        
        Args:
            tablas_url: URL de la ventana de tablas
            tablas_handle: Handle de la ventana de tablas
            ventanas_antes: Lista de handles de ventanas antes de abrir el PDF
            
        Returns:
            WebDriver: El driver con la ventana de tablas activa
        """
        logger.info("Intentando recuperar la ventana de tablas")
        
        try:
            # Verificar si la ventana original todavía existe
            ventanas_actuales = self.driver.window_handles
            
            # Si solo queda una ventana, ya estamos en la correcta
            if len(ventanas_actuales) == 1:
                logger.info("Solo queda una ventana abierta, asumiendo que es la correcta")
                return self.driver
                
            # Intentar cambiar a la ventana original por su handle
            if tablas_handle in ventanas_actuales:
                logger.info(f"Cambiando a la ventana original con handle: {tablas_handle}")
                self.driver.switch_to.window(tablas_handle)
                return self.driver
                
            # Si la ventana original no existe, intentar encontrar otra con la URL correcta
            for handle in ventanas_actuales:
                try:
                    self.driver.switch_to.window(handle)
                    if tablas_url in self.driver.current_url:
                        logger.info(f"Encontrada ventana con URL similar: {self.driver.current_url}")
                        return self.driver
                except Exception:
                    continue
                    
            # Si llegamos aquí, no encontramos la ventana original
            # Usar la primera ventana disponible
            logger.warning("No se encontró la ventana original, usando la primera disponible")
            self.driver.switch_to.window(ventanas_actuales[0])
            return self.driver
            
        except Exception as e:
            logger.error(f"Error al recuperar ventana de tablas: {e}")
            # En caso de error, intentar usar la primera ventana disponible
            try:
                ventanas_actuales = self.driver.window_handles
                if ventanas_actuales:
                    self.driver.switch_to.window(ventanas_actuales[0])
            except Exception:
                pass
            return self.driver

    def close(self):
        """Cerrar el navegador y limpiar temporales."""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
                logger.info("Navegador cerrado correctamente")
            except Exception as e:
                logger.warning(f"Error al cerrar el navegador: {e}")
            finally:
                # Asegurar que se liberen los recursos
                if hasattr(self, 'directorio_temporal') and os.path.exists(self.directorio_temporal):
                    try:
                        shutil.rmtree(self.directorio_temporal)
                        logger.info("Directorio temporal eliminado correctamente")
                    except Exception as e:
                        logger.warning(f"Error al eliminar directorio temporal: {e}")
    
    def normalizar_nombre(self, nombre):
        """
        Normaliza el nombre de un archivo o carpeta.
        Esta función ahora redirecciona a utils.file_utils.normalizar_nombre
        
        Args:
            nombre: Nombre a normalizar
            
        Returns:
            str: Nombre normalizado
        """
        from utils.file_utils import normalizar_nombre as norm
        return norm(nombre)

    def seleccionar_archivo_csv(self, default_filename="clientes.csv"):
        """
        Permite al usuario seleccionar un archivo CSV mediante un explorador de archivos.
        
        Args:
            default_filename (str): Nombre del archivo por defecto
            
        Returns:
            str: Ruta al archivo seleccionado o valor predeterminado si se canceló
        """
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            logger.info("Abriendo explorador de archivos para seleccionar CSV")
            
            # Inicializar Tkinter sin mostrar la ventana principal
            root = tk.Tk()
            root.withdraw()
            
            # Preparar el diálogo de selección
            filetypes = [("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
            initialdir = os.getcwd()
            
            print("\nPor favor, seleccione el archivo CSV con los datos de los contribuyentes...")
            
            # Mostrar el diálogo y obtener la selección
            archivo_seleccionado = filedialog.askopenfilename(
                title="Seleccionar archivo CSV",
                initialdir=initialdir,
                initialfile=default_filename,
                filetypes=filetypes
            )
            
            # Cerrar Tkinter
            root.destroy()
            
            # Procesar el resultado
            if archivo_seleccionado:
                logger.info(f"Archivo seleccionado: {archivo_seleccionado}")
                return archivo_seleccionado
            
            # Si no se seleccionó nada, usar el predeterminado
            logger.info(f"No se seleccionó ningún archivo, usando el predeterminado: {default_filename}")
            return os.path.join(self.directorio_actual, default_filename)
            
        except Exception as e:
            # Manejar cualquier error
            logger.error(f"Error al abrir el explorador de archivos: {e}")
            print(f"\nNo se pudo abrir el explorador de archivos: {e}")
            print(f"Se usará el archivo predeterminado: {default_filename}")
            return os.path.join(self.directorio_actual, default_filename)

def parse_arguments():
    """Parsea los argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description="AFIP Nuestra Parte - Extracción de información fiscal")
    
    parser.add_argument(
        "--year", "-y",
        help="Año a procesar (opciones disponibles desde 2018 al año actual)",
        type=str,
        default=None
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Archivo CSV con datos de contribuyentes (si no se especifica, se mostrará un diálogo para seleccionarlo)",
        type=str,
        default=None
    )
    
    parser.add_argument(
        "--select-file",
        help="Mostrar diálogo para seleccionar archivo CSV",
        action="store_true"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    extractor = None
    try:
        args = parse_arguments()
        extractor = NuestraParteExtractor()
        
        # Si se especificó --select-file, ignorar el valor de --file
        csv_file = None if args.select_file else args.file
        
        extractor.ejecutar(año=args.year, csv_file=csv_file)
    except Exception as e:
        logging.error(f"Error general en la aplicación: {e}")
        print(f"\nError inesperado: {e}")
        print("Se ha generado un archivo de log con los detalles.")
    finally:
        if extractor:
            extractor.close()  # Clean up resources even if an exception occurs
        input("\nPresione ENTER para salir...") 