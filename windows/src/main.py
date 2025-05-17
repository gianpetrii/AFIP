#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AFIP Nuestra Parte Extractor - Versión Windows
Interfaz gráfica para seleccionar archivos CSV
"""

import os
import sys
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

# Agregar el directorio padre al path para poder importar utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.csv_utils import CSVHandler

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("afip_extractor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AFIPExtractorApp:
    """Aplicación principal para AFIP Extractor con interfaz gráfica"""
    
    def __init__(self, root):
        """
        Inicializa la aplicación.
        
        Args:
            root: La ventana raíz de Tkinter
        """
        self.root = root
        self.root.title("AFIP Nuestra Parte Extractor")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # Variables para almacenar datos
        self.csv_file_path = tk.StringVar()
        self.contribuyentes = []
        
        # Directorio de trabajo (donde se guardarán los resultados)
        self.working_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Configurar la interfaz
        self._setup_ui()
        
        logger.info("AFIP Extractor GUI iniciada")
        
    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        # Estilo
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6, relief="flat", background="#ccc")
        self.style.configure("TLabel", padding=6)
        self.style.configure("Header.TLabel", font=("Arial", 14, "bold"))
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header con título
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="AFIP Nuestra Parte Extractor", style="Header.TLabel").pack()
        ttk.Label(header_frame, text="Seleccione un archivo CSV con los datos de los contribuyentes").pack()
        ttk.Label(header_frame, text="El archivo debe tener tres columnas: Contribuyente, CUIT y Clave Fiscal").pack()
        
        # Frame para selección de archivo
        file_frame = ttk.Frame(main_frame, padding="10")
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(file_frame, text="Archivo CSV:").grid(row=0, column=0, sticky=tk.W)
        
        # Entry para mostrar la ruta del archivo
        entry_file = ttk.Entry(file_frame, textvariable=self.csv_file_path, width=50)
        entry_file.grid(row=0, column=1, padx=5, sticky=tk.W+tk.E)
        
        # Botón para explorar archivos
        browse_button = ttk.Button(file_frame, text="Explorar...", command=self._browse_csv_file)
        browse_button.grid(row=0, column=2, padx=5)
        
        file_frame.columnconfigure(1, weight=1)  # Hacer que el entry se expanda
        
        # Frame para mostrar información y acciones
        info_frame = ttk.Frame(main_frame, padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tabla para mostrar contribuyentes
        self.tree = ttk.Treeview(info_frame, columns=("nombre", "cuit", "clave"), show="headings", height=15)
        self.tree.heading("nombre", text="Contribuyente")
        self.tree.heading("cuit", text="CUIT")
        self.tree.heading("clave", text="Clave Fiscal")
        
        self.tree.column("nombre", width=200)
        self.tree.column("cuit", width=120)
        self.tree.column("clave", width=120)
        
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Scrollbar para la tabla
        scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Frame para botones de acción
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Botón para mostrar los contribuyentes
        load_button = ttk.Button(action_frame, text="Cargar Contribuyentes", command=self._load_contribuyentes)
        load_button.pack(side=tk.LEFT, padx=5)
        
        # Botón para crear archivo de ejemplo
        example_button = ttk.Button(action_frame, text="Crear Archivo de Ejemplo", command=self._create_example_file)
        example_button.pack(side=tk.LEFT, padx=5)
        
        # Área de estado
        self.status_var = tk.StringVar()
        self.status_var.set("Listo")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _browse_csv_file(self):
        """Abre un diálogo para seleccionar un archivo CSV"""
        filetypes = [("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=filetypes,
            initialdir=self.working_dir
        )
        
        if filename:
            self.csv_file_path.set(filename)
            logger.info(f"Archivo seleccionado: {filename}")
            self.status_var.set(f"Archivo seleccionado: {os.path.basename(filename)}")
            
            # Cargar automáticamente los contribuyentes
            self._load_contribuyentes()
    
    def _load_contribuyentes(self):
        """Carga los contribuyentes desde el archivo CSV seleccionado"""
        csv_file = self.csv_file_path.get()
        
        if not csv_file:
            messagebox.showwarning("Advertencia", "Por favor, seleccione un archivo CSV primero.")
            return
            
        try:
            # Limpiar la tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            # Cargar contribuyentes
            self.contribuyentes = CSVHandler.leer_contribuyentes(csv_file)
            
            if not self.contribuyentes:
                messagebox.showinfo(
                    "Información", 
                    "No se encontraron contribuyentes válidos en el archivo CSV.\n\n"
                    "Asegúrese de que el archivo tiene al menos tres columnas:\n"
                    "1. Contribuyente (Nombre)\n"
                    "2. CUIT (solo dígitos)\n"
                    "3. Clave Fiscal"
                )
                self.status_var.set("No se encontraron contribuyentes válidos en el archivo")
                return
                
            # Mostrar contribuyentes en la tabla
            for i, contrib in enumerate(self.contribuyentes):
                # Ocultar la clave fiscal por seguridad (mostrar asteriscos)
                clave_oculta = '*' * len(contrib.get('clave_fiscal', ''))
                
                self.tree.insert("", tk.END, values=(
                    contrib.get('nombre', ''),
                    contrib.get('cuit', ''),
                    clave_oculta
                ))
                
            self.status_var.set(f"Se cargaron {len(self.contribuyentes)} contribuyentes")
            logger.info(f"Se cargaron {len(self.contribuyentes)} contribuyentes de {csv_file}")
            
        except Exception as e:
            error_msg = f"Error al cargar el archivo CSV: {e}"
            logger.error(error_msg)
            messagebox.showerror("Error", error_msg)
            self.status_var.set("Error al cargar el archivo")
    
    def _create_example_file(self):
        """Crea un archivo CSV de ejemplo"""
        filetypes = [("Archivos CSV", "*.csv")]
        filename = filedialog.asksaveasfilename(
            title="Guardar archivo de ejemplo",
            filetypes=filetypes,
            defaultextension=".csv",
            initialdir=self.working_dir,
            initialfile="clientes_ejemplo.csv"
        )
        
        if filename:
            try:
                if CSVHandler.crear_csv_ejemplo(filename):
                    messagebox.showinfo(
                        "Información", 
                        f"Se ha creado el archivo de ejemplo en:\n{filename}\n\n"
                        f"El archivo contiene tres columnas:\n"
                        f"1. Contribuyente (Nombre)\n"
                        f"2. CUIT (solo dígitos)\n"
                        f"3. Clave Fiscal\n\n"
                        f"Puede editarlo con sus datos y luego cargarlo en la aplicación."
                    )
                    self.status_var.set(f"Archivo de ejemplo creado: {os.path.basename(filename)}")
                    logger.info(f"Archivo de ejemplo creado: {filename}")
                else:
                    messagebox.showerror("Error", "No se pudo crear el archivo de ejemplo.")
            except Exception as e:
                error_msg = f"Error al crear archivo de ejemplo: {e}"
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)

def main():
    """Función principal que inicia la aplicación"""
    root = tk.Tk()
    app = AFIPExtractorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 