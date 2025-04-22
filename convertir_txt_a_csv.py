#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidad para convertir archivos TXT al nuevo formato CSV en AFIP Extractor.

Este script permite convertir archivos de texto plano con formato antiguo
al nuevo formato CSV requerido por el extractor AFIP.
"""

import os
import sys
import argparse
import logging
from utils.csv_utils import CSVHandler

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Conversor TXT a CSV")

def main():
    """
    Función principal que maneja la conversión de archivos TXT a CSV.
    
    Parsea los argumentos de línea de comandos, verifica la existencia del archivo
    de entrada y realiza la conversión utilizando el CSVHandler.
    
    Returns:
        int: Código de salida (0 en caso de éxito, 1 en caso de error)
    """
    # Configurar el parser de argumentos
    parser = argparse.ArgumentParser(
        description="Convertir archivo TXT de contribuyentes al formato CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplo de uso:
  python convertir_txt_a_csv.py archivo.txt
  python convertir_txt_a_csv.py archivo.txt -o contribuyentes.csv
        """
    )
    
    parser.add_argument(
        "archivo_txt",
        help="Ruta del archivo TXT a convertir"
    )
    
    parser.add_argument(
        "--salida", "-o",
        help="Archivo de salida (por defecto se usa el mismo nombre con extensión .csv)",
        type=str,
        default=None
    )
    
    args = parser.parse_args()
    
    # Verificar que el archivo de entrada exista
    if not os.path.exists(args.archivo_txt):
        logger.error(f"El archivo {args.archivo_txt} no existe.")
        return 1
    
    try:
        # Realizar la conversión
        archivo_salida = CSVHandler.convertir_txt_a_csv(args.archivo_txt, args.salida)
        
        if archivo_salida:
            logger.info(f"✅ Archivo convertido exitosamente a: {archivo_salida}")
            logger.info(f"   Úselo con el comando: python afip_extractor.py --file {archivo_salida}")
            return 0
        else:
            logger.error("❌ Error al convertir el archivo.")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 