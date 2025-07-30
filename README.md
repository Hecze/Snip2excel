# Herramienta de Extracción de Tablas y Texto desde Imágenes

## 🎯 Objetivo

Desarrollar una aplicación de escritorio sencilla que permita al usuario seleccionar una región de la pantalla (mediante recorte), enviar la imagen a un modelo de IA (LLM) y obtener como resultado una tabla editable (para Excel) o texto (para Docs), facilitando la copia y pegado en aplicaciones ofimáticas.

---

## ✅ Funcionalidades principales

- Recorte de cualquier área de la pantalla y procesamiento con IA.
- Soporte para múltiples proveedores de modelos LLM (OpenAI, Google, Anthropic, xAI) a través de OpenRouter.
- Modo de extracción seleccionable: **Excel** o **Docs**.
- Opción de definir dimensiones de tabla manualmente o de forma automática (solo en modo Excel).
- Resultado editable tipo hoja de cálculo (`Treeview`) o block de notas (`Text`).
- Interfaz visual amigable con tooltips y controles intuitivos.
- Permite editar el prompt enviado al modelo.
- Procesamiento automático tras captura o con confirmación manual.
- Variables de entorno gestionadas mediante `.env`.

---

## ⚙️ Instalación y ejecución

### 1. Clona el repositorio

```bash
git clone https://github.com/tu_usuario/tu_repositorio.git
cd tu_repositorio
```

### 2. Crea el entorno virtual (opcional pero recomendado)

```bash
python -m venv venv
source venv/bin/activate   # En Linux/macOS
venv\Scripts\activate      # En Windows
```

### 3. Instala las dependencias

```bash
pip install -r requirements.txt
```

### 4. Configura tu clave API

Copia el archivo `.env.example` como `.env` y reemplaza con tu API key de [OpenRouter](https://openrouter.ai/):

```bash
cp .env.example .env
```

Abre `.env` y coloca tu clave:

```env
OPENROUTER_API_KEY=tu_api_key_real
```

### 5. Ejecuta la aplicación

```bash
python recorte_simple.py
```

---

## 🛠️ Cómo generar el ejecutable (.exe)

Asegúrate de tener instalado PyInstaller:

```bash
pip install pyinstaller
```

Luego, ejecuta:

```bash
pyinstaller --onefile --windowed --icon=e:\Codigo\python\experimentos\icono.ico --name zoro recorte_simple.py

```

Esto generará un ejecutable en la carpeta `dist/` que puedes usar sin necesidad de tener Python instalado.

---

## 👤 Público objetivo

Esta herramienta está diseñada para:

- Profesionales administrativos que trabajan con reportes escaneados o documentos en imagen que contienen tablas complejas.
- Asistentes de oficina, analistas y personas que copian manualmente datos de imágenes o PDFs sin OCR a Excel o Word.
- Usuarios que usan ChatGPT o LLMs para transformar imágenes en texto o tablas, pero quieren una forma más eficiente y directa.
- Cualquiera que necesite convertir imágenes a contenido ofimático sin complicaciones.

---

## 📂 Estructura del proyecto

```
.
├── recorte_simple.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── icono.ico
```

