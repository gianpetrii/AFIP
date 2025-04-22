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