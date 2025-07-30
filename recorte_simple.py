import pyscreeze
from PIL import Image, ImageTk, ImageEnhance
import tkinter as tk
from tkinter import ttk, Toplevel, Button, messagebox, Canvas, Text, Frame, Label, Entry, StringVar
import base64
import io
import requests
import threading
import json
from dotenv import load_dotenv
import os
load_dotenv()
# --- CONFIGURACIÓN --- #
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

DEFAULT_MODEL = "Qwen2.5 VL 72B (Free)"
# Número de capturas antes de actualizar automáticamente el uso de API
CAPTURAS_ANTES_ACTUALIZAR = 5

MODEL_MAP = {
    "Qwen2.5 VL 32B (Free)": "qwen/qwen2.5-vl-32b-instruct",
    "Qwen2.5 VL 72B (Free)": "qwen/qwen2.5-vl-72b-instruct",
    "Mistral 3.2 Small 24B (Free)": "mistralai/mistral-small-3.2-24b-instruct",
    "Gemma 3 12B IT (Free)": "google/gemma-3-12b-it",
    "Gemma 3 27B IT (Free)": "google/gemma-3-27b-it",
    "Gemini 2.5 Flash Lite": "google/gemini-2.5-flash-lite",
    "GPT-4.1 Mini": "openai/gpt-4.1-mini",
}

def crear_tooltip_label(label, text):
    tooltip = None
    def on_enter(event):
        nonlocal tooltip
        if tooltip:
            tooltip.destroy()
        x = label.winfo_rootx() + 20
        y = label.winfo_rooty() + label.winfo_height() + 5
        tooltip = tk.Toplevel(label)
        tooltip.wm_overrideredirect(True)
        tooltip.geometry(f"+{x}+{y}")
        label_tip = tk.Label(
            tooltip,
            text=text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Helvetica", 9),
            anchor="w",  # Justifica a la izquierda
            justify="left"  # Justifica a la izquierda
        )
        label_tip.pack()
    def on_leave(event):
        nonlocal tooltip
        if tooltip:
            tooltip.destroy()
            tooltip = None
    label.bind("<Enter>", on_enter)
    label.bind("<Leave>", on_leave)

class RecorteApp:
    def __init__(self, master):
        self.master = master
        master.title("Herramienta de Extracción")
        master.geometry("400x400")
        master.resizable(False, False)

        self.prompt_excel = """Convierte esta imagen a un archivo Excel respetando al máximo la apariencia visual original.
No reorganices, no reinterpretes ni parafrasees ningún texto.
Si algo no se puede leer claramente, coloca la palabra "ilegible" en su celda.
Aunque no haya una estructura clara de columnas y filas, haz que el Excel se vea visualmente igual que la imagen, con los textos en sus posiciones relativas originales (alineaciones, espaciados, secciones separadas, etc.).
No corrijas errores tipográficos ni completes nada que no esté explícitamente en la imagen.
Sé lo más fiel posible al diseño, como si fuera una reconstrucción visual exacta."""
        self.prompt_docs = """Extrae todo el texto legible de la imagen y respétalo tal cual aparece, sin parafrasear ni corregir errores.
Si hay partes ilegibles, indícalo con la palabra "ilegible".
No incluyas ningún texto adicional fuera del contenido extraído.
El resultado debe estar listo para copiar y pegar en un documento de texto."""
        self.prompt_text = self.prompt_excel  # Inicializa con Excel
        self.auto_process_post_capture = False  # Por defecto desactivado
        
        # Variables para el seguimiento de uso de API
        self.api_usage = 0
        self.api_limit = None
        self.is_free_tier = True
        self.capturas_realizadas = 0  # Contador de capturas para auto-actualizar

        main_frame = Frame(master, padx=30, pady=20, bg="#f7f7f7")  # aumenta separación con bordes
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=0)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)
        main_frame.grid_columnconfigure(3, weight=1)

        # Modo
        lbl_modo = Label(main_frame, text="Modo:", bg="#f7f7f7", anchor="w", justify="left")
        lbl_modo.grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.mode_var = StringVar(value="Excel")
        self.mode_menu = ttk.Combobox(main_frame, textvariable=self.mode_var, values=["Excel", "Docs"], state="readonly", width=20)
        self.mode_menu.grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 10), padx=(20,0))
        self.mode_menu.bind("<<ComboboxSelected>>", self.check_mode_selection)
        self.mode_menu.bind("<Enter>", lambda e: self.mode_menu.config(cursor="hand2"))
        self.mode_menu.bind("<Leave>", lambda e: self.mode_menu.config(cursor="arrow"))
        crear_tooltip_label(lbl_modo, "Selecciona el tipo de archivo que quieres generar. 'Excel' crea una tabla editable. 'Docs' (no disponible) genera un documento de texto.")

        # Proveedor IA
        lbl_prov = Label(main_frame, text="Proveedor IA:", bg="#f7f7f7", anchor="w", justify="left")
        lbl_prov.grid(row=1, column=0, sticky="w", pady=(0, 10))
        self.provider_var = StringVar(value=DEFAULT_MODEL)
        self.provider_menu = ttk.Combobox(main_frame, textvariable=self.provider_var, values=list(MODEL_MAP.keys()), state="readonly", width=20)
        self.provider_menu.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(0, 10), padx=(20,0))
        self.provider_menu.bind("<Enter>", lambda e: self.provider_menu.config(cursor="hand2"))
        self.provider_menu.bind("<Leave>", lambda e: self.provider_menu.config(cursor="arrow"))
        crear_tooltip_label(lbl_prov, "Los modelos están organizados de más barato (arriba) a más caro (abajo). El costo depende del modelo seleccionado.")

        # Dimensiones
        lbl_dim = Label(main_frame, text="Dimensiones:", bg="#f7f7f7", anchor="w", justify="left")
        self.lbl_dim = lbl_dim  # Guarda referencia para ocultar
        lbl_dim.grid(row=2, column=0, sticky="w", pady=(0, 10))
        self.dimension_var = StringVar(value="Automático")
        self.dimension_menu = ttk.Combobox(main_frame, textvariable=self.dimension_var, values=["Automático", "Manual"], state="readonly", width=20)
        self.dimension_menu.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(0, 10), padx=(20,0))
        self.dimension_menu.bind("<Enter>", lambda e: self.dimension_menu.config(cursor="hand2"))
        self.dimension_menu.bind("<Leave>", lambda e: self.dimension_menu.config(cursor="arrow"))
        crear_tooltip_label(lbl_dim, "Automático: La IA detecta filas y columnas.\nManual: Puedes definir el número exacto de columnas y filas.")

        vcmd = (master.register(self._validate_numeric), "%P")

        # Sección columnas/filas (labels + inputs en un frame)
        self.dim_frame = Frame(main_frame, bg="#f7f7f7")
        self.dim_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        lbl_cols = Label(self.dim_frame, text="N° Columnas:", bg="#f7f7f7", anchor="w", justify="left")
        lbl_cols.grid(row=0, column=0, sticky="w")
        self.cols_entry = Entry(self.dim_frame, width=10, bg="white", relief="solid", borderwidth=1, validate="key", validatecommand=vcmd)
        self.cols_entry.grid(row=0, column=1, sticky="w")
        crear_tooltip_label(lbl_cols, "Número de columnas que tendrá la tabla.")

        lbl_rows = Label(self.dim_frame, text="N° Filas:", bg="#f7f7f7", anchor="w", justify="left")
        lbl_rows.grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.rows_entry = Entry(self.dim_frame, width=10, bg="white", relief="solid", borderwidth=1, validate="key", validatecommand=vcmd)
        self.rows_entry.grid(row=0, column=3, sticky="w")
        crear_tooltip_label(lbl_rows, "Número de filas que tendrá la tabla.")

        self.dimension_var.trace_add("write", self.toggle_dimension_inputs)
        # Asegura que la sección de dimensiones esté correctamente oculta/visible al iniciar
        self.toggle_dimension_inputs()

        prompt_button = Button(main_frame, text="Editar Prompt", command=self.abrir_ventana_prompt, bg="#f7f7f7", fg="black", font=("Helvetica", 10, "bold"), relief="raised", borderwidth=2, cursor="hand2")
        prompt_button.grid(row=4, column=0, columnspan=4, sticky="ew", pady=10)
        prompt_button.bind("<Enter>", lambda e: prompt_button.config(cursor="hand2"))
        prompt_button.bind("<Leave>", lambda e: prompt_button.config(cursor="arrow"))
        crear_tooltip_label(prompt_button, "Edita el prompt que se enviará a la IA.")

        self.snip_button = Button(main_frame, text="Recortar y Procesar", command=self.crear_ventana_recorte, bg="#4CAF50", fg="white", font=("Helvetica", 10, "bold"), relief="raised", borderwidth=2, cursor="hand2")
        self.snip_button.grid(row=5, column=0, columnspan=4, sticky="ew", ipady=5)
        self.snip_button.bind("<Enter>", lambda e: self.snip_button.config(cursor="hand2"))
        self.snip_button.bind("<Leave>", lambda e: self.snip_button.config(cursor="arrow"))
        crear_tooltip_label(self.snip_button, "Haz clic para seleccionar el área de la pantalla a procesar.")

        self.auto_var = tk.BooleanVar(value=False)  # Por defecto desactivado
        auto_check = tk.Checkbutton(main_frame, text="Procesamiento automático post captura", variable=self.auto_var, command=self.actualizar_auto_config, bg="#f7f7f7", font=("Helvetica", 10), cursor="hand2")
        auto_check.grid(row=6, column=0, columnspan=4, sticky="w", pady=(10, 0))
        auto_check.bind("<Enter>", lambda e: auto_check.config(cursor="hand2"))
        auto_check.bind("<Leave>", lambda e: auto_check.config(cursor="arrow"))
        crear_tooltip_label(auto_check, "Activado: Tras tomar la captura se procesará automáticamente.\nDesactivado: Tras tomar la captura se pedirá confirmación antes de procesar la imagen.")
        
        # Barra de uso de API
        self.crear_barra_uso_api(main_frame)
        
        # Cargar datos de uso inicial
        self.actualizar_uso_api()

    def crear_barra_uso_api(self, parent):
        """Crea la barra de uso de API en la interfaz"""
        # Frame para la barra de uso
        self.uso_frame = Frame(parent, bg="#f7f7f7")
        self.uso_frame.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        
        # Label de créditos con emoji
        self.lbl_creditos = Label(self.uso_frame, text="💰 API:", bg="#f7f7f7", font=("Helvetica", 9))
        self.lbl_creditos.grid(row=0, column=0, sticky="w")
        
        # Barra de progreso
        self.progress_bar = ttk.Progressbar(self.uso_frame, length=200, mode='determinate')
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=(10, 10))
        
        # Label de información de uso
        self.lbl_uso_info = Label(self.uso_frame, text="Cargando...", bg="#f7f7f7", font=("Helvetica", 8), fg="#666")
        self.lbl_uso_info.grid(row=0, column=2, sticky="e")
        
        # Botón de actualizar
        self.btn_actualizar = Button(self.uso_frame, text="↻", command=self.actualizar_uso_api, 
                                   bg="#e0e0e0", fg="black", font=("Helvetica", 8), 
                                   width=3, height=1, cursor="hand2")
        self.btn_actualizar.grid(row=0, column=3, sticky="e", padx=(5, 0))
        
        # Configurar expansión de columnas
        self.uso_frame.grid_columnconfigure(1, weight=1)
        
        # Tooltip para la barra de uso
        crear_tooltip_label(self.lbl_creditos, "Muestra el uso actual de créditos de la API de OpenRouter.\nVerde: Uso bajo, Amarillo: Uso medio, Rojo: Uso alto")
        crear_tooltip_label(self.btn_actualizar, "Actualizar información de uso de API")

    def obtener_uso_api(self):
        """Obtiene la información de uso de la API de OpenRouter"""
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/key",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    self.api_usage = data['data'].get('usage', 0)
                    self.api_limit = data['data'].get('limit')
                    self.is_free_tier = data['data'].get('is_free_tier', True)
                    return True
            else:
                print(f"Error al obtener uso de API: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión al obtener uso de API: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado al obtener uso de API: {e}")
            return False

    def actualizar_uso_api(self):
        """Actualiza la información de uso de API en un hilo separado"""
        def _actualizar():
            if self.obtener_uso_api():
                # Actualizar UI en el hilo principal
                self.master.after(0, self.actualizar_ui_uso)
            else:
                self.master.after(0, self.mostrar_error_uso)
        
        # Ejecutar en hilo separado para no bloquear la UI
        threading.Thread(target=_actualizar, daemon=True).start()

    def actualizar_ui_uso(self):
        """Actualiza la interfaz con la información de uso de API"""
        if self.api_limit is not None and self.api_limit > 0:
            # Calcular porcentaje usado
            porcentaje_usado = (self.api_usage / self.api_limit) * 100
            
            # Actualizar barra de progreso
            self.progress_bar['value'] = porcentaje_usado
            
            # Cambiar color según el uso
            if porcentaje_usado < 50:
                color = "green"
            elif porcentaje_usado < 80:
                color = "orange"
            else:
                color = "red"
            
            # Formato compacto: usado/total
            self.lbl_uso_info.config(text=f"{self.api_usage:.2f}/{self.api_limit:.0f}$ usados", fg=color)
            
        else:
            # Límite ilimitado o no disponible
            self.progress_bar['value'] = 0
            if self.is_free_tier:
                self.lbl_uso_info.config(text=f"Gratis: {self.api_usage:.2f}$ usados", fg="blue")
            else:
                self.lbl_uso_info.config(text=f"Ilimitado: {self.api_usage:.2f}$ usados", fg="green")

    def mostrar_error_uso(self):
        """Muestra error cuando no se puede obtener información de uso"""
        self.progress_bar['value'] = 0
        self.lbl_uso_info.config(text="Error al obtener datos de uso", fg="red")

    def toggle_dimension_inputs(self, *args):
        # Oculta label, menú y frame de dimensiones si el modo es Docs
        if self.mode_var.get() == "Docs":
            self.lbl_dim.grid_remove()
            self.dimension_menu.grid_remove()
            self.dim_frame.grid_remove()
        else:
            self.lbl_dim.grid()
            self.dimension_menu.grid()
            visible = self.dimension_var.get() == "Manual"
            if visible:
                self.dim_frame.grid()
            else:
                self.dim_frame.grid_remove()

    def abrir_ventana_prompt(self):
        prompt_window = Toplevel(self.master)
        prompt_window.title("Editor de Prompt")
        prompt_window.geometry("500x350")
        text_widget = Text(prompt_window, wrap="word", padx=10, pady=10, font=("Helvetica", 10))
        text_widget.pack(fill="both", expand=True)
        # Muestra el prompt según el modo actual
        if self.mode_var.get() == "Excel":
            text_widget.insert("1.0", self.prompt_excel)
        else:
            text_widget.insert("1.0", self.prompt_docs)
        btn_guardar = Button(prompt_window, text="Guardar", command=lambda: self.set_prompt_and_close(text_widget, prompt_window), bg="#4CAF50", fg="white", cursor="hand2")
        btn_guardar.pack(pady=10)
        btn_guardar.bind("<Enter>", lambda e: btn_guardar.config(cursor="hand2"))
        btn_guardar.bind("<Leave>", lambda e: btn_guardar.config(cursor="arrow"))

    def set_prompt_and_close(self, widget, window):
        texto = widget.get("1.0", "end-1c")
        # Guarda el prompt en el modo correspondiente
        if self.mode_var.get() == "Excel":
            self.prompt_excel = texto
            self.prompt_text = self.prompt_excel
        else:
            self.prompt_docs = texto
            self.prompt_text = self.prompt_docs
        window.destroy()

    def crear_ventana_recorte(self):
        self.master.withdraw()
        self.master.after(300, self.iniciar_captura)

    def iniciar_captura(self):
        try:
            self.original_screenshot = pyscreeze.screenshot()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo capturar la pantalla: {e}")
            self.master.deiconify()
            return

        enhancer = ImageEnhance.Brightness(self.original_screenshot)
        darkened = enhancer.enhance(0.8)
        self.darkened_screenshot_tk = ImageTk.PhotoImage(darkened)

        self.snip_window = Toplevel(self.master)
        self.snip_window.attributes("-fullscreen", True)
        self.snip_window.attributes("-topmost", True)

        self.canvas = Canvas(self.snip_window, cursor="cross", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.darkened_screenshot_tk, anchor="nw")

        self.selection_image_id = self.canvas.create_image(0, 0, anchor="nw")
        self.selection_rect_id = self.canvas.create_rectangle(0, 0, 0, 0, outline="red", width=2)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.snip_window.bind("<Escape>", self.cancelar_recorte)  # <-- corregido nombre del método

    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.selection_rect_id, self.start_x, self.start_y, self.start_x, self.start_y)

    def on_mouse_drag(self, event):
        x1, y1 = min(self.start_x, self.canvas.canvasx(event.x)), min(self.start_y, self.canvas.canvasy(event.y))
        x2, y2 = max(self.start_x, self.canvas.canvasx(event.x)), max(self.start_y, self.canvas.canvasy(event.y))
        if x1 == x2 or y1 == y2:
            return
        self.canvas.coords(self.selection_rect_id, x1, y1, x2, y2)
        crop = self.original_screenshot.crop((int(x1), int(y1), int(x2), int(y2)))
        self.revealed_image_tk = ImageTk.PhotoImage(crop)
        self.canvas.itemconfig(self.selection_image_id, image=self.revealed_image_tk)
        self.canvas.coords(self.selection_image_id, x1, y1)
        self.canvas.lift(self.selection_rect_id)

    def on_button_release(self, event):
        if not self.canvas or not self.canvas.winfo_exists():
            return  # Evita error si la ventana fue cerrada

        try:
            x1, y1 = min(self.start_x, self.canvas.canvasx(event.x)), min(self.start_y, self.canvas.canvasy(event.y))
            x2, y2 = max(self.start_x, self.canvas.canvasx(event.x)), max(self.start_y, self.canvas.canvasy(event.y))
        except Exception as e:
            print(f"Error al obtener coordenadas: {e}")
            return

        self.snip_window.destroy()
        self.master.deiconify()
        region = (int(x1), int(y1), int(x2), int(y2))
        screenshot = self.original_screenshot.crop(region)
        self.revealed_image_tk = ImageTk.PhotoImage(screenshot)
        if self.auto_process_post_capture:
            if self.mode_var.get() == "Excel":
                self.procesar_imagen_excel(screenshot)
            elif self.mode_var.get() == "Docs":
                self.procesar_imagen_docs(screenshot)
        else:
            self.confirmar_procesamiento_imagen(screenshot)

    def cancelar_recorte(self, event=None):
        if hasattr(self, 'snip_window') and self.snip_window:
            self.snip_window.destroy()
        self.master.deiconify()
        messagebox.showinfo("Cancelado", "El recorte ha sido cancelado.")

    def confirmar_procesamiento_imagen(self, imagen):
        # Obtén tamaño de la imagen
        img_width, img_height = imagen.size
        # Calcula tamaño mínimo de ventana (imagen + espacio para botones)
        min_width = max(400, img_width + 50)
        min_height = img_height + 110  
        win = Toplevel(self.master)
        win.title("Confirmar procesamiento")
        win.geometry(f"{min_width}x{min_height}")
        win.minsize(min_width, min_height)
        win.resizable(False, False)
        img_tk = ImageTk.PhotoImage(imagen)
        lbl = Label(win, image=img_tk)
        lbl.image = img_tk
        lbl.pack(padx=20, pady=20, expand=True)
        btn_frame = Frame(win)
        btn_frame.pack(pady=(10, 10))
        if self.mode_var.get() == "Excel":
            btn = Button(btn_frame, text="Procesar", command=lambda: (win.destroy(), self.procesar_imagen_excel(imagen)), bg="#4CAF50", fg="white", font=("Helvetica", 10, "bold"), relief="raised", borderwidth=2, cursor="hand2")
        else:
            btn = Button(btn_frame, text="Procesar", command=lambda: (win.destroy(), self.procesar_imagen_docs(imagen)), bg="#4CAF50", fg="white", font=("Helvetica", 10, "bold"), relief="raised", borderwidth=2, cursor="hand2")
        btn.grid(row=0, column=0, padx=(0, 10))
        btn_cancel = Button(btn_frame, text="Cancelar", command=win.destroy, bg="#F44336", fg="white", font=("Helvetica", 10, "bold"), relief="raised", borderwidth=2, cursor="hand2")
        btn_cancel.grid(row=0, column=1)
        win.transient(self.master)
        win.grab_set()
        self.master.wait_window(win)

    def procesar_imagen_excel(self, imagen):
        # Construir el prompt final
        prompt_usuario = self.prompt_excel.strip()
        prompt_formato = """
Responde únicamente en formato TSV (tab-separated values), donde cada fila representa una fila de la tabla y cada columna está separada por un tabulador. No incluyas ningún texto adicional fuera de la tabla. Ejemplo:
Cantidad\tPrecio S/.\tParcial S/.
4.0000\t9.93\t39.72
2.0000\t8.94\t17.88

Si alguna columna o fila no cuadra con lo que percibes en la imagen, puedes dejar celdas vacías; no es obligatorio llenar todas las celdas.
"""
        prompt = prompt_usuario + "\n\n" + prompt_formato

        if self.dimension_var.get() == "Manual":
            cols = self.cols_entry.get()
            rows = self.rows_entry.get()
            if cols.isdigit() and rows.isdigit():
                prompt += f"\n\nInstrucción adicional: La tabla debe tener exactamente {cols} columnas y {rows} filas."
            else:
                messagebox.showwarning("Datos inválidos", "Las dimensiones deben ser números. Se usará modo automático.")

        modelo_id = MODEL_MAP[self.provider_var.get()]
        base64_img = self._imagen_a_base64(imagen)

        payload = {
            "model": modelo_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{base64_img}"}
                    ]
                }
            ]
        }

        # Ventana de resultado con Frame para organizar widgets
        self.result_win = Toplevel(self.master)
        self.result_win.title("Resultado (TSV, listo para copiar y pegar en Excel)")
        self.result_win.geometry("600x400")
        frame = Frame(self.result_win)
        frame.pack(fill="both", expand=True)

        self.result_text = Text(frame, wrap="none", font=("Consolas", 11))
        self.result_text.insert("1.0", "Cargando, por favor espera...")
        self.result_text.config(state="disabled")
        self.result_text.pack(fill="both", expand=True, padx=10, pady=10)

        self.copy_btn = Button(frame, text="Copiar celdas", state="disabled", command=lambda: self.copiar_al_portapapeles(self.result_text.get("1.0", "end-1c")), cursor="hand2")
        self.copy_btn.pack(pady=8)

        self.result_win.transient(self.master)
        self.result_win.grab_set()

        threading.Thread(target=self._peticion_api_thread, args=(payload,), daemon=True).start()

    def _peticion_api_thread(self, payload):
        import json
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}"
                },
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            output = result['choices'][0]['message']['content']
            print("\n--- RESPUESTA ---\n", output, "\n--- FIN ---")
            
            # Incrementar contador de capturas y verificar si necesita actualizar uso
            self.capturas_realizadas += 1
            if self.capturas_realizadas >= CAPTURAS_ANTES_ACTUALIZAR:
                self.capturas_realizadas = 0  # Reiniciar contador
                self.actualizar_uso_api()  # Actualizar uso automáticamente
            
            self.master.after(0, lambda: self._mostrar_tabla_tsv_en_widget(output))
        except Exception as exc:
            error_msg = f"Error: {exc}"
            self.master.after(0, lambda: self._mostrar_tabla_tsv_en_widget(error_msg))

    def _mostrar_tabla_tsv_en_widget(self, output):
        import json
        # Si la respuesta parece ser JSON, convertir a matriz
        try:
            data = json.loads(output)
            max_row = max(item["row"] for item in data)
            max_col = max(item["column"] for item in data)
            table = [["" for _ in range(max_col)] for _ in range(max_row)]
            for item in data:
                table[item["row"]-1][item["column"]-1] = item["text"]
        except Exception:
            # Si ya es TSV, convertir a matriz
            lines = output.strip().splitlines()
            table = [line.split('\t') for line in lines if line.strip()]

        # --- SOLUCIÓN VISUAL ---
        # Asegura que todas las filas tengan el mismo número de columnas
        max_cols = max(len(row) for row in table) if table else 0
        for row in table:
            if len(row) < max_cols:
                row.extend([""] * (max_cols - len(row)))

        # Borra el widget Text si existe
        self.result_text.pack_forget()

        tree_frame = Frame(self.result_win)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        cols = [f"Col{i+1}" for i in range(max_cols)]
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for i, col in enumerate(cols):
            tree.heading(col, text=f"Columna {i+1}")
            tree.column(col, width=120, anchor="center")
        for row in table:
            tree.insert("", "end", values=row)
        tree.pack(fill="both", expand=True)

        tsv = "\n".join(["\t".join(row) for row in table])

        self.copy_btn.config(state="normal", command=lambda: self.copiar_al_portapapeles(tsv))
        self.copy_btn.pack_forget()
        self.copy_btn.pack(pady=(2, 2))
        self.copy_btn.bind("<Enter>", lambda e: self.copy_btn.config(cursor="hand2"))
        self.copy_btn.bind("<Leave>", lambda e: self.copy_btn.config(cursor="arrow"))

    def procesar_imagen_docs(self, imagen):
        # Prompt para extracción de texto (sin formato Excel)
        prompt_usuario = self.prompt_docs.strip()
        prompt_formato = """
Extrae todo el texto legible de la imagen y respétalo tal cual aparece, sin parafrasear ni corregir errores. Si hay partes ilegibles, indícalo con la palabra "ilegible". No incluyas ningún texto adicional fuera del contenido extraído. El resultado debe estar listo para copiar y pegar en un documento de texto.
"""
        prompt = prompt_usuario + "\n\n" + prompt_formato

        modelo_id = MODEL_MAP[self.provider_var.get()]
        base64_img = self._imagen_a_base64(imagen)

        payload = {
            "model": modelo_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{base64_img}"}
                    ]
                }
            ]
        }

        self.result_win = Toplevel(self.master)
        self.result_win.title("Resultado (Texto extraído, listo para copiar)")
        self.result_win.geometry("600x400")
        frame = Frame(self.result_win)
        frame.pack(fill="both", expand=True)

        self.result_text = Text(frame, wrap="word", font=("Consolas", 11))
        self.result_text.insert("1.0", "Cargando, por favor espera...")
        self.result_text.config(state="disabled")
        self.result_text.pack(fill="both", expand=True, padx=10, pady=10)

        self.copy_btn = Button(frame, text="Copiar texto", state="disabled", command=lambda: self.copiar_al_portapapeles(self.result_text.get("1.0", "end-1c")), cursor="hand2")
        self.copy_btn.pack(pady=8)

        self.result_win.transient(self.master)
        self.result_win.grab_set()

        threading.Thread(target=self._peticion_api_thread_docs, args=(payload,), daemon=True).start()

    def _peticion_api_thread_docs(self, payload):
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}"
                },
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            output = result['choices'][0]['message']['content']
            # Elimina delimitadores tipo ```excel``` si aparecen
            output = output.strip()
            if output.startswith("```excel"):
                output = output[len("```excel"):].strip()
            if output.endswith("```"):
                output = output[:-3].strip()
            self.master.after(0, lambda: self._mostrar_texto_en_widget(output))
        except Exception as exc:
            self.master.after(0, lambda: self._mostrar_texto_en_widget(f"Error: {exc}"))

    def _mostrar_texto_en_widget(self, output):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", output.strip())
        self.result_text.config(state="normal")
        self.copy_btn.config(state="normal", command=lambda: self.copiar_al_portapapeles(self.result_text.get("1.0", "end-1c")))
        self.copy_btn.pack_forget()
        self.copy_btn.pack(pady=(2, 2))
        self.copy_btn.bind("<Enter>", lambda e: self.copy_btn.config(cursor="hand2"))
        self.copy_btn.bind("<Leave>", lambda e: self.copy_btn.config(cursor="arrow"))

    def mostrar_imagen_capturada(self, image):
        window = Toplevel(self.master)
        window.title("Imagen Capturada")
        window.image = ImageTk.PhotoImage(image)
        Label(window, image=window.image).pack(padx=10, pady=10)
        Button(window, text="Cerrar", command=window.destroy, cursor="hand2").pack(pady=10)
        window.transient(self.master)
        window.grab_set()
        self.master.wait_window(window)

    def _imagen_a_base64(self, img):
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def copiar_al_portapapeles(self, texto):
        self.master.clipboard_clear()
        self.master.clipboard_append(texto)
        # No muestra mensaje

    def set_prompt(self, widget):
        self.prompt_text = widget.get("1.0", "end-1c")

    def actualizar_auto_config(self):
        self.auto_process_post_capture = self.auto_var.get()

    def check_mode_selection(self, event=None):
        # Oculta dimensiones si selecciona Docs, muestra si Excel
        self.toggle_dimension_inputs()
        # Cambia el prompt activo al cambiar de modo
        if self.mode_var.get() == "Excel":
            self.prompt_text = self.prompt_excel
        else:
            self.prompt_text = self.prompt_docs

    def _validate_numeric(self, value):
        return value.isdigit() or value == ""

def main():
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
        messagebox.showerror(
            "API Key no configurada",
            "No se ha encontrado una API Key válida para OpenRouter.\n\n"
            "Verifica que esté definida en el archivo .env como:\n\n"
            "OPENROUTER_API_KEY=tu_clave_aqui"
        )
        return  # Detiene el programa si no hay API key

    try:
        root = tk.Tk()
        # Cambia el icono de la ventana principal
        root.iconbitmap(r"e:\Codigo\python\experimentos\icono.ico")
        app = RecorteApp(root)
        root.mainloop()
    except Exception as e:
        import traceback
        messagebox.showerror("Error crítico", f"{e}\n\n{traceback.format_exc()}")

if __name__ == "__main__":
    
    main()
