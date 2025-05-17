#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilidades para manejo de archivos CSV en AFIP Extractor
"""

import os
import csv
import logging
import re

# Configurar logging
logger = logging.getLogger(__name__)

class CSVHandler:
    """Clase para manejar operaciones con archivos CSV"""
    
    @staticmethod
    def leer_contribuyentes(csv_file):
        """
        Lee la lista de contribuyentes desde un archivo CSV.
        Toma los valores directamente por posición:
        - Primera columna: Nombre del contribuyente
        - Segunda columna: CUIT (debe contener solo dígitos)
        - Tercera columna: Clave fiscal
        
        Args:
            csv_file (str): Ruta al archivo CSV con los datos de los contribuyentes
        
        Returns:
            list: Lista de diccionarios con información de contribuyentes
        """
        try:
            contribuyentes = []
            
            # Abrir el archivo CSV
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                # Leer todas las filas como listas
                csv_reader = csv.reader(f)
                
                # Saltar la primera fila (encabezados)
                next(csv_reader, None)
                
                # Procesar cada fila
                for i, row in enumerate(csv_reader, 1):
                    # Verificar que la fila tenga al menos 3 columnas
                    if len(row) < 3:
                        logger.warning(f"La fila {i} no tiene las 3 columnas requeridas. Ignorando.")
                        continue
                    
                    # Obtener valores y eliminar espacios en blanco y saltos de línea
                    nombre = row[0].strip().replace('\n', ' ').replace('\r', '')
                    cuit = row[1].strip().replace('\n', '').replace('\r', '')
                    clave_fiscal = row[2].strip().replace('\n', '').replace('\r', '')
                    
                    # Validar que el nombre no esté vacío
                    if not nombre:
                        logger.warning(f"La fila {i} tiene un nombre vacío. Ignorando.")
                        continue
                    
                    # Validar que el CUIT solo contenga dígitos
                    cuit_sin_caracteres = re.sub(r'[^0-9]', '', cuit)
                    if not cuit_sin_caracteres:
                        logger.warning(f"La fila {i} tiene un CUIT inválido (sin dígitos). Ignorando.")
                        continue
                    
                    # Asegurar que el CUIT tenga 11 dígitos
                    if len(cuit_sin_caracteres) < 11:
                        # Si tiene 10 dígitos, agregar un 0 al inicio
                        if len(cuit_sin_caracteres) == 10:
                            cuit_sin_caracteres = '0' + cuit_sin_caracteres
                        else:
                            logger.warning(f"La fila {i} tiene un CUIT con menos de 10 dígitos. Ignorando.")
                            continue
                    elif len(cuit_sin_caracteres) > 11:
                        logger.warning(f"La fila {i} tiene un CUIT con más de 11 dígitos. Truncando a 11.")
                        cuit_sin_caracteres = cuit_sin_caracteres[:11]
                    
                    # Validar que la clave fiscal no esté vacía
                    if not clave_fiscal:
                        logger.warning(f"La fila {i} tiene una clave fiscal vacía. Ignorando.")
                        continue
                    
                    # Crear diccionario con los datos validados
                    contribuyente = {
                        'nombre': nombre,
                        'cuit': cuit_sin_caracteres,
                        'clave_fiscal': clave_fiscal
                    }
                    
                    contribuyentes.append(contribuyente)
                    
            if not contribuyentes:
                logger.warning(f"El archivo CSV {csv_file} no contiene contribuyentes válidos")
                return []
                
            logger.info(f"Se leyeron {len(contribuyentes)} contribuyentes del archivo {csv_file}")
            return contribuyentes
            
        except Exception as e:
            logger.error(f"Error al leer el archivo CSV {csv_file}: {e}")
            raise
    
    @staticmethod
    def crear_csv_ejemplo(archivo_destino):
        """
        Crea un archivo CSV de ejemplo que el usuario puede usar como referencia.
        
        Args:
            archivo_destino (str): Ruta donde crear el archivo de ejemplo
            
        Returns:
            bool: True si se creó correctamente, False en caso contrario
        """
        try:
            with open(archivo_destino, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # Escribir encabezado
                writer.writerow(['Contribuyente', 'CUIT', 'Clave Fiscal'])
                # Escribir ejemplos
                writer.writerow(['Juan Perez', '20123456789', 'clave123'])
                writer.writerow(['Empresa SA', '30987654321', 'clave456'])
                
            logger.info(f"Archivo de ejemplo creado: {archivo_destino}")
            return True
            
        except Exception as e:
            logger.error(f"Error al crear archivo CSV de ejemplo: {e}")
            return False 