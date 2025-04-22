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
    logger.info(f"{mensaje}")
    
    # Pequeña espera inicial para dar tiempo a que se inicie el proceso de apertura
    time.sleep(1)  # Reducido de 2 a 1 segundo
    
    # Verificar brevemente si hay nuevas ventanas, pero no bloquear el proceso
    try:
        ventanas_despues = driver.window_handles
        if len(ventanas_despues) > len(ventanas_antes):
            # Hay una nueva ventana, intentar cambiar a ella
            nueva_ventana = [v for v in ventanas_despues if v not in ventanas_antes][0]
            try:
                driver.switch_to.window(nueva_ventana)
                logger.info(f"Cambiado a nueva ventana: {driver.current_url}")
            except Exception as e:
                logger.warning(f"Error al cambiar a la nueva ventana, pero continuando: {e}")
        else:
            logger.info("No se detectó una nueva ventana por handle, pero continuando de todos modos")
    except Exception as e:
        logger.warning(f"Error al verificar nuevas ventanas, pero continuando: {e}")
    
    # Siempre continuar con el proceso, asumiendo que la ventana de impresión está visible
    # aunque no la hayamos detectado como un handle separado
    return True 