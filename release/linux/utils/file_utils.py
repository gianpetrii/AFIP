#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades para el manejo de archivos y rutas en el Extractor AFIP.

Este módulo contiene funciones para normalizar nombres de archivos,
gestionar rutas y manejar caracteres especiales en los nombres.
"""

import os
import re
import unicodedata
import logging
import shutil

# Configurar logging
logger = logging.getLogger(__name__)

def normalizar_nombre(nombre, max_length=80):
    """
    Normaliza un nombre para usarlo como nombre de archivo o carpeta.
    
    Esta función:
    - Elimina caracteres no permitidos en rutas de archivo
    - Reemplaza espacios por guiones bajos
    - Limita la longitud para evitar problemas con rutas largas
    - Maneja caracteres especiales, acentos y eñes correctamente
    
    Args:
        nombre (str): Nombre a normalizar
        max_length (int, optional): Longitud máxima permitida. Por defecto 80.
        
    Returns:
        str: Nombre normalizado seguro para usar en rutas de archivo
    """
    if not nombre or nombre.strip() == "":
        return "sin_nombre"
    
    # Primero, limpiar espacios extras y caracteres de control
    resultado = nombre.strip()
    
    # Convertir caracteres especiales (como ñ, tildes) a ASCII
    # Esto preserva los caracteres básicos y reemplaza los especiales
    # de manera consistente en todas las plataformas
    resultado = unicodedata.normalize('NFKD', resultado)
    resultado = ''.join([c for c in resultado if not unicodedata.combining(c)])
    
    # Reemplazar caracteres no permitidos en nombres de archivo
    caracteres_invalidos = r'[<>:"/\\|?*]'
    resultado = re.sub(caracteres_invalidos, '_', resultado)
    
    # Reemplazar múltiples espacios por uno solo
    resultado = re.sub(r'\s+', ' ', resultado)
    
    # Reemplazar espacios por guiones bajos
    resultado = resultado.replace(' ', '_')
    
    # Eliminar posibles guiones bajos múltiples
    resultado = re.sub(r'_{2,}', '_', resultado)
    
    # Limitar longitud
    if len(resultado) > max_length:
        resultado = resultado[:max_length]
    
    # Eliminar posibles guiones al final
    resultado = resultado.rstrip('_')
    
    return resultado

def crear_estructura_carpetas(ruta, crear_si_existe=True):
    """
    Crea una estructura de carpetas asegurando que exista.
    
    Args:
        ruta (str): Ruta de la carpeta a crear
        crear_si_existe (bool): Si es True, crea la carpeta aunque ya exista
        
    Returns:
        bool: True si se creó o ya existe la carpeta, False en caso de error
    """
    try:
        if os.path.exists(ruta) and not crear_si_existe:
            logger.info(f"La carpeta ya existe: {ruta}")
            return True
            
        os.makedirs(ruta, exist_ok=True)
        logger.info(f"Carpeta creada: {ruta}")
        return True
    except Exception as e:
        logger.error(f"Error al crear carpeta {ruta}: {e}")
        return False

def limpiar_carpeta(ruta):
    """
    Elimina todo el contenido de una carpeta.
    
    Args:
        ruta (str): Ruta de la carpeta a limpiar
        
    Returns:
        bool: True si se limpió correctamente, False en caso de error
    """
    try:
        if not os.path.exists(ruta):
            logger.warning(f"La carpeta no existe: {ruta}")
            return True
        
        for item in os.listdir(ruta):
            item_path = os.path.join(ruta, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
                
        logger.info(f"Carpeta limpiada: {ruta}")
        return True
    except Exception as e:
        logger.error(f"Error al limpiar carpeta {ruta}: {e}")
        return False

def verificar_archivo_existe(ruta, timeout=30, intervalo=0.5):
    """
    Verifica si un archivo existe con timeout.
    
    Args:
        ruta (str): Ruta del archivo a verificar
        timeout (float): Tiempo máximo de espera en segundos
        intervalo (float): Intervalo entre verificaciones
        
    Returns:
        bool: True si el archivo existe, False si no existe después del timeout
    """
    import time
    tiempo_inicio = time.time()
    
    while (time.time() - tiempo_inicio) < timeout:
        if os.path.exists(ruta):
            return True
        time.sleep(intervalo)
    
    return False 