# 📊 Análisis de Sentimientos - MercadoLibre Ecuador

Proyecto de análisis de sentimientos de reseñas de productos de MercadoLibre Ecuador usando técnicas de NLP (Procesamiento de Lenguaje Natural).

## 🚀 Características

- **Web Scraping**: Extracción de productos y reseñas de MercadoLibre Ecuador
- **Análisis de Sentimientos**: Clasificación automática usando modelo `pysentimiento/robertuito-sentiment-analysis`
- **Dashboard Interactivo**: Visualización de resultados con Streamlit
- **Base de Datos**: Almacenamiento en MongoDB Atlas

## 📦 Categorías Analizadas

- Audífonos
- Laptops
- Televisores

## 🛠️ Tecnologías

- **Python 3.8+**
- **BeautifulSoup4**: Web scraping
- **Selenium**: Scraping dinámico de reseñas
- **Transformers (HuggingFace)**: Análisis de sentimientos
- **MongoDB**: Base de datos NoSQL
- **Streamlit**: Dashboard interactivo
- **Pandas, Matplotlib, WordCloud**: Análisis y visualización

## 📋 Requisitos

```bash
pip install -r requirements.txt
```

## ⚙️ Configuración

1. Crear archivo `.env` en la raíz del proyecto:

```env

```

2. Reemplazar con tu URI de MongoDB Atlas

## 🚀 Uso

### 1. Scraping de Productos

```bash
python scrape_products.py
```

Modo interactivo para extraer productos por categoría.

### 2. Scraping de Reseñas

```bash
python scrape_reviews.py
```

Extrae reseñas de los productos guardados usando Selenium.

### 3. Análisis de Sentimientos

```bash
python enrich_sentiment.py
```

Clasifica las reseñas en: positivo, neutral, negativo.

### 4. Dashboard

```bash
streamlit run dashboard.py
```

Visualiza los resultados en un dashboard interactivo.

## 📊 Estructura del Proyecto

```
ml_sentiment/
│
├── scrape_products.py      # Scraping de listados de productos
├── scrape_reviews.py        # Scraping de reseñas con Selenium
├── enrich_sentiment.py      # Análisis de sentimientos
├── dashboard.py             # Dashboard de visualización
├── diagnostico_html.py      # Herramienta de diagnóstico
│
├── .env                     # Variables de entorno (NO SUBIR)
├── .gitignore              # Archivos ignorados
├── requirements.txt         # Dependencias
└── README.md               # Este archivo
```

## 📈 Resultados

El dashboard muestra:

- ✅ Distribución de sentimientos por categoría
- ✅ Análisis por producto individual
- ✅ Nubes de palabras positivas/negativas
- ✅ Top 10 palabras más frecuentes
- ✅ Exportación de datos a CSV

## 🤖 Modelo de IA

**Modelo**: `pysentimiento/robertuito-sentiment-analysis`
- Entrenado específicamente para español
- Clasificación: POS / NEU / NEG
- Basado en RoBERTa

## 📝 Licencia

MIT License

## 👤 Autor

[Tu Nombre]

## 🔗 Links

- [MercadoLibre Ecuador](https://www.mercadolibre.com.ec/)
- [Pysentimiento](https://github.com/pysentimiento/pysentimiento)
- [Streamlit](https://streamlit.io/)
```