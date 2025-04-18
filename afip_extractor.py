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
from pathlib import Path
from datetime import datetime

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
        self.output_folder = "Resultados"
        
    def setup_driver(self):
        """Configura y devuelve el driver de Chrome con opciones optimizadas"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
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
            time.sleep(5)  # Esperar carga de página
            
            # Capturar screenshot de la página de login
            login_screenshot = os.path.join(self.output_folder, f"login_page_{cuit}.png")
            driver.save_screenshot(login_screenshot)
            logger.info(f"Se guardó captura de la página de login en {login_screenshot}")
            
            # Verificar que la página ha cargado correctamente
            logger.info(f"Título de la página: '{driver.title}'")
            
            # PASO 1: Ingresar CUIT
            logger.info("Buscando campo de CUIT...")
            try:
                # Selector exacto basado en el HTML proporcionado
                username_field = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "F1:username"))
                )
                logger.info("Campo de CUIT encontrado")
                username_field.clear()
                username_field.send_keys(cuit)
                logger.info(f"CUIT ingresado: {cuit}")
                
                # Buscar el botón "Siguiente"
                siguiente_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.ID, "F1:btnSiguiente"))
                )
                logger.info("Botón 'Siguiente' encontrado, haciendo clic...")
                siguiente_button.click()
                
                # Esperar a que se cargue la pantalla de contraseña
                time.sleep(5)
                
                # Capturar screenshot después de ingresar CUIT
                cuit_screenshot = os.path.join(self.output_folder, f"after_cuit_{cuit}.png")
                driver.save_screenshot(cuit_screenshot)
                logger.info(f"Se guardó captura después de ingresar CUIT en {cuit_screenshot}")
                
                # PASO 2: Ingresar contraseña
                logger.info("Buscando campo de contraseña...")
                # La página se recarga, necesitamos esperar el campo de contraseña
                password_field = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "F1:password"))
                )
                logger.info("Campo de contraseña encontrado")
                password_field.clear()
                password_field.send_keys(clave_fiscal)
                logger.info("Contraseña ingresada")
                
                # Buscar el botón "Ingresar"
                ingresar_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.ID, "F1:btnIngresar"))
                )
                logger.info("Botón 'Ingresar' encontrado, haciendo clic...")
                ingresar_button.click()
                
                # Esperar redirección
                time.sleep(7)
                
                # Capturar screenshot después del login
                after_login_screenshot = os.path.join(self.output_folder, f"after_login_{cuit}.png")
                driver.save_screenshot(after_login_screenshot)
                logger.info(f"Se guardó captura después del login en {after_login_screenshot}")
                
                # Verificar que el login fue exitoso
                logger.info(f"URL después de login: {driver.current_url}")
                
                # Verificar si estamos en la página de servicios (ahora acepta la nueva URL de AFIP)
                if "menuPrincipal" in driver.current_url or "contribuyente" in driver.current_url or "portalcf.cloud.afip.gob.ar" in driver.current_url:
                    logger.info(f"Inicio de sesión exitoso para el usuario {cuit}")
                    
                    # En lugar de navegar directamente a la URL de "Nuestra Parte"
                    # vamos a usar el buscador principal
                    logger.info("Buscando 'Nuestra Parte' en el buscador principal")
                    
                    try:
                        # Esperar a que la página se cargue completamente
                        time.sleep(3)
                        
                        # Esperar a que el buscador esté disponible
                        buscador = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.ID, "buscadorInput"))
                        )
                        logger.info("Buscador encontrado")
                        
                        # Hacer clic en el buscador primero para activarlo
                        buscador.click()
                        time.sleep(1)
                        
                        # Limpiar el campo y escribir "Nuestra Parte"
                        buscador.clear()
                        buscador.send_keys("Nuestra Parte")
                        logger.info("Texto 'Nuestra Parte' ingresado en el buscador")
                        
                        # Esperar a que aparezcan los resultados en el dropdown
                        time.sleep(2)  # Dar tiempo para que aparezcan los resultados
                        
                        # Capturar screenshot de los resultados de búsqueda
                        busqueda_screenshot = os.path.join(self.output_folder, f"busqueda_nuestra_parte_{cuit}.png")
                        driver.save_screenshot(busqueda_screenshot)
                        logger.info(f"Se guardó captura de resultados de búsqueda en {busqueda_screenshot}")
                        
                        # Verificar que el dropdown de resultados está visible
                        dropdown = WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located((By.ID, "resultadoBusqueda"))
                        )
                        logger.info("Dropdown de resultados visible")
                        
                        # Seleccionar el primer resultado
                        primer_resultado = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "#resultadoBusqueda a:first-child"))
                        )
                        logger.info("Primer resultado de búsqueda encontrado, haciendo clic...")
                        
                        # Capturar las ventanas actuales antes de hacer clic
                        ventanas_antes = driver.window_handles
                        
                        # Hacer clic en el primer resultado
                        primer_resultado.click()
                        logger.info("Se hizo clic en el primer resultado")
                        
                        # Realizar múltiples intentos para detectar y cambiar a la nueva pestaña
                        nueva_ventana_encontrada = False
                        max_intentos = 5
                        
                        for intento in range(max_intentos):
                            logger.info(f"Intento {intento+1}/{max_intentos} para detectar nueva pestaña...")
                            # Esperar a que se abra una nueva pestaña
                            time.sleep(3)
                            ventanas_despues = driver.window_handles
                            
                            # Verificar si se abrió una nueva pestaña
                            if len(ventanas_despues) > len(ventanas_antes):
                                # Cambiar a la nueva pestaña
                                nueva_ventana = [v for v in ventanas_despues if v not in ventanas_antes][0]
                                driver.switch_to.window(nueva_ventana)
                                logger.info(f"Se cambió a la nueva pestaña: {driver.current_url}")
                                
                                # Capturar screenshot en la nueva pestaña
                                nueva_ventana_screenshot = os.path.join(self.output_folder, f"nueva_ventana_{cuit}.png")
                                driver.save_screenshot(nueva_ventana_screenshot)
                                logger.info(f"Se guardó captura de la nueva pestaña en {nueva_ventana_screenshot}")
                                
                                nueva_ventana_encontrada = True
                                break
                            else:
                                logger.info(f"No se detectó nueva pestaña en el intento {intento+1}, esperando...")
                        
                        # Si no se abrió una nueva pestaña después de los intentos
                        if not nueva_ventana_encontrada:
                            logger.warning("No se abrió una nueva pestaña después de múltiples intentos")
                            # Capturar screenshot de la página actual
                            misma_pagina_screenshot = os.path.join(self.output_folder, f"misma_pagina_{cuit}.png")
                            driver.save_screenshot(misma_pagina_screenshot)
                            logger.info(f"Se guardó captura en {misma_pagina_screenshot}")
                        
                        # Esperar a que cargue la página
                        time.sleep(5)
                        
                        # Verificar si estamos en la página correcta de Nuestra Parte
                        # Verificamos por fragmentos de URL que podrían indicar que estamos en la página correcta
                        url_actual = driver.current_url
                        urls_validas = ["serviciosjava2.afip.gob.ar/cgpf", "nuestra-parte", "nuestraparte"]
                        
                        if any(fragmento in url_actual.lower() for fragmento in urls_validas):
                            logger.info(f"Navegación exitosa a través del buscador. URL actual: {url_actual}")
                            return True
                        else:
                            logger.error(f"No se pudo navegar a la página de Nuestra Parte. URL actual: {url_actual}")
                            error_navegacion_screenshot = os.path.join(self.output_folder, f"error_navegacion_{cuit}.png")
                            driver.save_screenshot(error_navegacion_screenshot)
                            logger.info(f"Se guardó captura del error de navegación en {error_navegacion_screenshot}")
                            
                            # Intentar alternativa: navegación directa a URL conocida
                            logger.info("Intentando navegación alternativa directa a URL de Nuestra Parte...")
                            try:
                                driver.get("https://serviciosjava2.afip.gob.ar/cgpf/jsp/mostrarMenu.do")
                                time.sleep(5)
                                
                                url_despues_redireccion = driver.current_url
                                logger.info(f"URL después de navegación directa: {url_despues_redireccion}")
                                
                                # Capturar screenshot después de navegación directa
                                nav_directa_screenshot = os.path.join(self.output_folder, f"navegacion_directa_{cuit}.png")
                                driver.save_screenshot(nav_directa_screenshot)
                                logger.info(f"Se guardó captura después de navegación directa en {nav_directa_screenshot}")
                                
                                # Verificar si la URL contiene alguno de los fragmentos válidos
                                if any(fragmento in url_despues_redireccion.lower() for fragmento in urls_validas):
                                    logger.info("Navegación directa exitosa a Nuestra Parte")
                                    return True
                                else:
                                    logger.error("La navegación directa también falló")
                                    return False
                            except Exception as e:
                                logger.error(f"Error durante la navegación directa: {e}")
                                return False
                    except Exception as e:
                        logger.error(f"Error al buscar 'Nuestra Parte': {e}")
                        
                        # Intentar capturar un screenshot del estado actual
                        error_busqueda_screenshot = os.path.join(self.output_folder, f"error_busqueda_{cuit}.png")
                        driver.save_screenshot(error_busqueda_screenshot)
                        logger.info(f"Se guardó captura del error de búsqueda en {error_busqueda_screenshot}")
                        
                        return False
                
            except TimeoutException as e:
                logger.error(f"Timeout esperando elementos de login: {e}")
                # Capturar screenshot del error
                error_screenshot = os.path.join(self.output_folder, f"error_timeout_{cuit}.png")
                driver.save_screenshot(error_screenshot)
                logger.info(f"Se guardó captura de pantalla del error en {error_screenshot}")
                return False
            except Exception as e:
                logger.error(f"Error durante el proceso de login: {e}")
                # Capturar screenshot del error
                error_screenshot = os.path.join(self.output_folder, f"error_exception_{cuit}.png")
                driver.save_screenshot(error_screenshot)
                logger.info(f"Se guardó captura de pantalla del error en {error_screenshot}")
                return False
                
        except Exception as e:
            logger.error(f"Error general al iniciar sesión: {e}")
            # Capturar screenshot del error
            try:
                error_screenshot = os.path.join(self.output_folder, f"error_general_{cuit}.png")
                driver.save_screenshot(error_screenshot)
                logger.info(f"Se guardó captura de pantalla del error en {error_screenshot}")
            except:
                pass
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
                driver.save_screenshot(os.path.join(contribuyente_dir, "pagina_desconocida.png"))
            
            # Capturar pantalla de la página de nuestra parte
            driver.save_screenshot(os.path.join(contribuyente_dir, "nuestra_parte.png"))
            
            # Buscar los botones de año directamente sin buscar primero la pestaña
            # Ya que la pestaña podría estar ya seleccionada por defecto
            año_encontrado = False
            
            # Capturar el estado actual para referencia
            driver.save_screenshot(os.path.join(contribuyente_dir, "antes_seleccion_año.png"))
            
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
                            driver.save_screenshot(os.path.join(contribuyente_dir, f"antes_clic_año_{año}.png"))
                            
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
                driver.save_screenshot(os.path.join(contribuyente_dir, "error_busqueda_botones.png"))
            
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
            
            # Si aún no hemos encontrado el año, capturar toda la página y continuar
            if not año_encontrado:
                logger.warning(f"No se pudo encontrar/seleccionar el año {año}, continuando con lo que esté disponible")
                driver.save_screenshot(os.path.join(contribuyente_dir, "pagina_sin_año_seleccionado.png"))
                
                # Guardar HTML completo para análisis posterior
                with open(os.path.join(contribuyente_dir, "pagina_completa.html"), "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            
            # Crear directorio para este año
            año_dir = os.path.join(contribuyente_dir, f"año_{año}")
            os.makedirs(año_dir, exist_ok=True)
            
            # Capturar pantalla con la información disponible
            driver.save_screenshot(os.path.join(año_dir, f"info_disponible_{año}.png"))
            
            # Procesar secciones de datos (intentar extraer lo que se pueda)
            self.procesar_secciones_datos(driver, año_dir)
            
            return True
            
        except Exception as e:
            logger.error(f"Error al procesar 'Nuestra Parte': {e}")
            # Capturar pantalla en caso de error
            try:
                error_dir = os.path.join(output_dir, cuit)
                os.makedirs(error_dir, exist_ok=True)
                driver.save_screenshot(os.path.join(error_dir, "error_nuestra_parte.png"))
            except:
                pass
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
            # Esperar a que la página cargue completamente
            time.sleep(5)
            
            # Primero, procesar las secciones principales (div-container-grey con span dentro)
            self.procesar_secciones_principales(driver, output_dir)
            
            # Luego, procesar los spans de títulos individuales que aparecen fuera de secciones principales
            self.procesar_spans_individuales(driver, output_dir)
            
            logger.info("Procesamiento de secciones completado")
            
        except Exception as e:
            logger.error(f"Error general al procesar secciones: {e}")
    
    def procesar_secciones_principales(self, driver, output_dir):
        """
        Procesa las secciones principales que están dentro de div-container-grey
        """
        try:
            # Encontrar todas las secciones (div-container-grey)
            secciones_containers = driver.find_elements(By.CSS_SELECTOR, "div.div-container-grey")
            
            if not secciones_containers:
                logger.warning("No se encontraron secciones principales en la página")
                driver.save_screenshot(os.path.join(output_dir, "no_secciones_principales.png"))
                return
                
            logger.info(f"Se encontraron {len(secciones_containers)} secciones principales")
            
            # Para cada sección principal
            for idx, seccion_container in enumerate(secciones_containers, 1):
                try:
                    # Obtener el título de la sección
                    span_titulo = seccion_container.find_element(By.CSS_SELECTOR, "span")
                    titulo_seccion = span_titulo.text.strip()
                    logger.info(f"Procesando sección principal: {titulo_seccion}")
                    
                    # Crear carpeta para esta sección
                    seccion_dir = os.path.join(output_dir, f"{idx}_{self.normalizar_nombre(titulo_seccion)}")
                    os.makedirs(seccion_dir, exist_ok=True)
                    
                    # Capturar screenshot de la sección
                    driver.save_screenshot(os.path.join(seccion_dir, "seccion.png"))
                    
                    # También guardar el HTML de la sección completa
                    seccion_html = seccion_container.get_attribute("outerHTML")
                    with open(os.path.join(seccion_dir, "seccion.html"), 'w', encoding='utf-8') as f:
                        f.write(seccion_html)
                    
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
                                
                                # Crear carpeta para este elemento
                                elemento_dir = os.path.join(seccion_dir, f"{icon_idx}_{self.normalizar_nombre(nombre_elemento)}")
                                os.makedirs(elemento_dir, exist_ok=True)
                                
                                # Hacer clic en el ícono
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", icon)
                                time.sleep(1)
                                
                                # Capturar antes de hacer clic
                                driver.save_screenshot(os.path.join(elemento_dir, "antes_clic.png"))
                                
                                # Hacer clic
                                driver.execute_script("arguments[0].click();", icon)
                                logger.info(f"Se hizo clic en el ícono de {nombre_elemento}")
                                
                                # Esperar a que se carguen los datos
                                time.sleep(5)
                                
                                # Capturar después de hacer clic
                                driver.save_screenshot(os.path.join(elemento_dir, "despues_clic.png"))
                                
                                # Buscar íconos de impresión para guardar PDFs
                                try:
                                    # Buscar todos los íconos de impresión que estén visibles
                                    print_icons = driver.find_elements(By.CSS_SELECTOR, "a.btn-imprimir")
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
                                            
                                            # En lugar de hacer clic en el botón de impresión (que abre un diálogo),
                                            # vamos a guardar directamente el contenido HTML de la tabla correspondiente
                                            
                                            # Determinar qué elemento capturar basado en el atributo data-class del ícono de impresión
                                            data_class = print_icon.get_attribute("data-class")
                                            
                                            # Encontrar la tabla correspondiente
                                            tabla_selector = None
                                            if data_class:
                                                try:
                                                    # Buscar el elemento con la clase especificada
                                                    contenedor = driver.find_element(By.CSS_SELECTOR, f".{data_class}")
                                                    
                                                    # Buscar tablas dentro del contenedor
                                                    tablas = contenedor.find_elements(By.CSS_SELECTOR, "table")
                                                    
                                                    if tablas:
                                                        for tabla in tablas:
                                                            # Guardar el HTML de cada tabla
                                                            tabla_html = tabla.get_attribute("outerHTML")
                                                            tabla_id = tabla.get_attribute("id") or f"tabla_{print_idx}"
                                                            
                                                            # Crear un archivo HTML con el contenido de la tabla
                                                            html_filename = os.path.join(elemento_dir, f"{print_idx}_{self.normalizar_nombre(tabla_id)}.html")
                                                            
                                                            # Crear un HTML básico con la tabla
                                                            html_content = f"""
                                                            <!DOCTYPE html>
                                                            <html>
                                                            <head>
                                                                <meta charset="UTF-8">
                                                                <title>{titulo_tabla}</title>
                                                                <style>
                                                                    table {{ border-collapse: collapse; width: 100%; }}
                                                                    th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
                                                                    th {{ background-color: #f2f2f2; }}
                                                                </style>
                                                            </head>
                                                            <body>
                                                                <h1>{titulo_tabla}</h1>
                                                                {tabla_html}
                                                            </body>
                                                            </html>
                                                            """
                                                            
                                                            with open(html_filename, 'w', encoding='utf-8') as f:
                                                                f.write(html_content)
                                                            
                                                            logger.info(f"Se guardó el HTML de la tabla {tabla_id} en {html_filename}")
                                                    else:
                                                        # Intentar capturar todo el contenedor si no hay tablas específicas
                                                        contenedor_html = contenedor.get_attribute("outerHTML")
                                                        html_filename = os.path.join(elemento_dir, f"{print_idx}_{self.normalizar_nombre(titulo_tabla)}.html")
                                                        
                                                        # Crear un HTML básico con el contenido
                                                        html_content = f"""
                                                        <!DOCTYPE html>
                                                        <html>
                                                        <head>
                                                            <meta charset="UTF-8">
                                                            <title>{titulo_tabla}</title>
                                                        </head>
                                                        <body>
                                                            <h1>{titulo_tabla}</h1>
                                                            {contenedor_html}
                                                        </body>
                                                        </html>
                                                        """
                                                        
                                                        with open(html_filename, 'w', encoding='utf-8') as f:
                                                            f.write(html_content)
                                                        
                                                        logger.info(f"Se guardó el HTML del contenedor en {html_filename}")
                                                except Exception as e:
                                                    logger.error(f"Error al encontrar el contenedor '{data_class}': {e}")
                                            
                                            # Además de guardar el HTML, también intentamos capturar una imagen
                                            img_filename = os.path.join(elemento_dir, f"{print_idx}_{self.normalizar_nombre(titulo_tabla)}.png")
                                            
                                            # Si encontramos un contenedor específico, hacemos scroll hacia él y lo capturamos
                                            if data_class:
                                                try:
                                                    contenedor = driver.find_element(By.CSS_SELECTOR, f".{data_class}")
                                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", contenedor)
                                                    time.sleep(0.5)
                                                    
                                                    # Intentar capturar solo ese elemento como imagen
                                                    driver.save_screenshot(img_filename)
                                                    logger.info(f"Se guardó captura de pantalla de {titulo_tabla} en {img_filename}")
                                                except Exception as e:
                                                    logger.error(f"Error al capturar imagen del contenedor '{data_class}': {e}")
                                            
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
                                        
                                        for tabla_idx, tabla in enumerate(tablas_visibles, 1):
                                            try:
                                                # Identificar la tabla por su ID o crear un nombre
                                                tabla_id = tabla.get_attribute("id") or f"tabla_adicional_{tabla_idx}"
                                                
                                                # Crear un archivo HTML con el contenido de la tabla
                                                html_filename = os.path.join(elemento_dir, f"adicional_{tabla_idx}_{self.normalizar_nombre(tabla_id)}.html")
                                                
                                                # Obtener el HTML de la tabla
                                                tabla_html = tabla.get_attribute("outerHTML")
                                                
                                                # Crear un HTML básico con la tabla
                                                html_content = f"""
                                                <!DOCTYPE html>
                                                <html>
                                                <head>
                                                    <meta charset="UTF-8">
                                                    <title>{tabla_id}</title>
                                                    <style>
                                                        table {{ border-collapse: collapse; width: 100%; }}
                                                        th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
                                                        th {{ background-color: #f2f2f2; }}
                                                    </style>
                                                </head>
                                                <body>
                                                    <h1>{tabla_id}</h1>
                                                    {tabla_html}
                                                </body>
                                                </html>
                                                """
                                                
                                                with open(html_filename, 'w', encoding='utf-8') as f:
                                                    f.write(html_content)
                                                
                                                logger.info(f"Se guardó el HTML de la tabla adicional {tabla_id} en {html_filename}")
                                                
                                                # Hacer scroll a la tabla y capturarla como imagen
                                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tabla)
                                                time.sleep(0.5)
                                                
                                                img_filename = os.path.join(elemento_dir, f"adicional_{tabla_idx}_{self.normalizar_nombre(tabla_id)}.png")
                                                driver.save_screenshot(img_filename)
                                                logger.info(f"Se guardó captura de la tabla adicional {tabla_id} en {img_filename}")
                                                
                                            except Exception as e:
                                                logger.error(f"Error al procesar tabla adicional {tabla_idx} en {nombre_elemento}: {e}")
                                                continue
                                except Exception as e:
                                    logger.error(f"Error al buscar tablas adicionales en {nombre_elemento}: {e}")
                                
                                # Buscar el botón de cerrar para volver a la vista principal
                                try:
                                    cerrar_btn = driver.find_element(By.CSS_SELECTOR, f"a.btn-cerrar[data-trigger='{icon.get_attribute('data-trigger')}']")
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cerrar_btn)
                                    time.sleep(1)
                                    driver.execute_script("arguments[0].click();", cerrar_btn)
                                    logger.info(f"Se cerró la vista de {nombre_elemento}")
                                    time.sleep(2)
                                except Exception as e:
                                    logger.error(f"Error al cerrar la vista de {nombre_elemento}: {e}")
                                    # Intentar presionar ESC para cerrar si el botón no funciona
                                    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                                    time.sleep(1)
                                
                            except Exception as e:
                                logger.error(f"Error al procesar ícono {icon_idx} en la sección {titulo_seccion}: {e}")
                                continue
                                
                    except Exception as e:
                        logger.error(f"Error al buscar íconos en la sección {titulo_seccion}: {e}")
                        
                except Exception as e:
                    logger.error(f"Error al procesar sección {idx}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error al procesar secciones principales: {e}")
    
    def procesar_spans_individuales(self, driver, output_dir):
        """
        Busca y procesa spans individuales que son títulos de secciones
        fuera de los div-container-grey principales
        """
        try:
            # Buscar todos los divs que contienen elementos con clase 'panel-body'
            panels = driver.find_elements(By.CSS_SELECTOR, "div.panel-body")
            
            if not panels:
                logger.warning("No se encontraron paneles individuales")
                return
                
            logger.info(f"Se encontraron {len(panels)} paneles individuales")
            
            # Para cada panel, buscar elementos h3 y crear carpetas para cada uno
            for idx, panel in enumerate(panels, 1):
                try:
                    # Buscar el h3 dentro del panel
                    h3 = panel.find_element(By.CSS_SELECTOR, "h3")
                    titulo = h3.text.strip()
                    
                    if not titulo:
                        continue
                        
                    logger.info(f"Procesando panel individual: {titulo}")
                    
                    # Crear carpeta para este panel
                    panel_dir = os.path.join(output_dir, f"Panel_{idx}_{self.normalizar_nombre(titulo)}")
                    os.makedirs(panel_dir, exist_ok=True)
                    
                    # Capturar screenshot del panel
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", panel)
                    time.sleep(0.5)
                    driver.save_screenshot(os.path.join(panel_dir, "panel.png"))
                    
                    # Guardar el HTML del panel
                    panel_html = panel.get_attribute("outerHTML")
                    with open(os.path.join(panel_dir, "panel.html"), 'w', encoding='utf-8') as f:
                        f.write(panel_html)
                    
                    # Buscar tablas cercanas a este panel
                    try:
                        # Buscar el elemento padre del panel y luego buscar tablas dentro
                        parent_div = panel.find_element(By.XPATH, "..")
                        tablas = parent_div.find_elements(By.CSS_SELECTOR, "table")
                        
                        if tablas:
                            logger.info(f"Se encontraron {len(tablas)} tablas en el panel {titulo}")
                            
                            for tabla_idx, tabla in enumerate(tablas, 1):
                                try:
                                    # Identificar la tabla por su ID o crear un nombre
                                    tabla_id = tabla.get_attribute("id") or f"tabla_panel_{tabla_idx}"
                                    
                                    # Crear un archivo HTML con el contenido de la tabla
                                    html_filename = os.path.join(panel_dir, f"{tabla_idx}_{self.normalizar_nombre(tabla_id)}.html")
                                    
                                    # Obtener el HTML de la tabla
                                    tabla_html = tabla.get_attribute("outerHTML")
                                    
                                    # Crear un HTML básico con la tabla
                                    html_content = f"""
                                    <!DOCTYPE html>
                                    <html>
                                    <head>
                                        <meta charset="UTF-8">
                                        <title>{titulo} - {tabla_id}</title>
                                        <style>
                                            table {{ border-collapse: collapse; width: 100%; }}
                                            th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
                                            th {{ background-color: #f2f2f2; }}
                                        </style>
                                    </head>
                                    <body>
                                        <h1>{titulo}</h1>
                                        {tabla_html}
                                    </body>
                                    </html>
                                    """
                                    
                                    with open(html_filename, 'w', encoding='utf-8') as f:
                                        f.write(html_content)
                                    
                                    logger.info(f"Se guardó el HTML de la tabla {tabla_id} en {html_filename}")
                                    
                                    # Hacer scroll a la tabla y capturarla como imagen
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tabla)
                                    time.sleep(0.5)
                                    
                                    img_filename = os.path.join(panel_dir, f"{tabla_idx}_{self.normalizar_nombre(tabla_id)}.png")
                                    driver.save_screenshot(img_filename)
                                    logger.info(f"Se guardó captura de la tabla {tabla_id} en {img_filename}")
                                    
                                except Exception as e:
                                    logger.error(f"Error al procesar tabla {tabla_idx} en el panel {titulo}: {e}")
                                    continue
                        
                    except Exception as e:
                        logger.error(f"Error al buscar tablas en el panel {titulo}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error al procesar panel {idx}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error al procesar spans individuales: {e}")
    
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
            if driver:
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