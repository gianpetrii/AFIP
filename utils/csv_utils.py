#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades para manejar archivos CSV en el Extractor AFIP.
Este módulo contiene clases y funciones para leer, escribir y manipular
archivos CSV utilizados por el extractor AFIP.
"""

import os
import csv
import logging
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

class CSVHandler:
    """
    Clase para manejar operaciones de archivos CSV en el extractor AFIP.
    
    Esta clase proporciona métodos estáticos para trabajar con archivos CSV
    de contribuyentes, incluyendo lectura, conversión desde formato antiguo (TXT)
    y creación de archivos de ejemplo.
    """
    
    # Columnas que deben estar presentes en el archivo CSV
    COLUMNAS_REQUERIDAS = ['cuit', 'clave_fiscal', 'nombre']
    
    @staticmethod
    def leer_contribuyentes(ruta_archivo):
        """
        Lee un archivo CSV de contribuyentes y devuelve una lista de diccionarios
        con sus datos.
        
        Formato esperado del CSV:
        nombre,cuit,clave_fiscal
        "Contribuyente Ejemplo","20123456789","contraseña1"
        "Empresa Ejemplo","30987654321","contraseña2"
        
        Args:
            ruta_archivo (str): Ruta al archivo CSV
            
        Returns:
            list: Lista de diccionarios con los datos de los contribuyentes
        """
        contribuyentes = []
        
        if not os.path.exists(ruta_archivo):
            logger.error(f"No se encontró el archivo de contribuyentes: {ruta_archivo}")
            return contribuyentes
            
        # Lista de codificaciones para intentar, en orden de preferencia
        codificaciones = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
        
        for encoding in codificaciones:
            try:
                logger.info(f"Intentando leer el archivo con codificación: {encoding}")
                contribuyentes = []  # Reiniciar lista en cada intento
                
                with open(ruta_archivo, 'r', encoding=encoding) as archivo:
                    lector_csv = csv.DictReader(archivo)
                    
                    # Obtener las columnas del archivo CSV
                    columnas_csv = lector_csv.fieldnames
                    
                    # Verificar si alguna columna tiene el BOM (para utf-8)
                    columnas_limpias = []
                    map_columnas = {}
                    
                    for col in columnas_csv:
                        # Limpiar BOM si existe
                        col_limpia = col.replace('\ufeff', '')
                        if col != col_limpia:
                            map_columnas[col] = col_limpia
                        columnas_limpias.append(col_limpia)
                    
                    # Verificar si el archivo usa "clave" en lugar de "clave_fiscal"
                    if 'clave' in columnas_limpias and 'clave_fiscal' not in columnas_limpias:
                        map_columnas['clave'] = 'clave_fiscal'
                        logger.info("Adaptando columna 'clave' a 'clave_fiscal'")
                    
                    # Verificar que existan todas las columnas requeridas (o sus equivalentes)
                    columnas_requeridas_presentes = all(
                        col in columnas_limpias or 
                        (col == 'clave_fiscal' and 'clave' in columnas_limpias)
                        for col in CSVHandler.COLUMNAS_REQUERIDAS
                    )
                    
                    if not columnas_requeridas_presentes:
                        logger.warning(f"El archivo no contiene todas las columnas requeridas. Columnas encontradas: {columnas_limpias}")
                        columnas_faltantes = [col for col in CSVHandler.COLUMNAS_REQUERIDAS 
                                             if col not in columnas_limpias and 
                                                not (col == 'clave_fiscal' and 'clave' in columnas_limpias)]
                        logger.warning(f"Columnas faltantes: {columnas_faltantes}")
                        continue  # Probar con otra codificación
                    
                    for fila in lector_csv:
                        # Limpiar nombres de columnas con BOM y adaptar según mapeo
                        fila_limpia = {}
                        for col_original, valor in fila.items():
                            # Determinar nombre de columna final
                            col_final = col_original
                            if col_original in map_columnas:
                                col_final = map_columnas[col_original]
                            elif col_original.replace('\ufeff', '') in map_columnas:
                                col_final = map_columnas[col_original.replace('\ufeff', '')]
                                
                            # Guardar con nombre correcto
                            fila_limpia[col_final] = valor
                        
                        # Verificar que estén los campos requeridos
                        if not all(col in fila_limpia for col in CSVHandler.COLUMNAS_REQUERIDAS):
                            logger.warning(f"Fila sin todas las columnas requeridas: {fila_limpia}")
                            continue
                        
                        # Verificar que los campos requeridos no estén vacíos
                        if not fila_limpia['cuit'] or not fila_limpia['clave_fiscal'] or not fila_limpia['nombre']:
                            logger.warning(f"Fila con datos incompletos ignorada: {fila_limpia}")
                            continue
                            
                        # Limpiar espacios en blanco
                        contribuyente = {
                            'cuit': fila_limpia['cuit'].strip(),
                            'clave_fiscal': fila_limpia['clave_fiscal'].strip(),
                            'nombre': fila_limpia['nombre'].strip()
                        }
                        
                        # Agregar campos adicionales si existen
                        for campo in fila_limpia:
                            if campo not in CSVHandler.COLUMNAS_REQUERIDAS and campo in fila_limpia:
                                contribuyente[campo] = fila_limpia[campo].strip()
                        
                        contribuyentes.append(contribuyente)
                
                # Si llegamos aquí sin excepción y con contribuyentes, terminamos
                if contribuyentes:
                    logger.info(f"Se cargaron {len(contribuyentes)} contribuyentes usando codificación {encoding}")
                    return contribuyentes
                else:
                    logger.warning(f"No se encontraron contribuyentes válidos con codificación {encoding}")
                    
            except UnicodeDecodeError:
                logger.warning(f"Error de decodificación con {encoding}, probando otra codificación")
            except Exception as e:
                logger.error(f"Error al leer el archivo CSV con codificación {encoding}: {str(e)}")
                
        # Si llegamos aquí, no pudimos leer con ninguna codificación
        logger.error(f"No se pudo leer el archivo CSV con ninguna de las codificaciones intentadas")
        return []
    
    @staticmethod
    def convertir_txt_a_csv(ruta_txt, ruta_csv=None):
        """
        Convierte un archivo de texto plano (formato antiguo) a formato CSV.
        
        Formato antiguo (TXT):
        Nombre y apellido del contribuyente
        CUIT sin guiones
        clave
        
        Args:
            ruta_txt (str): Ruta al archivo de texto
            ruta_csv (str, optional): Ruta donde guardar el archivo CSV resultante.
                                     Si no se especifica, se usará el mismo nombre con extensión .csv
                                     
        Returns:
            str: Ruta al archivo CSV creado o None si hubo un error
        """
        if not os.path.exists(ruta_txt):
            logger.error(f"No se encontró el archivo de texto: {ruta_txt}")
            return None
            
        if not ruta_csv:
            # Usar el mismo nombre de archivo pero con extensión .csv
            ruta_csv = os.path.splitext(ruta_txt)[0] + '.csv'
            
        try:
            contribuyentes = []
            nombre_actual = None
            cuit_actual = None
            clave_actual = None
            
            # Leer el archivo TXT
            with open(ruta_txt, 'r', encoding='utf-8') as archivo_txt:
                lineas = [linea.strip() for linea in archivo_txt if linea.strip() and not linea.strip().startswith('#')]
                
                # Procesar por bloques de 3 líneas (nombre, cuit, clave)
                i = 0
                while i < len(lineas):
                    # Si encontramos la línea de instrucciones, saltar
                    if "ES IMPORTANTE DEJAR ESPACIO" in lineas[i] or "sin guiones" in lineas[i] or "creara carpeta" in lineas[i]:
                        i += 1
                        continue
                    
                    # Primera línea: nombre
                    if i < len(lineas):
                        nombre_actual = lineas[i].strip()
                        i += 1
                    else:
                        break
                    
                    # Segunda línea: cuit
                    if i < len(lineas):
                        cuit_actual = lineas[i].strip()
                        i += 1
                    else:
                        break
                    
                    # Tercera línea: clave
                    if i < len(lineas):
                        clave_actual = lineas[i].strip()
                        i += 1
                    else:
                        break
                    
                    # Agregar contribuyente si tenemos todos los datos
                    if nombre_actual and cuit_actual and clave_actual:
                        # Verificar que no sean las líneas de instrucciones
                        if not ("sin guiones" in cuit_actual or "creara carpeta" in nombre_actual):
                            contribuyente = {
                                'nombre': nombre_actual,
                                'cuit': cuit_actual,
                                'clave_fiscal': clave_actual
                            }
                            contribuyentes.append(contribuyente)
                            logger.info(f"Contribuyente agregado: {nombre_actual}")
                    
                    # Limpiar para el siguiente
                    nombre_actual = None
                    cuit_actual = None
                    clave_actual = None
            
            # Escribir el archivo CSV
            with open(ruta_csv, 'w', encoding='utf-8', newline='') as archivo_csv:
                campos = ['nombre', 'cuit', 'clave_fiscal']
                escritor = csv.DictWriter(archivo_csv, fieldnames=campos)
                escritor.writeheader()
                
                for contribuyente in contribuyentes:
                    escritor.writerow(contribuyente)
                    
            logger.info(f"Se convirtieron {len(contribuyentes)} contribuyentes de TXT a CSV en {ruta_csv}")
            return ruta_csv
            
        except Exception as e:
            logger.error(f"Error al convertir de TXT a CSV: {e}")
            return None
    
    @staticmethod
    def crear_csv_ejemplo(ruta_salida):
        """
        Crea un archivo CSV de ejemplo para mostrar el formato correcto
        
        Args:
            ruta_salida (str): Ruta donde guardar el archivo CSV de ejemplo
            
        Returns:
            bool: True si se creó correctamente, False en caso contrario
        """
        try:
            # Crear directorio si no existe
            directorio = os.path.dirname(ruta_salida)
            if directorio and not os.path.exists(directorio):
                os.makedirs(directorio, exist_ok=True)
            
            with open(ruta_salida, 'w', encoding='utf-8', newline='') as archivo:
                campos = ['nombre', 'cuit', 'clave_fiscal']
                escritor = csv.DictWriter(archivo, fieldnames=campos)
                escritor.writeheader()
                
                # Agregar dos ejemplos
                escritor.writerow({
                    'nombre': 'Contribuyente Ejemplo',
                    'cuit': '20123456789',
                    'clave_fiscal': 'contraseña123'
                })
                
                escritor.writerow({
                    'nombre': 'Empresa Ejemplo',
                    'cuit': '30987654321', 
                    'clave_fiscal': 'clave456'
                })
                
            logger.info(f"Se creó un archivo CSV de ejemplo en {ruta_salida}")
            return True
            
        except Exception as e:
            logger.error(f"Error al crear el archivo CSV de ejemplo: {e}")
            return False 