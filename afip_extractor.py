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
                        
                        # Esperar a que se abra una nueva pestaña (si es que se abre)
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
                        else:
                            logger.info("No se abrió una nueva pestaña, continuando en la misma")
                            # Capturar screenshot de la página actual
                            misma_pagina_screenshot = os.path.join(self.output_folder, f"misma_pagina_{cuit}.png")
                            driver.save_screenshot(misma_pagina_screenshot)
                            logger.info(f"Se guardó captura en {misma_pagina_screenshot}")
                        
                        # Esperar a que cargue la página
                        time.sleep(5)
                        
                        # Solo reportar que la navegación fue exitosa
                        logger.info(f"Navegación exitosa a través del buscador. URL actual: {driver.current_url}")
                        return True
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
    
    def procesar_nuestra_parte(self, driver, año, path_contribuyente):
        """
        Procesa la sección de Nuestra Parte
        """
        try:
            logger.info("Procesando sección de Nuestra Parte")
            
            # Crear carpeta para Nuestra Parte con timestamp para evitar sobreescrituras
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nuestra_parte_dir = os.path.join(path_contribuyente, f"Nuestra_Parte_{año}_{timestamp}")
            os.makedirs(nuestra_parte_dir, exist_ok=True)
            
            # Capturar screenshot de la página inicial de Nuestra Parte
            menu_screenshot = os.path.join(nuestra_parte_dir, "menu_principal.png")
            driver.save_screenshot(menu_screenshot)
            logger.info(f"Se guardó captura de la página de Nuestra Parte en {menu_screenshot}")
            
            # Buscar y hacer clic en el año especificado
            logger.info(f"Buscando el año {año} en la sección 'Información nacional anual'")
            
            try:
                # Verificar que estamos en la pestaña "Información nacional anual"
                tab_nacional = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabNacional']"))
                )
                
                # Si la pestaña no tiene la clase 'active', hacemos clic
                if "active" not in tab_nacional.get_attribute("class"):
                    logger.info("Haciendo clic en la pestaña 'Información nacional anual'")
                    tab_nacional.click()
                    time.sleep(2)
                    
                # Buscar el botón del año usando el selector directo
                selector = f"span.btn-consultar[data-periodo='{año}']"
                
                # Buscar todos los botones de años visibles
                visible_years_elements = [e for e in driver.find_elements(By.CSS_SELECTOR, "span.btn-consultar.c-2x") if e.is_displayed()]
                visible_years = [elem.text.strip() for elem in visible_years_elements]
                logger.info(f"Años visibles actualmente: {visible_years}")
                
                # El año está visible directamente?
                year_found = False
                
                if año in visible_years:
                    year_found = True
                    # Encontrar el botón para hacer clic
                    for btn in visible_years_elements:
                        if btn.text.strip() == año:
                            year_button = btn
                            break
                else:
                    # Navegar usando las flechas para encontrar el año
                    if visible_years and int(año) < int(min(visible_years)):
                        # Navegar a la izquierda para años anteriores
                        left_arrow = driver.find_element(By.CSS_SELECTOR, "a.left-button")
                        
                        # Seguir haciendo clic hasta encontrar el año o alcanzar el límite
                        for _ in range(10):
                            if "flecha-disabled" in left_arrow.get_attribute("class"):
                                break
                                
                            left_arrow.click()
                            time.sleep(1)
                            
                            # Verificar si el año ya es visible
                            visible_years_elements = [e for e in driver.find_elements(By.CSS_SELECTOR, "span.btn-consultar.c-2x") if e.is_displayed()]
                            visible_years = [elem.text.strip() for elem in visible_years_elements]
                            
                            if año in visible_years:
                                for btn in visible_years_elements:
                                    if btn.text.strip() == año:
                                        year_button = btn
                                        year_found = True
                                        break
                                if year_found:
                                    break
                    
                    elif visible_years and int(año) > int(max(visible_years)):
                        # Navegar a la derecha para años más recientes
                        right_arrow = driver.find_element(By.CSS_SELECTOR, "a.right-button")
                        
                        # Seguir haciendo clic hasta encontrar el año o alcanzar el límite
                        for _ in range(10):
                            if "flecha-disabled" in right_arrow.get_attribute("class"):
                                break
                                
                            right_arrow.click()
                            time.sleep(1)
                            
                            # Verificar si el año ya es visible
                            visible_years_elements = [e for e in driver.find_elements(By.CSS_SELECTOR, "span.btn-consultar.c-2x") if e.is_displayed()]
                            visible_years = [elem.text.strip() for elem in visible_years_elements]
                            
                            if año in visible_years:
                                for btn in visible_years_elements:
                                    if btn.text.strip() == año:
                                        year_button = btn
                                        year_found = True
                                        break
                                if year_found:
                                    break
                
                # Si encontramos el año, hacer clic
                if year_found:
                    logger.info(f"Año {año} encontrado, haciendo clic...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", year_button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", year_button)
                    logger.info(f"Se hizo clic en el año {año}")
                else:
                    # Si no encontramos el año, intentar usar el más reciente disponible
                    logger.warning(f"No se pudo encontrar el año {año}, intentando usar el más reciente disponible")
                    visible_years_elements = [e for e in driver.find_elements(By.CSS_SELECTOR, "span.btn-consultar.c-2x") if e.is_displayed()]
                    visible_years = [elem.text.strip() for elem in visible_years_elements]
                    
                    if visible_years:
                        most_recent_year = max(visible_years)
                        for btn in visible_years_elements:
                            if btn.text.strip() == most_recent_year:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", btn)
                                logger.info(f"Se hizo clic en el año alternativo {most_recent_year}")
                    else:
                        logger.error("No se encontraron años visibles para hacer clic")
                        return False
                
                # Esperar a que se procese el formulario después de hacer clic
                time.sleep(5)
                
                # Capturar screenshot después de hacer clic
                after_click_screenshot = os.path.join(nuestra_parte_dir, f"después_clic_año.png")
                driver.save_screenshot(after_click_screenshot)
                logger.info(f"Se guardó captura después de hacer clic en {after_click_screenshot}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error al buscar/hacer clic en el año {año}: {e}")
                error_screenshot = os.path.join(nuestra_parte_dir, f"error_año_{año}.png")
                driver.save_screenshot(error_screenshot)
                logger.info(f"Se guardó captura del error en {error_screenshot}")
                return False
                
        except Exception as e:
            logger.error(f"Error general en procesar_nuestra_parte: {e}")
            return False
    
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
            resultado = self.procesar_nuestra_parte(driver, año, path_contribuyente)
            
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