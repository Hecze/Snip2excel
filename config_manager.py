import os
import json
import base64
import requests
from cryptography.fernet import Fernet
from tkinter import messagebox, simpledialog
import tkinter as tk


ENCRYPTION_KEY = "_PjqHMjuxoN8xivCT-23aaZn85UdflOY0sXvued8SKE="
# Configuración por defecto
DEFAULT_CONFIG = {
    "OPENROUTER_API_KEY": "",
    "selected_model": "Qwen2.5 VL 72B (Free)",
    "output_mode": "Excel",
    "auto_process_enabled": False,
    "prompt_excel": """Convierte esta imagen a un archivo Excel respetando al máximo la apariencia visual original.
No reorganices, no reinterpretes ni parafrasees ningún texto.
Si algo no se puede leer claramente, coloca la palabra "ilegible" en su celda.
Aunque no haya una estructura clara de columnas y filas, haz que el Excel se vea visualmente igual que la imagen, con los textos en sus posiciones relativas originales (alineaciones, espaciados, secciones separadas, etc.).
No corrijas errores tipográficos ni completes nada que no esté explícitamente en la imagen.
Sé lo más fiel posible al diseño, como si fuera una reconstrucción visual exacta.""",
    "prompt_docs": """Extrae todo el texto legible de la imagen y respétalo tal cual aparece, sin parafrasear ni corregir errores.
Si hay partes ilegibles, indícalo con la palabra "ilegible".
No incluyas ningún texto adicional fuera del contenido extraído.
El resultado debe estar listo para copiar y pegar en un documento de texto."""
}

def get_config_dir():
    """Obtiene el directorio de configuración según el sistema operativo"""
    if os.name == 'nt':  # Windows
        config_dir = os.path.join(os.getenv('APPDATA'), 'Snip2Excel')
    else:  # Linux/macOS
        config_dir = os.path.expanduser('~/.config/Snip2Excel')
    
    # Crear el directorio si no existe
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def get_config_file():
    """Obtiene la ruta completa del archivo de configuración"""
    return os.path.join(get_config_dir(), 'config.json')

def encrypt_api_key(api_key):
    """Encripta la API key usando Fernet"""
    if not api_key:
        return ""
    
    # Convertir la clave de string a bytes y crear un Fernet
    key_bytes = base64.urlsafe_b64encode(ENCRYPTION_KEY.encode()[:32].ljust(32, b'0'))
    fernet = Fernet(key_bytes)
    
    # Encriptar la API key
    encrypted = fernet.encrypt(api_key.encode())
    return base64.b64encode(encrypted).decode()

def decrypt_api_key(encrypted_api_key):
    """Desencripta la API key"""
    if not encrypted_api_key:
        return ""
    
    try:
        # Convertir la clave de string a bytes y crear un Fernet
        key_bytes = base64.urlsafe_b64encode(ENCRYPTION_KEY.encode()[:32].ljust(32, b'0'))
        fernet = Fernet(key_bytes)
        
        # Desencriptar la API key
        encrypted_bytes = base64.b64decode(encrypted_api_key.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        print(f"Error al desencriptar API key: {e}")
        return ""

def load_config():
    """Carga la configuración desde el archivo JSON"""
    config_file = get_config_file()
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Desencriptar la API key si existe
            if 'OPENROUTER_API_KEY' in config:
                config['OPENROUTER_API_KEY'] = decrypt_api_key(config['OPENROUTER_API_KEY'])
                
            return config
        else:
            # Si no existe, crear con valores por defecto
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
            
    except Exception as e:
        print(f"Error al cargar configuración: {e}")
        # En caso de error, devolver configuración por defecto
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Guarda la configuración en el archivo JSON"""
    config_file = get_config_file()
    
    try:
        # Crear una copia para no modificar el original
        config_to_save = config.copy()
        
        # Encriptar la API key antes de guardar
        if 'OPENROUTER_API_KEY' in config_to_save:
            config_to_save['OPENROUTER_API_KEY'] = encrypt_api_key(config_to_save['OPENROUTER_API_KEY'])
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"Error al guardar configuración: {e}")
        messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")

def update_config(key, value):
    """Actualiza un valor específico en la configuración"""
    config = load_config()
    config[key] = value
    save_config(config)

def get_api_key():
    """Obtiene la API key de la configuración"""
    config = load_config()
    return config.get('OPENROUTER_API_KEY', '')

def set_api_key(api_key):
    """Establece la API key en la configuración"""
    update_config('OPENROUTER_API_KEY', api_key)

def ask_for_api_key(parent=None):
    """Muestra un diálogo para pedir la API key al usuario"""
    temp_root = None
    if parent is None:
        # Crear una ventana temporal si no se proporciona un parent
        temp_root = tk.Tk()
        temp_root.withdraw()  # Ocultar la ventana temporal
        parent = temp_root
    
    # Crear ventana personalizada
    dialog = tk.Toplevel(parent)
    dialog.title("API Key requerida")
    dialog.geometry("400x300")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    
    # Centrar la ventana
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
    y = (dialog.winfo_screenheight() // 2) - (300 // 2)
    dialog.geometry(f"400x300+{x}+{y}")
    
    # Frame principal
    main_frame = tk.Frame(dialog, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)
    
    # Título
    title_label = tk.Label(main_frame, text="Por favor ingresa tu API Key de OpenRouter:", font=("Helvetica", 10, "bold"))
    title_label.pack(pady=(0, 15))
    
    # Instrucciones
    step1_frame = tk.Frame(main_frame)
    step1_frame.pack(fill="x", pady=(0, 8))
    
    step1 = tk.Label(step1_frame, text="1. Ve a ", font=("Helvetica", 9))
    step1.pack(side="left")
    
    # URL clickeable
    url_label = tk.Label(step1_frame, text="https://openrouter.ai/settings/keys", 
                        font=("Helvetica", 9), fg="#0066cc", cursor="hand2")
    url_label.pack(side="left")
    
    def open_url(event):
        import webbrowser
        webbrowser.open("https://openrouter.ai/settings/keys")
    
    url_label.bind("<Button-1>", open_url)
    url_label.bind("<Enter>", lambda e: url_label.config(fg="#003366"))
    url_label.bind("<Leave>", lambda e: url_label.config(fg="#0066cc"))
    
    # Punto 2
    step2 = tk.Label(main_frame, text="2. Crea una nueva API key", font=("Helvetica", 9))
    step2.pack(anchor="w", pady=(0, 8))
    
    # Punto 3
    step3 = tk.Label(main_frame, text="3. Copia y pega la clave aquí:", font=("Helvetica", 9))
    step3.pack(anchor="w", pady=(0, 10))
    
    # Campo de entrada
    entry_var = tk.StringVar()
    entry = tk.Entry(main_frame, textvariable=entry_var, font=("Helvetica", 10), width=40)
    entry.pack(pady=(0, 15))
    entry.focus()
    
    # Variables para el resultado
    result = [None]
    
    def on_ok():
        result[0] = entry_var.get()
        dialog.destroy()
    
    def on_cancel():
        result[0] = None
        dialog.destroy()
    
    # Botones
    button_frame = tk.Frame(main_frame)
    button_frame.pack()
    
    ok_button = tk.Button(button_frame, text="OK", command=on_ok, bg="#4CAF50", fg="white", 
                         font=("Helvetica", 9, "bold"), width=10, cursor="hand2")
    ok_button.pack(side="left", padx=(0, 10))
    
    cancel_button = tk.Button(button_frame, text="Cancelar", command=on_cancel, 
                             bg="#f44336", fg="white", font=("Helvetica", 9), width=10, cursor="hand2")
    cancel_button.pack(side="left")
    
    # Bind Enter y Escape
    entry.bind("<Return>", lambda e: on_ok())
    dialog.bind("<Escape>", lambda e: on_cancel())
    
    # Esperar a que se cierre la ventana
    dialog.wait_window()
    
    if temp_root is not None:
        temp_root.destroy()
    
    return result[0]

def validate_api_key(api_key):
    """Valida que la API key sea correcta haciendo una petición al endpoint de uso"""
    if not api_key or not api_key.strip():
        return False
    
    api_key = api_key.strip()
    
    # Verificación básica: debe tener al menos 20 caracteres
    if len(api_key) < 20:
        return False
    
    # Debe empezar con 'sk-' (formato estándar de OpenRouter)
    if not api_key.startswith('sk-'):
        return False
    
    # Validación real haciendo una petición al endpoint de uso
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/key",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            timeout=10
        )
        
        # Si la respuesta es 200, la API key es válida
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión al validar API key: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado al validar API key: {e}")
        return False 