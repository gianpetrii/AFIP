#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidad para convertir archivos TXT al nuevo formato CSV en AFIP Extractor.
"""

import os
import sys
import argparse
from csv_utils import CSVHandler
import logging

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
    parser = argparse.ArgumentParser(description="Convertir archivo TXT de contribuyentes al formato CSV")
    
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
    
    if not os.path.exists(args.archivo_txt):
        logger.error(f"El archivo {args.archivo_txt} no existe.")
        return 1
    
    try:
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