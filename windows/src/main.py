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
from datetime import datetime

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
        self.anio = tk.StringVar(value=str(datetime.now().year))  # Año actual por defecto
        self.sobrescribir = tk.BooleanVar(value=False)
        self.output_dir = tk.StringVar()
        
        # Directorio de trabajo (donde se guardarán los resultados)
        self.working_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir.set(self.working_dir)  # Directorio de trabajo por defecto
        
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
        ttk.Label(header_frame, text="Seleccione un archivo CSV").pack()
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
        
        # Frame para configuración adicional
        config_frame = ttk.Frame(main_frame, padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Año a analizar
        ttk.Label(config_frame, text="Año a analizar:").grid(row=0, column=0, sticky=tk.W, padx=5)
        entry_anio = ttk.Entry(config_frame, textvariable=self.anio, width=6)
        entry_anio.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Opción de sobrescribir
        check_sobrescribir = ttk.Checkbutton(
            config_frame, 
            text="Sobrescribir archivos existentes",
            variable=self.sobrescribir
        )
        check_sobrescribir.grid(row=0, column=2, sticky=tk.W, padx=20)
        
        # Directorio de resultados
        ttk.Label(config_frame, text="Directorio de resultados:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        entry_output = ttk.Entry(config_frame, textvariable=self.output_dir, width=50)
        entry_output.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        browse_output_button = ttk.Button(config_frame, text="Explorar...", command=self._browse_output_dir)
        browse_output_button.grid(row=1, column=3, padx=5, pady=5)
        
        config_frame.columnconfigure(1, weight=1)  # Hacer que el entry se expanda
        
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
        
        # Botón para procesar contribuyentes
        process_button = ttk.Button(action_frame, text="Procesar Contribuyentes", command=self._process_contribuyentes)
        process_button.pack(side=tk.LEFT, padx=5)
        
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
    
    def _browse_output_dir(self):
        """Abre un diálogo para seleccionar el directorio de resultados"""
        dirname = filedialog.askdirectory(
            title="Seleccionar directorio de resultados",
            initialdir=self.output_dir.get()
        )
        
        if dirname:
            self.output_dir.set(dirname)
            logger.info(f"Directorio de resultados seleccionado: {dirname}")
            self.status_var.set(f"Directorio de resultados: {dirname}")
    
    def _process_contribuyentes(self):
        """Procesa los contribuyentes con las opciones seleccionadas"""
        if not self.contribuyentes:
            messagebox.showwarning("Advertencia", "Por favor, cargue los contribuyentes primero.")
            return
            
        # Validar el año
        try:
            año = int(self.anio.get())
            if año < 2018 or año > datetime.now().year:
                messagebox.showerror(
                    "Error", 
                    f"El año debe estar entre 2018 y {datetime.now().year}"
                )
                return
        except ValueError:
            messagebox.showerror("Error", "El año debe ser un número válido.")
            return
            
        # Validar directorio de resultados
        output_dir = self.output_dir.get()
        if not output_dir:
            messagebox.showerror("Error", "Por favor, seleccione un directorio para los resultados.")
            return
            
        # Crear el extractor
        extractor = NuestraParteExtractor()
        
        # Configurar opciones
        extractor.output_folder = output_dir
        
        # Procesar contribuyentes
        try:
            self.status_var.set("Procesando contribuyentes...")
            self.root.update()
            
            # Ejecutar el procesamiento
            extractor.ejecutar(
                año=str(año),
                csv_file=self.csv_file_path.get(),
                sobrescribir=self.sobrescribir.get()
            )
            
            self.status_var.set("Procesamiento completado")
            messagebox.showinfo(
                "Completado",
                f"Se ha completado el procesamiento de {len(self.contribuyentes)} contribuyentes.\n"
                f"Los resultados se encuentran en: {output_dir}"
            )
            
        except Exception as e:
            error_msg = f"Error durante el procesamiento: {e}"
            logger.error(error_msg)
            messagebox.showerror("Error", error_msg)
            self.status_var.set("Error durante el procesamiento")

def main():
    """Función principal que inicia la aplicación"""
    root = tk.Tk()
    app = AFIPExtractorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 