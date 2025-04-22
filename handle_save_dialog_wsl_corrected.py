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