#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades para manejar navegadores web en el Extractor AFIP.
Este módulo contiene funciones para verificar la instalación de Chrome
y descargar/instalar Chrome cuando sea necesario.
"""

import os
import sys
import platform
import logging
import subprocess
import shutil
from pathlib import Path

# Configurar logging
logger = logging.getLogger(__name__)

def verificar_chrome_instalado():
    """
    Verifica si Google Chrome está instalado en el sistema.
    
    Returns:
        bool: True si Chrome está instalado, False en caso contrario
    """
    try:
        sistema = platform.system().lower()
        
        if sistema == "windows":
            # En Windows, verificar en las rutas comunes de instalación
            rutas_chrome = [
                os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google\\Chrome\\Application\\chrome.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe'),
                os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\Users\\Default\\AppData\\Local'), 'Google\\Chrome\\Application\\chrome.exe')
            ]
            
            for ruta in rutas_chrome:
                if os.path.exists(ruta):
                    logger.info(f"Chrome encontrado en: {ruta}")
                    return True
                
            logger.warning("Chrome no encontrado en rutas comunes de Windows")
            return False
            
        elif sistema == "linux":
            # En Linux, usar 'which' para buscar el ejecutable chrome o google-chrome
            try:
                result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    logger.info(f"Chrome encontrado en: {result.stdout.strip()}")
                    return True
                    
                result = subprocess.run(['which', 'chrome'], capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    logger.info(f"Chrome encontrado en: {result.stdout.strip()}")
                    return True
                    
                # Verificar en rutas comunes en Linux
                rutas_linux = [
                    '/usr/bin/google-chrome',
                    '/usr/bin/google-chrome-stable',
                    '/usr/bin/chrome',
                    '/snap/bin/google-chrome'
                ]
                
                for ruta in rutas_linux:
                    if os.path.exists(ruta):
                        logger.info(f"Chrome encontrado en: {ruta}")
                        return True
                        
                logger.warning("Chrome no encontrado en el sistema Linux")
                return False
            except Exception as e:
                logger.error(f"Error al verificar Chrome en Linux: {e}")
                return False
                
        elif sistema == "darwin":  # macOS
            # En macOS, verificar en la carpeta de Aplicaciones
            chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            if os.path.exists(chrome_path):
                logger.info(f"Chrome encontrado en: {chrome_path}")
                return True
                
            logger.warning("Chrome no encontrado en macOS")
            return False
            
        else:
            logger.warning(f"Sistema operativo no soportado para verificación de Chrome: {sistema}")
            return False
            
    except Exception as e:
        logger.error(f"Error al verificar instalación de Chrome: {e}")
        return False

def descargar_chrome():
    """
    Proporciona instrucciones para descargar e instalar Chrome.
    
    Returns:
        str: Instrucciones para la instalación de Chrome
    """
    sistema = platform.system().lower()
    
    if sistema == "windows":
        return """
        Para instalar Google Chrome en Windows:
        1. Visita https://www.google.com/chrome/
        2. Haz clic en "Descargar Chrome"
        3. Ejecuta el instalador descargado y sigue las instrucciones
        """
    elif sistema == "linux":
        # Detectar distribución de Linux
        try:
            # Verificar si es Ubuntu/Debian
            if os.path.exists('/etc/debian_version') or os.path.exists('/etc/lsb-release'):
                return """
                Para instalar Google Chrome en Ubuntu/Debian:
                1. Abre una terminal
                2. Ejecuta los siguientes comandos:
                   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
                   sudo apt update
                   sudo apt install ./google-chrome-stable_current_amd64.deb
                """
            # Verificar si es Fedora/RHEL/CentOS
            elif os.path.exists('/etc/fedora-release') or os.path.exists('/etc/redhat-release'):
                return """
                Para instalar Google Chrome en Fedora/RHEL/CentOS:
                1. Abre una terminal
                2. Ejecuta los siguientes comandos:
                   sudo dnf install wget
                   wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
                   sudo dnf install ./google-chrome-stable_current_x86_64.rpm
                """
            # Verificar si es Arch Linux
            elif os.path.exists('/etc/arch-release'):
                return """
                Para instalar Google Chrome en Arch Linux:
                1. Abre una terminal
                2. Ejecuta el siguiente comando:
                   sudo pacman -S chromium
                """
            else:
                return """
                Para instalar Google Chrome en Linux:
                1. Visita https://www.google.com/chrome/
                2. Descarga la versión para tu distribución de Linux
                3. Instala el paquete descargado usando el gestor de paquetes de tu distribución
                """
        except Exception:
            return """
            Para instalar Google Chrome en Linux:
            1. Visita https://www.google.com/chrome/
            2. Descarga la versión para tu distribución de Linux
            3. Instala el paquete descargado usando el gestor de paquetes de tu distribución
            """
    elif sistema == "darwin":  # macOS
        return """
        Para instalar Google Chrome en macOS:
        1. Visita https://www.google.com/chrome/
        2. Haz clic en "Descargar Chrome"
        3. Abre el archivo .dmg descargado
        4. Arrastra el icono de Google Chrome a la carpeta de Aplicaciones
        """
    else:
        return """
        Para instalar Google Chrome:
        1. Visita https://www.google.com/chrome/
        2. Descarga la versión para tu sistema operativo
        3. Sigue las instrucciones de instalación específicas para tu sistema
        """

def instalar_chrome_wsl():
    """
    Intenta instalar Chrome en WSL (Windows Subsystem for Linux)
    
    Returns:
        bool: True si la instalación fue exitosa, False en caso contrario
    """
    try:
        # Verificar si estamos en WSL
        if not is_wsl():
            logger.error("Esta función solo es válida en WSL")
            return False
            
        logger.info("Intentando instalar Google Chrome en WSL...")
        
        # Descargar el paquete .deb de Chrome
        download_cmd = "wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb"
        logger.info("Descargando Google Chrome...")
        result = subprocess.run(download_cmd, shell=True, check=False)
        
        if result.returncode != 0:
            logger.error("Error al descargar Chrome")
            return False
            
        # Instalar dependencias
        logger.info("Instalando dependencias...")
        deps_cmd = "sudo apt update && sudo apt install -y gdebi-core"
        result = subprocess.run(deps_cmd, shell=True, check=False)
        
        if result.returncode != 0:
            logger.error("Error al instalar dependencias")
            return False
            
        # Instalar Chrome
        logger.info("Instalando Google Chrome...")
        install_cmd = "sudo gdebi -n /tmp/chrome.deb"
        result = subprocess.run(install_cmd, shell=True, check=False)
        
        if result.returncode != 0:
            logger.error("Error al instalar Chrome")
            return False
            
        # Limpiar archivos temporales
        cleanup_cmd = "rm /tmp/chrome.deb"
        subprocess.run(cleanup_cmd, shell=True, check=False)
        
        # Verificar que la instalación fue exitosa
        if verificar_chrome_instalado():
            logger.info("Google Chrome instalado correctamente en WSL")
            return True
        else:
            logger.error("No se pudo verificar la instalación de Chrome")
            return False
            
    except Exception as e:
        logger.error(f"Error al instalar Chrome en WSL: {e}")
        return False

def is_wsl():
    """
    Determina si el código se está ejecutando en WSL (Windows Subsystem for Linux)
    
    Returns:
        bool: True si es WSL, False en caso contrario
    """
    try:
        # Métodos específicos para detectar WSL
        # 1. Verificar /proc/version
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                version_content = f.read().lower()
                if 'microsoft' in version_content or 'wsl' in version_content:
                    return True
        
        # 2. Verificar /proc/sys/kernel/osrelease
        if os.path.exists('/proc/sys/kernel/osrelease'):
            with open('/proc/sys/kernel/osrelease', 'r') as f:
                osrelease_content = f.read().lower()
                if 'microsoft' in osrelease_content or 'wsl' in osrelease_content:
                    return True
                    
        return False
    except Exception:
        return False

def obtener_version_chrome():
    """
    Obtiene la versión de Chrome instalada
    
    Returns:
        str: Versión de Chrome o None si no se pudo determinar
    """
    try:
        sistema = platform.system().lower()
        
        if sistema == "windows":
            # Intentar obtener versión en Windows usando el registro
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
                version, _ = winreg.QueryValueEx(key, "version")
                return version
            except:
                # Si falla, intentar con PowerShell
                try:
                    cmd = 'powershell -command "(Get-Item \'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\').VersionInfo.FileVersion"'
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=False)
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip()
                except:
                    pass
                    
                # Intentar con el ejecutable en Program Files (x86)
                try:
                    cmd = 'powershell -command "(Get-Item \'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe\').VersionInfo.FileVersion"'
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=False)
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip()
                except:
                    pass
            
            return None
                
        elif sistema == "linux":
            # En Linux, usar google-chrome --version
            try:
                cmd = "google-chrome --version"
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=False)
                if result.returncode == 0 and result.stdout:
                    # Extraer versión del formato "Google Chrome XX.X.XXXX.XX"
                    import re
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        return match.group(1)
            except:
                pass
                
            # Intentar con google-chrome-stable
            try:
                cmd = "google-chrome-stable --version"
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=False)
                if result.returncode == 0 and result.stdout:
                    import re
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        return match.group(1)
            except:
                pass
                
            return None
                
        elif sistema == "darwin":  # macOS
            # En macOS, usar la ruta de aplicación
            try:
                cmd = '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --version'
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=False)
                if result.returncode == 0 and result.stdout:
                    import re
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        return match.group(1)
            except:
                pass
                
            return None
        
        return None
    except Exception as e:
        logger.error(f"Error al obtener versión de Chrome: {e}")
        return None

def limpiar_cache_chromedriver():
    """
    Limpia el caché del WebDriver Manager para forzar una nueva descarga de ChromeDriver
    
    Returns:
        bool: True si se limpió correctamente, False en caso contrario
    """
    try:
        import os
        import shutil
        
        # Limpiar caché de webdriver-manager
        cache_dir = os.path.expanduser("~/.wdm/drivers/chromedriver")
        if os.path.exists(cache_dir):
            logger.info(f"Limpiando caché del chromedriver en: {cache_dir}")
            shutil.rmtree(cache_dir, ignore_errors=True)
            return True
        return False
    except Exception as e:
        logger.error(f"Error al limpiar caché de chromedriver: {e}")
        return False

if __name__ == "__main__":
    # Configurar logging básico para pruebas
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Verificar si Chrome está instalado
    if verificar_chrome_instalado():
        print("Google Chrome está instalado en este sistema.")
        version = obtener_version_chrome()
        if version:
            print(f"Versión de Chrome: {version}")
    else:
        print("Google Chrome NO está instalado en este sistema.")
        instrucciones = descargar_chrome()
        print("\nInstrucciones de instalación:")
        print(instrucciones)
        
        # Si estamos en WSL, ofrecer instalación automática
        if is_wsl():
            print("\nSe detectó que estás utilizando WSL (Windows Subsystem for Linux).")
            respuesta = input("¿Deseas intentar instalar Chrome automáticamente? (s/n): ")
            if respuesta.lower() in ['s', 'si', 'sí', 'y', 'yes']:
                if instalar_chrome_wsl():
                    print("Chrome instalado correctamente.")
                else:
                    print("No se pudo instalar Chrome automáticamente. Por favor, sigue las instrucciones manuales.") 