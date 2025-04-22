def close(self):
    """Cerrar el navegador y limpiar temporales."""
    if hasattr(self, 'driver'):
        try:
            self.driver.quit()
            logger.info("Navegador cerrado correctamente")
        except Exception as e:
            logger.warning(f"Error al cerrar el navegador: {e}") 