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

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Importar el manejador de CSV
from csv_utils import CSVHandler

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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("afip_extractor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AFIP Extractor")

class NuestraParteExtractor:
    def __init__(self):
        self.directorio_actual = os.getcwd()
        # Actualizar lista de años desde 2018 hasta el año actual
        current_year = datetime.now().year
        self.años_disponibles = [str(year) for year in range(2018, current_year + 1)]
        self.output_folder = os.path.join(os.path.expanduser('~'), "Desktop", "AFIP_Resultados")
        
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
        
        # Crear un directorio temporal para descargas en el escritorio
        self.download_dir = os.path.join("/tmp", "AFIP_temp_downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        logger.info(f"Directorio de descargas configurado en: {self.download_dir}")
        
    def setup_driver(self):
        """Configura y devuelve el driver de Chrome con opciones optimizadas"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Configuración para manejar PDFs
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Habilitar guardado de PDF directamente
        prefs = {
            "download.default_directory": self.download_dir,
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
    
    def crear_estructura_carpetas(self):
        """Crea la carpeta principal donde se guardarán los resultados"""
        try:
            os.makedirs(self.output_folder, exist_ok=True)
            logger.info(f"Carpeta {self.output_folder} creada exitosamente")
        except Exception as e:
            logger.error(f"Error al crear carpeta {self.output_folder}: {e}")
            raise
    
    def leer_contribuyentes(self, csv_file="clientes.csv"):
        """Lee la lista de contribuyentes desde un archivo CSV
        
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
    
    def iniciar_sesion(self, driver, cuit, clave_fiscal):
        """Inicia sesión en el sitio de AFIP"""
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
    
    def navegacion_alternativa(self, driver):
        """Intenta una navegación alternativa a Nuestra Parte"""
        logger.info("Intentando navegación alternativa directa a URL de Nuestra Parte...")
        try:
            driver.get("https://serviciosjava2.afip.gob.ar/cgpf/jsp/mostrarMenu.do")
            
            # Verificar si la URL contiene alguno de los fragmentos válidos
            url_despues_redireccion = driver.current_url
            logger.info(f"URL después de navegación directa: {url_despues_redireccion}")
            
            urls_validas = ["serviciosjava2.afip.gob.ar/cgpf", "nuestra-parte", "nuestraparte"]
            
            if any(fragmento in url_despues_redireccion.lower() for fragmento in urls_validas):
                logger.info("Navegación directa exitosa a Nuestra Parte")
                return True
            else:
                logger.error("La navegación directa también falló")
                return False
        except Exception as e:
            logger.error(f"Error durante la navegación directa: {e}")
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
            # Crear directorio de salida para este cuit si no existe
            contribuyente_dir = os.path.join(output_dir, cuit)
            os.makedirs(contribuyente_dir, exist_ok=True)
            
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
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", button)
                            logger.info(f"Se hizo clic en el botón del año {año}")
                            time.sleep(5)  # Esperar a que cargue la información del año
                            
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
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", recent_year)
                            logger.info(f"Se hizo clic en el año más reciente: {año_reciente}")
                            time.sleep(5)  # Esperar a que cargue la información del año
                            
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
                            time.sleep(2)
                            break
                        except:
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
                                time.sleep(2)
                                año_encontrado = True
                                break
                except Exception as e:
                    logger.error(f"Error en método alternativo: {e}")
            
            # Si aún no hemos encontrado el año, continuar con lo que esté disponible
            if not año_encontrado:
                logger.warning(f"No se pudo encontrar/seleccionar el año {año}, continuando con lo que esté disponible")
            
            # Crear directorio para este año
            año_dir = os.path.join(contribuyente_dir, f"año_{año}")
            os.makedirs(año_dir, exist_ok=True)
            
            # Procesar secciones de datos (ignorando declaraciones anteriores)
            self.procesar_secciones_datos(driver, año_dir)
            
            return True
            
        except Exception as e:
            logger.error(f"Error al procesar 'Nuestra Parte': {e}")
            return False
    
    def procesar_secciones_datos(self, driver, output_dir):
        """
        Procesa todas las secciones de datos disponibles en la página de Nuestra Parte.
        Para cada sección, crea una carpeta y captura los PDFs haciendo clic en los íconos de impresión.
        
        Args:
            driver: WebDriver de Selenium
            output_dir: Directorio donde guardar los resultados
        """
        try:
            # Esperar a que la página cargue completamente usando un método dinámico
            logger.info("Esperando a que la página cargue completamente...")
            
            # Función que verifica si las secciones están cargadas
            def secciones_cargadas():
                try:
                    # Buscar secciones en la página
                    secciones = driver.find_elements(By.CSS_SELECTOR, "div.div-container-grey")
                    # Verificar si hay al menos una sección y que no hay indicadores de carga
                    return len(secciones) > 0 and "cargando" not in driver.page_source.lower()
                except:
                    return False
            
            # Esperar a que las secciones se carguen con un máximo de 10 intentos (1s cada uno)
            if not self.esperar_con_intentos(secciones_cargadas, "Esperando carga de secciones", max_intentos=10):
                logger.warning("No se pudo confirmar que las secciones están cargadas, continuando de todas formas")
            
            # Procesar las secciones principales (div-container-grey con span dentro)
            self.procesar_secciones_principales(driver, output_dir)
            
            # No procesar spans individuales que pertenezcan a otros servicios
            logger.info("Procesamiento de secciones completado")
            
        except Exception as e:
            logger.error(f"Error general al procesar secciones: {e}")
    
    def procesar_secciones_principales(self, driver, output_dir):
        """Procesa las secciones principales de la página de Nuestra Parte"""
        # Guardar una referencia al driver para usar en otros métodos
        self.driver = driver
        
        try:
            # Encontrar todas las secciones (div-container-grey)
            secciones_containers = driver.find_elements(By.CSS_SELECTOR, "div.div-container-grey")
            
            if not secciones_containers:
                logger.warning("No se encontraron secciones principales en la página")
                return
                
            logger.info(f"Se encontraron {len(secciones_containers)} secciones principales")
            
            # Verificar si la sección es "Declaraciones juradas del periodo anterior" para ignorarla
            for idx, seccion_container in enumerate(secciones_containers, 1):
                try:
                    # Obtener el título de la sección
                    span_titulo = seccion_container.find_element(By.CSS_SELECTOR, "span")
                    titulo_seccion = span_titulo.text.strip()
                    logger.info(f"Procesando sección principal: {titulo_seccion}")
                    
                    # Ignorar si es la sección de "Declaraciones juradas del periodo anterior"
                    if "declaraciones juradas del periodo anterior" in titulo_seccion.lower():
                        logger.info(f"Ignorando sección: {titulo_seccion}")
                        continue
                    
                    # Crear directorio para esta sección
                    seccion_dir = os.path.join(output_dir, f"{self.normalizar_nombre(titulo_seccion)}")
                    os.makedirs(seccion_dir, exist_ok=True)
                    
                    # Buscar todos los íconos (elementos clickeables) dentro de esta sección
                    try:
                        icons = seccion_container.find_elements(By.CSS_SELECTOR, ".circleIcon i.btn-consultar")
                        logger.info(f"Se encontraron {len(icons)} íconos en la sección principal {titulo_seccion}")
                        
                        # Para cada ícono, hacer clic y procesar su contenido
                        for icon_idx, icon in enumerate(icons, 1):
                            try:
                                # Obtener el nombre del elemento a partir del párrafo adyacente
                                try:
                                    nombre_elemento = icon.find_element(By.XPATH, "./following-sibling::p").text.strip()
                                except:
                                    try:
                                        # Si no funciona, intentar obtenerlo del elemento padre
                                        nombre_elemento = icon.find_element(By.XPATH, "../p").text.strip()
                                    except:
                                        nombre_elemento = f"elemento_{icon_idx}"
                                
                                logger.info(f"Procesando elemento: {nombre_elemento}")
                                
                                # Hacer clic en el ícono con reintentos
                                icon_click_success = self.click_con_reintentos(driver, icon, f"ícono de {nombre_elemento}")
                                if not icon_click_success:
                                    logger.warning(f"No se pudo hacer clic en el ícono de {nombre_elemento}, continuando con el siguiente")
                                    continue
                                
                                # Esperar a que se carguen los datos (función específica)
                                def datos_cargados():
                                    try:
                                        # Buscar elementos que indiquen que los datos están cargados (por ejemplo, tablas o botones de impresión)
                                        print_icons = driver.find_elements(By.CSS_SELECTOR, "a.btn-imprimir, i.fa-print")
                                        tables = driver.find_elements(By.CSS_SELECTOR, "table")
                                        return len(print_icons) > 0 or len(tables) > 0
                                    except:
                                        return False
                                
                                datos_loaded = self.esperar_con_intentos(
                                    datos_cargados,
                                    mensaje=f"Esperando datos para {nombre_elemento}",
                                    max_intentos=10  # Más intentos aquí, ya que la carga puede ser más lenta
                                )
                                
                                if not datos_loaded:
                                    logger.warning(f"No se pudieron cargar los datos para {nombre_elemento}")
                                
                                # Buscar íconos de impresión para guardar PDFs
                                try:
                                    # Buscar todos los íconos de impresión que estén visibles
                                    print_icons = driver.find_elements(By.CSS_SELECTOR, "a.btn-imprimir, i.fa-print")
                                    visible_print_icons = [icon for icon in print_icons if icon.is_displayed()]
                                    
                                    logger.info(f"Se encontraron {len(visible_print_icons)} íconos de impresión en {nombre_elemento}")
                                    
                                    for print_idx, print_icon in enumerate(visible_print_icons, 1):
                                        try:
                                            # Obtener el título de la tabla/sección
                                            try:
                                                # Encontrar el encabezado h3 más cercano
                                                h3_element = print_icon.find_element(By.XPATH, "../h3")
                                                titulo_tabla = h3_element.text.strip()
                                            except:
                                                titulo_tabla = f"tabla_{print_idx}"
                                            
                                            logger.info(f"Procesando tabla: {titulo_tabla}")
                                            
                                            # Crear nombre de archivo para este PDF
                                            pdf_filename = f"{self.normalizar_nombre(nombre_elemento)}_{self.normalizar_nombre(titulo_tabla)}_{print_idx}.pdf"
                                            pdf_path = os.path.join(seccion_dir, pdf_filename)
                                            
                                            # Asegurarse de que la carpeta existe
                                            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                                            
                                            # Guardar como PDF usando el botón de impresión con reintentos
                                            try:
                                                # Almacenar las ventanas antes de hacer clic
                                                ventanas_antes = driver.window_handles
                                                
                                                # Hacer clic en el botón de impresión con reintentos
                                                print_click_success = self.click_con_reintentos(driver, print_icon, f"botón de impresión para {titulo_tabla}")
                                                if not print_click_success:
                                                    logger.warning(f"No se pudo hacer clic en el botón de impresión para {titulo_tabla}, continuando con el siguiente")
                                                    continue
                                                
                                                # Esperar a que se abra la ventana de impresión
                                                ventana_detectada = self.esperar_nueva_ventana(
                                                    driver, 
                                                    ventanas_antes,
                                                    mensaje=f"Esperando ventana de impresión para {titulo_tabla}",
                                                    max_intentos=10
                                                )
                                                
                                                if ventana_detectada:
                                                    # Preparar el nombre del archivo para el diálogo (sin .pdf)
                                                    if pdf_path.lower().endswith('.pdf'):
                                                        dialog_filename = pdf_path[:-4]  # Quitar la extensión .pdf
                                                    else:
                                                        dialog_filename = pdf_path
                                                    
                                                    # Usar la ruta completa donde queremos guardar el archivo
                                                    logger.info(f"Utilizando diálogo nativo para guardar como: {pdf_path}")
                                                    guardado_exitoso = self.handle_save_dialog(dialog_filename)
                                                    
                                                    # La ventana debería cerrarse automáticamente después de guardar
                                                    logger.info("Esperando cierre automático de la ventana de impresión")
                                                    time.sleep(4)  # Aumentado de 2 a 4 segundos
                                                    
                                                    # Verificar el estado de las ventanas después de guardar
                                                    try:
                                                        handles = driver.window_handles
                                                        logger.info(f"Ventanas activas después de guardar: {len(handles)}")
                                                        
                                                        # Si seguimos en la ventana de impresión, intentar cerrarla
                                                        if len(handles) > 1:
                                                            current_url = driver.current_url
                                                            if "print" in current_url:
                                                                logger.info("Detectada ventana de impresión abierta, intentando cerrarla")
                                                                driver.close()
                                                                time.sleep(1)
                                                            
                                                            # Volver a la ventana principal
                                                            driver.switch_to.window(ventanas_antes[0])
                                                            logger.info("Volviendo a la ventana principal")
                                                    except Exception as e:
                                                        logger.warning(f"Error al verificar estado de ventanas: {e}")
                                            except Exception as e:
                                                logger.warning(f"Error al guardar como PDF: {e}")
                                                # Intentar volver a la ventana principal en caso de error
                                                try:
                                                    if len(driver.window_handles) > 1:
                                                        driver.switch_to.window(ventanas_antes[0])
                                                except Exception as win_error:
                                                    logger.error(f"Error al volver a ventana principal: {win_error}")
                                            
                                        except Exception as e:
                                            logger.error(f"Error al procesar ícono de impresión {print_idx} en {nombre_elemento}: {e}")
                                            continue
                                            
                                except Exception as e:
                                    logger.error(f"Error al buscar íconos de impresión en {nombre_elemento}: {e}")
                                
                                # También capturamos tablas existentes en caso de que no tengan iconos de impresión
                                try:
                                    # Buscar todas las tablas visibles en la página actual
                                    tablas = driver.find_elements(By.CSS_SELECTOR, "table")
                                    tablas_visibles = [tabla for tabla in tablas if tabla.is_displayed()]
                                    
                                    if tablas_visibles:
                                        logger.info(f"Se encontraron {len(tablas_visibles)} tablas adicionales en {nombre_elemento}")
                                        
                                        # Buscar botones de impresión específicos para la tabla o página actual
                                        botones_imprimir = driver.find_elements(By.CSS_SELECTOR, ".btn-imprimir, .icon-print, i.fa-print")
                                        if botones_imprimir:
                                            for btn_idx, boton in enumerate(botones_imprimir, 1):
                                                if boton.is_displayed():
                                                    logger.info(f"Encontrado botón de impresión adicional {btn_idx}")
                                                    
                                                    # Crear nombre para el archivo PDF
                                                    pdf_filename = f"{self.normalizar_nombre(nombre_elemento)}_adicional_{btn_idx}.pdf"
                                                    pdf_path = os.path.join(seccion_dir, pdf_filename)
                                                    
                                                    # Hacer clic y guardar usando el método normal
                                                    ventanas_antes = driver.window_handles
                                                    if self.click_con_reintentos(driver, boton, f"botón de impresión adicional {btn_idx}"):
                                                        # Esperar a que se abra la ventana de impresión
                                                        ventana_detectada = self.esperar_nueva_ventana(
                                                            driver, 
                                                            ventanas_antes,
                                                            mensaje=f"Esperando ventana de impresión para tabla adicional {btn_idx}",
                                                            max_intentos=10
                                                        )
                                                        
                                                        if ventana_detectada:
                                                            # Preparar el nombre del archivo sin extensión
                                                            if pdf_path.lower().endswith('.pdf'):
                                                                dialog_filename = pdf_path[:-4]
                                                            else:
                                                                dialog_filename = pdf_path
                                                                
                                                            logger.info(f"Utilizando diálogo nativo para guardar como: {pdf_path}")
                                                            guardado_exitoso = self.handle_save_dialog(dialog_filename)
                                                            
                                                            # La ventana debería cerrarse automáticamente después de guardar
                                                            logger.info("Esperando cierre automático de la ventana de impresión")
                                                            time.sleep(4)
                                                            
                                                            # Verificar estado de ventanas
                                                            try:
                                                                handles = driver.window_handles
                                                                logger.info(f"Ventanas activas después de guardar adicional: {len(handles)}")
                                                                
                                                                # Si seguimos en la ventana de impresión, intentar cerrarla
                                                                if len(handles) > 1:
                                                                    current_url = driver.current_url
                                                                    if "print" in current_url:
                                                                        logger.info("Detectada ventana de impresión abierta, intentando cerrarla")
                                                                        driver.close()
                                                                        time.sleep(1)
                                                                    
                                                                    # Volver a la ventana principal
                                                                    driver.switch_to.window(ventanas_antes[0])
                                                                    logger.info("Volviendo a la ventana principal")
                                                            except Exception as e:
                                                                logger.warning(f"Error al verificar estado de ventanas adicionales: {e}")
                                        else:
                                            logger.info("No se encontraron botones de impresión adicionales, no se capturarán tablas que no tienen iconos de impresión")
                                                
                                except Exception as e:
                                    logger.error(f"Error al buscar tablas adicionales en {nombre_elemento}: {e}")
                                
                                # Buscar el botón de cerrar para volver a la vista principal
                                try:
                                    cerrar_btn = driver.find_element(By.CSS_SELECTOR, f"a.btn-cerrar[data-trigger='{icon.get_attribute('data-trigger')}']")
                                    cerrar_click_success = self.click_con_reintentos(driver, cerrar_btn, f"botón cerrar para {nombre_elemento}")
                                    if not cerrar_click_success:
                                        logger.warning(f"No se pudo hacer clic en el botón cerrar para {nombre_elemento}, intentando con ESCAPE")
                                        # Intentar presionar ESC para cerrar si el botón no funciona
                                        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                                except Exception as e:
                                    logger.error(f"Error al cerrar la vista de {nombre_elemento}: {e}")
                                    # Intentar presionar ESC para cerrar si el botón no funciona
                                    try:
                                        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                                    except:
                                        pass
                            
                            except Exception as e:
                                logger.error(f"Error al procesar ícono {icon_idx} en la sección {titulo_seccion}: {e}")
                                # Intentar recuperarse para el siguiente ícono
                                try:
                                    # Intentar volver al frame principal si estábamos en algún otro
                                    driver.switch_to.default_content()
                                    # Intentar cerrar cualquier ventana emergente
                                    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                                except:
                                    pass
                                continue
                                
                    except Exception as e:
                        logger.error(f"Error al buscar íconos en la sección {titulo_seccion}: {e}")
                        
                except Exception as e:
                    logger.error(f"Error al procesar sección {idx}: {e}")
                    continue
                    
            logger.info("Procesamiento de secciones completado")
            
        except Exception as e:
            logger.error(f"Error general al procesar secciones: {e}")
    
    def click_con_reintentos(self, driver, elemento, nombre_elemento, max_reintentos=3, espera_entre_intentos=1):
        """
        Realiza un click en un elemento con reintentos en caso de fallos.
        Retorna True si el click fue exitoso, False en caso contrario.
        """
        for intento in range(1, max_reintentos + 1):
            try:
                # Esperar a que el elemento sea clickeable
                if intento > 1:
                    logger.info(f"Reintento {intento} para hacer clic en {nombre_elemento}")
                
                # Intentar hacer scroll hacia el elemento para asegurar visibilidad
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
                    time.sleep(0.5)  # Breve pausa para que el scroll termine
                except Exception as e:
                    logger.warning(f"No se pudo hacer scroll hacia {nombre_elemento}: {e}")
                
                # Intentar hacer clic en el elemento
                elemento.click()
                logger.info(f"Clic exitoso en {nombre_elemento}")
                return True
                
            except Exception as e:
                logger.warning(f"Error al intentar hacer clic en {nombre_elemento} (intento {intento}): {e}")
                
                # Intentar clic mediante JavaScript como alternativa
                if intento == max_reintentos - 1:
                    try:
                        logger.info(f"Intentando clic mediante JavaScript en {nombre_elemento}")
                        driver.execute_script("arguments[0].click();", elemento)
                        logger.info(f"Clic mediante JavaScript exitoso en {nombre_elemento}")
                        return True
                    except Exception as js_error:
                        logger.warning(f"Error al intentar clic mediante JavaScript en {nombre_elemento}: {js_error}")
                
                # Esperar antes del siguiente intento
                if intento < max_reintentos:
                    time.sleep(espera_entre_intentos)
        
        logger.error(f"No se pudo hacer clic en {nombre_elemento} después de {max_reintentos} intentos")
        return False

    def esperar_con_intentos(self, condicion_funcion, mensaje, max_intentos=10, tiempo_espera=1):
        """
        Espera a que una condición representada por una función sin argumentos sea verdadera.
        La función debe retornar True cuando la condición se cumpla.
        Retorna True si la condición se cumplió, False en caso contrario.
        """
        for intento in range(1, max_intentos + 1):
            try:
                if condicion_funcion():
                    logger.info(f"{mensaje}: condición cumplida en el intento {intento}")
                    return True
                
                logger.info(f"{mensaje}: esperando... (intento {intento}/{max_intentos})")
                time.sleep(tiempo_espera)
                
            except Exception as e:
                logger.warning(f"Error en la función de condición para '{mensaje}' (intento {intento}): {e}")
                time.sleep(tiempo_espera)
        
        logger.error(f"{mensaje}: condición no cumplida después de {max_intentos} intentos")
        return False

    def esperar_elemento(self, driver, localizador, tiempo_espera=10, mensaje=None, max_intentos=1, clickable=False):
        """
        Espera a que un elemento esté presente en el DOM.
        Puede recibir un localizador CSS o una tupla (By.XXX, valor) como localizador.
        
        Args:
            driver: WebDriver de Selenium
            localizador: String con selector CSS o tupla (By.XXX, valor)
            tiempo_espera: Tiempo máximo de espera en segundos
            mensaje: Mensaje descriptivo del elemento para logs
            max_intentos: Número máximo de intentos
            clickable: Si es True, espera a que el elemento sea clickeable en lugar de solo presente
            
        Returns:
            El elemento encontrado o None si no se encuentra
        """
        nombre_elemento = mensaje or str(localizador)
        logger.info(f"Esperando elemento: {nombre_elemento} (máximo {tiempo_espera}s)")
        
        for intento in range(1, max_intentos + 1):
            try:
                # Determinar tipo de localizador
                if isinstance(localizador, tuple) and len(localizador) == 2:
                    # Es una tupla (By.XXX, valor)
                    by_type, value = localizador
                    wait = WebDriverWait(driver, tiempo_espera)
                    if clickable:
                        elemento = wait.until(EC.element_to_be_clickable((by_type, value)))
                    else:
                        elemento = wait.until(EC.presence_of_element_located((by_type, value)))
                else:
                    # Asumimos que es un selector CSS
                    wait = WebDriverWait(driver, tiempo_espera)
                    if clickable:
                        elemento = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, localizador)))
                    else:
                        elemento = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, localizador)))
                    
                logger.info(f"Elemento encontrado: {nombre_elemento}")
                return elemento
                    
            except TimeoutException:
                if intento < max_intentos:
                    logger.warning(f"Timeout esperando elemento: {nombre_elemento} (intento {intento}/{max_intentos})")
                    continue
                else:
                    logger.warning(f"Timeout esperando elemento: {nombre_elemento} después de {tiempo_espera}s x {max_intentos} intentos")
                    return None
            except Exception as e:
                if intento < max_intentos:
                    logger.warning(f"Error esperando elemento {nombre_elemento} (intento {intento}/{max_intentos}): {e}")
                    continue
                else:
                    logger.error(f"Error esperando elemento {nombre_elemento}: {e}")
                    return None
    
    def esperar_elementos(self, driver, localizador, tiempo_espera=10, mensaje=None, max_intentos=1):
        """
        Espera a que uno o más elementos estén presentes en el DOM.
        Puede recibir un localizador CSS o una tupla (By.XXX, valor) como localizador.
        
        Args:
            driver: WebDriver de Selenium
            localizador: String con selector CSS o tupla (By.XXX, valor)
            tiempo_espera: Tiempo máximo de espera en segundos
            mensaje: Mensaje descriptivo de los elementos para logs
            max_intentos: Número máximo de intentos
            
        Returns:
            Lista de elementos encontrados o lista vacía si no se encuentra ninguno
        """
        nombre_elementos = mensaje or str(localizador)
        logger.info(f"Esperando elementos: {nombre_elementos} (máximo {tiempo_espera}s)")
        
        for intento in range(1, max_intentos + 1):
            try:
                # Determinar tipo de localizador
                if isinstance(localizador, tuple) and len(localizador) == 2:
                    # Es una tupla (By.XXX, valor)
                    by_type, value = localizador
                    wait = WebDriverWait(driver, tiempo_espera)
                    elementos = wait.until(EC.presence_of_all_elements_located((by_type, value)))
                else:
                    # Asumimos que es un selector CSS
                    wait = WebDriverWait(driver, tiempo_espera)
                    elementos = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, localizador)))
                    
                logger.info(f"Elementos encontrados: {nombre_elementos} (cantidad: {len(elementos)})")
                return elementos
                
            except TimeoutException:
                if intento < max_intentos:
                    logger.warning(f"Timeout esperando elementos: {nombre_elementos} (intento {intento}/{max_intentos})")
                    continue
                else:
                    logger.warning(f"Timeout esperando elementos: {nombre_elementos} después de {tiempo_espera}s x {max_intentos} intentos")
                    return []
            except Exception as e:
                if intento < max_intentos:
                    logger.warning(f"Error esperando elementos {nombre_elementos} (intento {intento}/{max_intentos}): {e}")
                    continue
                else:
                    logger.error(f"Error esperando elementos {nombre_elementos}: {e}")
                    return []
    
    def normalizar_nombre(self, nombre):
        """
        Normaliza un nombre para usarlo como nombre de archivo o carpeta
        """
        # Reemplazar caracteres no válidos y espacios
        nombre_normalizado = nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
        nombre_normalizado = ''.join(c for c in nombre_normalizado if c.isalnum() or c in '_-.')
        return nombre_normalizado
    
    def procesar_contribuyente(self, contribuyente, año):
        """Procesa toda la información de un contribuyente"""
        nombre = contribuyente["nombre"]
        cuit = contribuyente["cuit"]
        clave_fiscal = contribuyente["clave_fiscal"]
        
        logger.info(f"Procesando contribuyente: {nombre}")
        
        # Crear carpeta para el contribuyente
        path_contribuyente = os.path.join(self.output_folder, nombre)
        try:
            os.makedirs(path_contribuyente, exist_ok=True)
            logger.info(f"Carpeta creada para contribuyente: {path_contribuyente}")
        except Exception as e:
            logger.error(f"Error al crear carpeta para {nombre}: {e}")
            return False
        
        # Iniciar driver
        driver = None
        try:
            driver = self.setup_driver()
            
            # Iniciar sesión
            if not self.iniciar_sesion(driver, cuit, clave_fiscal):
                with open(os.path.join(path_contribuyente, "error_login.txt"), "w") as f:
                    f.write("Error al intentar iniciar sesión. Verifique las credenciales.")
                logger.error(f"Error al iniciar sesión para {nombre}")
                return False
            
            # Procesar Nuestra Parte
            resultado = self.procesar_nuestra_parte(driver, cuit, año, path_contribuyente)
            
            if resultado:
                logger.info(f"Procesamiento de {nombre} completado exitosamente")
                return True
            else:
                logger.warning(f"No se pudo procesar Nuestra Parte para {nombre}")
                return False
                
        except Exception as e:
            logger.error(f"Error general procesando {nombre}: {e}")
            return False
        finally:
            # Siempre cerrar el driver cuando termine el procesamiento
            if driver:
                logger.info("Cerrando el navegador")
                driver.quit()
    
    def ejecutar(self, año=None, csv_file="clientes.csv"):
        """Función principal que inicia todo el proceso"""
        try:
            # Mostrar banner e instrucciones
            self.mostrar_banner()
            
            # Solicitar año a evaluar si no se proporcionó
            if año is None:
                año = self.solicitar_año()
                
            # Crear estructura de carpetas
            self.crear_estructura_carpetas()
            
            # Verificar que el archivo CSV existe
            self.verificar_archivo_clientes(csv_file)
            
            # Leer contribuyentes
            contribuyentes = self.leer_contribuyentes(csv_file)
            
            # Procesar contribuyentes
            contribuyentes_procesados = 0
            contribuyentes_fallidos = 0
            
            for i, contribuyente in enumerate(contribuyentes, 1):
                if self.procesar_contribuyente(contribuyente, año):
                    contribuyentes_procesados += 1
                else:
                    contribuyentes_fallidos += 1
                    
                # Mostrar progreso
                print(f"Contribuyente {i}/{len(contribuyentes)} procesado: {contribuyente['nombre']}")
            
            # Mostrar resumen
            logger.info("==== RESUMEN DE EJECUCIÓN ====")
            logger.info(f"Contribuyentes procesados exitosamente: {contribuyentes_procesados}")
            logger.info(f"Contribuyentes con errores: {contribuyentes_fallidos}")
            logger.info("=============================")
            
            print("\n\n====================================")
            print(f"EXTRACCIÓN FINALIZADA:")
            print(f"- Contribuyentes procesados: {contribuyentes_procesados}")
            print(f"- Contribuyentes con errores: {contribuyentes_fallidos}")
            print("====================================")
            print(f"Los resultados se encuentran en la carpeta: {self.output_folder}")
            print("====================================\n")
            
            input("Presione ENTER para finalizar...")
            
        except Exception as e:
            logger.error(f"Error general en la ejecución: {e}")
            print(f"\nError inesperado: {e}")
            input("\nPresione ENTER para finalizar...")
    
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
        print("2. Asegúrese de que el archivo contenga los datos correctos de cada contribuyente")
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
            
            raise
        except Exception as e:
            logger.error(f"Error al abrir el archivo de listado: {e}")
            raise

    def handle_save_dialog(self, filename):
        """
        Maneja el diálogo de guardar archivo nativo del sistema.
        
        Args:
            filename: Nombre completo del archivo con ruta (sin extensión .pdf)
        
        Returns:
            bool: True si el manejo parece exitoso, False en caso contrario
        """
        logger.info(f"Intentando guardar como: {filename}")
        
        # Si estamos en WSL, usar manejador específico
        if self.is_wsl:
            logger.info("Usando enfoque específico para WSL")
            return self.handle_save_dialog_wsl(filename)
        
        # Para sistemas no-WSL, usar enfoque simplificado con ubicación directa
        try:
            # Usar directamente la ruta completa donde debe guardarse el archivo
            final_path = filename
            logger.info(f"Ruta final para guardar: {final_path}")
            
            # Asegurarnos de que el directorio exista
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            
            # Presionar Enter para confirmar el cuadro de diálogo de impresión
            logger.info("Presionando Enter para confirmar impresión")
            webdriver.ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            
            # Esperar más tiempo a que aparezca el explorador de archivos
            logger.info("Esperando a que aparezca el explorador de archivos")
            time.sleep(3.0)
            
            # Presionar Enter nuevamente para aceptar el nombre de archivo predeterminado
            logger.info("Presionando Enter para aceptar el nombre de archivo predeterminado")
            webdriver.ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            
            # Manejar posible diálogo de confirmación de sobrescritura
            time.sleep(1.0)
            try:
                webdriver.ActionChains(self.driver).send_keys(Keys.TAB).perform()
                time.sleep(0.5)
                webdriver.ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                time.sleep(0.5)
            except:
                pass
            
            # Esperar más tiempo para que se guarde el archivo
            logger.info("Esperando a que se guarde el archivo")
            time.sleep(5.0)
            
            # Verificar si la ventana sigue abierta
            try:
                current_handles = self.driver.window_handles
                current_url = self.driver.current_url
                
                # Si aún estamos en la ventana de impresión, intentar un segundo Enter
                if "print" in current_url.lower():
                    logger.info("La ventana de impresión sigue abierta. Intentando segundo Enter...")
                    webdriver.ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    time.sleep(1.0)
                    # Intentar manejar diálogo de confirmación
                    webdriver.ActionChains(self.driver).send_keys(Keys.TAB).perform()
                    time.sleep(0.5)
                    webdriver.ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    time.sleep(1.0)
            except Exception as e:
                logger.info(f"Excepción al verificar estado de ventana: {e} (posiblemente ya cerrada)")
            
            # Verificar si el archivo se guardó en la ubicación final (con .pdf añadido si no lo tenía)
            final_check_path = final_path if final_path.lower().endswith('.pdf') else f"{final_path}.pdf"
            time.sleep(1.0)
            if os.path.exists(final_check_path):
                logger.info(f"Archivo guardado correctamente en: {final_check_path}")
                return True
            else:
                # Buscar en el directorio temporal y mover si es necesario
                files_in_temp = os.listdir(self.download_dir)
                pdf_files = [f for f in files_in_temp if f.endswith('.pdf')]
                
                if pdf_files:
                    # Tomar el archivo PDF más reciente
                    pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.download_dir, x)), reverse=True)
                    latest_pdf = pdf_files[0]
                    latest_pdf_path = os.path.join(self.download_dir, latest_pdf)
                    
                    logger.info(f"Moviendo PDF reciente a ubicación final: {final_check_path}")
                    
                    # Mover el archivo a la ubicación final
                    try:
                        shutil.move(latest_pdf_path, final_check_path)
                        logger.info(f"Archivo PDF movido a: {final_check_path}")
                        return True
                    except Exception as e:
                        logger.warning(f"Error al mover archivo PDF: {e}")
                else:
                    logger.warning(f"No se encontró ningún archivo PDF en el directorio temporal: {self.download_dir}")
            
            logger.info("Proceso de guardado completado")
            return True
            
        except Exception as e:
            logger.error(f"Error al manejar diálogo de guardado: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Intentar con Escape como último recurso
            try:
                logger.info("Intentando cerrar diálogo con Escape")
                webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
            except:
                pass
                
            return False

    def handle_save_dialog_wsl(self, filename):
        """Método específico para manejar diálogos de guardar en WSL"""
        try:
            # Ruta absoluta donde se guardará el PDF
            # Usar la ruta sin extensión, ya que el diálogo añadirá .pdf automáticamente
            full_save_path = os.path.join(self.output_folder, filename)
            
            logger.info(f"WSL: Guardando directamente en ruta final: {full_save_path}")
            
            # Esperar a que aparezca el diálogo de guardar (en Windows)
            logger.info("WSL: Intentando Alt+Tab para cambiar ventana")
            time.sleep(2.5)  # Esperar a que aparezca la ventana
            
            # Presionar Alt+Tab para asegurar que el foco esté en la ventana de diálogo
            try:
                os.system("xdotool key alt+Tab")
                time.sleep(0.5)
            except:
                logger.warning("Error al intentar Alt+Tab con xdotool")
                
            # Escribir la ruta del archivo completa
            logger.info(f"WSL: Escribiendo ruta del archivo: {full_save_path}")
            try:
                # Limpiar primero cualquier texto existente
                os.system('xdotool key ctrl+a')
                time.sleep(0.3)
                os.system('xdotool key Delete')
                time.sleep(0.3)
                
                # La ruta que escribimos no debe incluir .pdf pues se añade automáticamente
                os.system(f'xdotool type "{full_save_path}"')
                time.sleep(0.5)
                
                # Presionar Enter para confirmar
                os.system('xdotool key Return')
                time.sleep(0.5)
                
                # Manejar posible diálogo de confirmación de sobrescritura
                try:
                    os.system('xdotool key Tab')
                    time.sleep(0.3)
                    os.system('xdotool key Return')  # Confirmar sobrescritura
                except:
                    logger.warning("Error al confirmar sobrescritura con método estándar")
            except Exception as e:
                logger.error(f"Error al intentar escribir ruta: {e}")
            
            # Esperar a que se complete la operación de guardar
            logger.info("WSL: Esperando a que se guarde el archivo")
            time.sleep(5)
            
            # Verificar si el archivo se descargó en el directorio temporal
            try:
                pdf_files = [f for f in os.listdir(self.download_dir) if f.lower().endswith('.pdf')]
                if pdf_files:
                    logger.info(f"WSL: Archivo(s) PDF encontrado(s) en directorio temporal: {pdf_files}")
                    # Aquí puedes mover los archivos si es necesario
                else:
                    logger.warning(f"WSL: No se encontró ningún archivo PDF en el directorio temporal: {self.download_dir}")
            except Exception as e:
                logger.error(f"Error al verificar archivos descargados: {e}")
            
            logger.info("WSL: Proceso de guardado completado")
            
        except Exception as e:
            logger.error(f"Error en handle_save_dialog_wsl: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def esperar_nueva_ventana(self, driver, ventanas_antes, mensaje="Esperando nueva ventana", max_intentos=5):
        """
        Espera a que se abra una nueva ventana y cambia a ella.
        
        Args:
            driver: WebDriver de Selenium
            ventanas_antes: Lista de handles de ventanas antes de la acción
            mensaje: Mensaje para los logs
            max_intentos: Número máximo de intentos
            
        Returns:
            bool: True si se detectó y cambió a una nueva ventana, False en caso contrario
        """
        def _condition():
            ventanas_despues = driver.window_handles
            return len(ventanas_despues) > len(ventanas_antes)
        
        if self.esperar_con_intentos(_condition, mensaje=mensaje, max_intentos=max_intentos):
            ventanas_despues = driver.window_handles
            nueva_ventana = [v for v in ventanas_despues if v not in ventanas_antes][0]
            driver.switch_to.window(nueva_ventana)
            logger.info(f"Cambiado a nueva ventana: {driver.current_url}")
            return True
        return False
    
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

    def navegar_entre_anios(self, driver, anio_objetivo):
        """
        Navega entre los años hasta encontrar el año objetivo.
        """
        logger.info(f"Intentando navegar al año {anio_objetivo}")
        
        # Selectores comunes para botones de año
        selectores_anios = [
            ".ui-button.ui-corner-right span", 
            ".ui-button span"
        ]
        
        # Lista para almacenar los años disponibles (para logging)
        anios_disponibles = []
        
        # Intentar con todos los selectores disponibles
        for selector in selectores_anios:
            logger.info(f"Buscando botones de año con selector: {selector}")
            botones_anio = self.esperar_elementos(driver, selector)
            
            if not botones_anio:
                logger.warning(f"No se encontraron botones de año con selector: {selector}")
                continue
                
            # Guardar años disponibles para logging
            anios_disponibles = [boton.text.strip() for boton in botones_anio if boton.text.strip()]
            logger.info(f"Años disponibles: {anios_disponibles}")
            
            # Buscar el botón del año objetivo y hacer clic
            for boton in botones_anio:
                texto_boton = boton.text.strip()
                if texto_boton == str(anio_objetivo):
                    logger.info(f"Encontrado botón para el año {anio_objetivo}")
                    
                    # Verificar si el botón ya está seleccionado
                    padre = boton.find_element(By.XPATH, "./..")
                    if "ui-state-active" in padre.get_attribute("class"):
                        logger.info(f"El año {anio_objetivo} ya está seleccionado")
                        return True
                    
                    # Hacer clic con reintentos
                    if self.click_con_reintentos(driver, boton, f"botón año {anio_objetivo}"):
                        # Esperar a que la interfaz se actualice
                        def verificar_anio_seleccionado():
                            try:
                                nuevo_padre = boton.find_element(By.XPATH, "./..")
                                return "ui-state-active" in nuevo_padre.get_attribute("class")
                            except:
                                return False
                        
                        if self.esperar_con_intentos(
                            verificar_anio_seleccionado, 
                            f"Esperando que el año {anio_objetivo} quede seleccionado"
                        ):
                            logger.info(f"Navegación exitosa al año {anio_objetivo}")
                            return True
            
            # Si llegamos aquí, no encontramos el año objetivo
            # con el selector actual, probamos con el siguiente selector
        
        # Si no encontramos el año objetivo con los selectores, intentamos navegar con flechas
        if anios_disponibles:
            logger.info(f"Intentando navegar al año {anio_objetivo} usando flechas, años disponibles: {anios_disponibles}")
            return self.navegar_usando_flechas(driver, anio_objetivo, anios_disponibles)
        else:
            logger.error(f"No se encontraron años disponibles para navegar al año {anio_objetivo}")
            return False
            
    def navegar_usando_flechas(self, driver, anio_objetivo, anios_disponibles):
        """
        Navega entre años usando las flechas izquierda/derecha cuando el año objetivo
        no está visible inicialmente.
        """
        if not anios_disponibles:
            logger.error("No hay años disponibles para navegar usando flechas")
            return False
            
        anio_objetivo = str(anio_objetivo)
        
        # Determinar dirección de navegación
        anio_actual = anios_disponibles[0]  # Asumimos que el primer año es el seleccionado actualmente
        try:
            if int(anio_objetivo) < int(anio_actual):
                flecha_selector = ".ui-datepicker-prev"
                direccion = "izquierda"
            else:
                flecha_selector = ".ui-datepicker-next"
                direccion = "derecha"
        except ValueError:
            logger.error(f"Error al convertir años para comparación: objetivo={anio_objetivo}, actual={anio_actual}")
            return False
            
        logger.info(f"Navegando con flecha {direccion} desde {anio_actual} hacia {anio_objetivo}")
        
        # Máximo de clics en flechas para evitar bucles infinitos
        max_clics = 10
        for i in range(max_clics):
            # Buscar botón de flecha
            flecha = self.esperar_elemento(driver, flecha_selector, mensaje=f"flecha {direccion}")
            if not flecha:
                logger.warning(f"No se encontró la flecha {direccion} para navegar")
                return False
                
            # Hacer clic en la flecha
            if not self.click_con_reintentos(driver, flecha, f"flecha {direccion}"):
                logger.warning(f"No se pudo hacer clic en la flecha {direccion}")
                return False
                
            # Esperar a que cambie el año
            time.sleep(1)  # Pequeña pausa para permitir la actualización de la interfaz
            
            # Verificar años actuales
            for selector in [".ui-button.ui-corner-right span", ".ui-button span"]:
                botones_anio = self.esperar_elementos(driver, selector)
                if botones_anio:
                    nuevos_anios = [boton.text.strip() for boton in botones_anio if boton.text.strip()]
                    logger.info(f"Después de navegar con flecha {direccion}, años disponibles: {nuevos_anios}")
                    
                    # Verificar si el año objetivo ahora está visible
                    for boton in botones_anio:
                        if boton.text.strip() == anio_objetivo:
                            logger.info(f"Encontrado botón para el año {anio_objetivo} después de navegar con flechas")
                            if self.click_con_reintentos(driver, boton, f"botón año {anio_objetivo} (después de flechas)"):
                                logger.info(f"Navegación exitosa al año {anio_objetivo} usando flechas")
                                return True
                    
                    # Si encontramos botones pero no el año objetivo, continuamos navegando
                    break
            
            # Si llegamos al límite de navegación sin encontrar el año
            if i == max_clics - 1:
                logger.error(f"No se encontró el año {anio_objetivo} después de {max_clics} navegaciones con flechas")
                return False
                
        logger.error(f"No se pudo navegar al año {anio_objetivo} usando flechas")
        return False

    def seleccionar_trimestre(self, driver, trimestre_objetivo):
        """
        Selecciona el trimestre objetivo del dropdown.
        Utiliza esperas inteligentes.
        """
        logger.info(f"Intentando seleccionar el trimestre {trimestre_objetivo}")
        
        try:
            # Buscar todos los dropdowns en la página
            dropdowns = driver.find_elements(By.CSS_SELECTOR, ".selectToDropdown")
            
            # Si no hay dropdowns, reportar error
            if not dropdowns:
                logger.warning("No se encontraron dropdowns para seleccionar trimestre")
                return False
            
            # Asumir que el primer dropdown es para trimestres
            trimestre_dropdown = dropdowns[0]
            
            # Hacer clic para abrir el dropdown con reintentos
            if not self.click_con_reintentos(driver, trimestre_dropdown, "dropdown de trimestres"):
                logger.error("No se pudo abrir el dropdown de trimestres")
                return False
            
            # Esperar a que aparezcan las opciones del dropdown
            def opciones_visibles():
                try:
                    options = driver.find_elements(By.CSS_SELECTOR, ".selectToDropdownOptions div.selectToDropdownOption")
                    return len(options) > 0 and all(option.is_displayed() for option in options[:1])
                except:
                    return False
            
            if not self.esperar_con_intentos(opciones_visibles, "Esperando opciones del dropdown", max_intentos=5):
                logger.error("No se pudieron visualizar las opciones del dropdown")
                return False
            
            # Buscar todas las opciones del dropdown
            options = driver.find_elements(By.CSS_SELECTOR, ".selectToDropdownOptions div.selectToDropdownOption")
            logger.info(f"Se encontraron {len(options)} opciones en el dropdown")
            
            # Buscar la opción que coincida con el trimestre objetivo
            for option in options:
                try:
                    option_text = option.text.strip().lower()
                    logger.info(f"Opción encontrada: {option_text}")
                    
                    if str(trimestre_objetivo).lower() in option_text or f"trimestre {trimestre_objetivo}".lower() in option_text:
                        # Hacer clic en la opción con reintentos
                        if self.click_con_reintentos(driver, option, f"opción {option_text}"):
                            logger.info(f"Se seleccionó la opción: {option_text}")
                            
                            # Esperar a que se cierren las opciones del dropdown y se actualice la interfaz
                            def dropdown_cerrado():
                                try:
                                    options = driver.find_elements(By.CSS_SELECTOR, ".selectToDropdownOptions div.selectToDropdownOption")
                                    return len(options) == 0 or not any(option.is_displayed() for option in options[:1])
                                except:
                                    return True  # Si hay error al buscar las opciones, asumimos que ya no están
                            
                            if self.esperar_con_intentos(dropdown_cerrado, "Esperando cierre del dropdown", max_intentos=5):
                                # Esperar a que la interfaz se actualice con los datos del trimestre
                                def datos_cargados():
                                    try:
                                        # Verificar si hay elementos que indican que los datos están cargados
                                        tablas = driver.find_elements(By.CSS_SELECTOR, "table")
                                        textos = driver.find_elements(By.CSS_SELECTOR, ".div-container-grey")
                                        return len(tablas) > 0 or len(textos) > 0
                                    except:
                                        return False
                                
                                if self.esperar_con_intentos(datos_cargados, "Esperando carga de datos del trimestre", max_intentos=8):
                                    logger.info(f"Datos del trimestre {trimestre_objetivo} cargados correctamente")
                                    return True
                                else:
                                    logger.warning(f"No se pudo confirmar la carga de datos del trimestre {trimestre_objetivo}")
                                    # Continuamos de todas formas ya que a veces la detección de cambios puede fallar
                                    return True
                            else:
                                logger.warning("No se pudo confirmar el cierre del dropdown")
                                # Intentar hacer clic en otro lugar para cerrar el dropdown
                                try:
                                    driver.find_element(By.TAG_NAME, "body").click()
                                except:
                                    pass
                                return True
                        else:
                            logger.warning(f"No se pudo hacer clic en la opción {option_text}")
                except Exception as e:
                    logger.error(f"Error al procesar opción del dropdown: {e}")
            
            # Si llegamos aquí, no encontramos el trimestre objetivo
            logger.error(f"No se encontró el trimestre {trimestre_objetivo} entre las opciones")
            
            # Intentar cerrar el dropdown haciendo clic en otro lugar
            try:
                driver.find_element(By.TAG_NAME, "body").click()
            except:
                pass
                
            return False
                
        except Exception as e:
            logger.error(f"Error al seleccionar trimestre: {e}")
            return False

    def guardar_tabla_como_pdf(self, pdf_filename, titulo_tabla=None):
        """Guarda la tabla como PDF utilizando el diálogo nativo de impresión"""
        try:
            # Preparar el nombre del archivo asegurándonos que no tenga extensión duplicada
            if pdf_filename.lower().endswith('.pdf'):
                base_filename = pdf_filename[:-4]  # Quitar la extensión .pdf
                dialog_filename = base_filename  # Para pasar al diálogo de guardar
                final_filename = pdf_filename  # Para logs y verificaciones
            else:
                dialog_filename = pdf_filename
                final_filename = f"{pdf_filename}.pdf"
                
            logger.info(f"Utilizando diálogo nativo para guardar como: {final_filename}")
            logger.info(f"Intentando guardar como: {final_filename}")
            
            # Detectar si estamos en WSL para usar enfoque específico
            if self.is_wsl:
                logger.info("Usando enfoque específico para WSL")
                self.handle_save_dialog_wsl(dialog_filename)
            else:
                # Enfoque estándar para otros sistemas
                self.handle_save_dialog(dialog_filename)
            
            logger.info("Esperando cierre automático de la ventana de impresión")
            
            # Dar tiempo para que se complete la operación de guardar
            time.sleep(4)
            
            # Verificar el estado de las ventanas del navegador
            try:
                handles = self.driver.window_handles
                current_url = self.driver.current_url
                logger.info(f"Ventanas activas después de guardar: {len(handles)}, URL actual: {current_url}")
                
                # Si seguimos en la ventana de impresión (chrome://print), intentar cerrarla
                if current_url.startswith("chrome://print"):
                    logger.info("Detectada ventana de impresión abierta, intentando cerrarla")
                    self.driver.close()
                    time.sleep(1)
                
                # Cambiar a la ventana principal de AFIP si hay más de una ventana
                if len(handles) > 1:
                    for handle in handles:
                        self.driver.switch_to.window(handle)
                        current_url = self.driver.current_url
                        logger.info(f"Verificando ventana: {current_url}")
                        if "afip.gob.ar" in current_url:
                            logger.info(f"Cambiado a ventana principal de AFIP: {current_url}")
                            break
                
            except Exception as e:
                logger.warning(f"Excepción al verificar estado de ventana: {e} (posiblemente ya cerrada)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error al guardar PDF: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def close(self):
        """Cerrar el navegador y limpiar temporales."""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
                logger.info("Navegador cerrado correctamente")
            except Exception as e:
                logger.warning(f"Error al cerrar el navegador: {e}")
        
        # Limpiar directorio temporal de descargas
        self.cleanup_temp_dir()
        
    def cleanup_temp_dir(self):
        """Eliminar el directorio temporal de descargas."""
        try:
            if os.path.exists(self.download_dir):
                import shutil
                shutil.rmtree(self.download_dir)
                logger.info(f"Directorio temporal eliminado: {self.download_dir}")
        except Exception as e:
            logger.error(f"Error al eliminar directorio temporal: {e}")

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
        help="Archivo CSV con datos de contribuyentes",
        type=str,
        default="clientes.csv"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    try:
        args = parse_arguments()
        extractor = NuestraParteExtractor()
        extractor.ejecutar(año=args.year, csv_file=args.file)
    except Exception as e:
        logging.error(f"Error general en la aplicación: {e}")
        print(f"\nError inesperado: {e}")
        print("Se ha generado un archivo de log con los detalles.")
        input("\nPresione ENTER para salir...") 