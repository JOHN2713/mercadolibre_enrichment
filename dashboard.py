import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
import streamlit as st
import altair as alt
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re


# Config MongoDB

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError("No se encontró MONGODB_URI en el .env")

client = MongoClient(MONGODB_URI)
db = client["ml_reviews"]
reviews_col = db["raw_reviews"]


# Funciones auxiliares

@st.cache_data
def cargar_datos():
    """
    Carga reseñas enriquecidas desde MongoDB a un DataFrame.
    Solo toma las que ya tienen sentimiento calculado.
    """
    cursor = reviews_col.find(
        {"sentiment_label": {"$exists": True}},
        {"_id": 1, "categoria": 1, "titulo_producto": 1, 
         "reseña_texto": 1, "sentiment_label": 1, "sentiment_stars": 1}
    )

    data = list(cursor)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    return df


def calcular_metricas_generales(df: pd.DataFrame):
    total = len(df)
    if total == 0:
        return total, 0, 0, 0

    conteo_labels = df["sentiment_label"].value_counts()
    pos = conteo_labels.get("positivo", 0)
    neu = conteo_labels.get("neutral", 0)
    neg = conteo_labels.get("negativo", 0)

    pct_pos = round(pos * 100 / total, 1)
    pct_neu = round(neu * 100 / total, 1)
    pct_neg = round(neg * 100 / total, 1)

    return total, pct_pos, pct_neu, pct_neg

# STOPWORDS AMPLIADAS - Incluye palabras contextuales y no significativas
STOPWORDS_ES = {
    # Artículos, preposiciones, conectores
    "el","la","los","las","de","del","y","a","en","un","una","que","se","por",
    "con","para","es","son","lo","al","como","más","mas","ya","me","mi","su","sus",
    "este","esta","esto","esa","ese","eso","tu","te","cuando","todo","todos","todas",
    "hay","aqui","ahí","ahi","pues","pero","si","no","muy","bien","mal","super",
    "tan","solo","solo","sólo","fue","sido","estar","tener","hacer","vez","veces",
    "puede","pueden","debe","deben","algún","alguna","otros","otras","cada","mismo",
    "misma","quiero","quiere","dar","dio","dió","hecho","hacer","está","horas",
    
    # Palabras genéricas de opinión que NO aportan insight
    "reseña","opinion","opinión","review","comentario","calificacion","calificación",
    "estrellas","estrella","puntos","valoracion","valoración","evaluacion","evaluación",
    "bueno","buena","regular","normal","común","típico","tipico",
    
    # Contexto de compra/producto (demasiado genérico)
    "producto","productos","artículo","articulo","artículos","articulos","item",
    "compra","compre","compré","comprado","comprar","compras",
    "mercado","libre","mercadolibre","tienda","vendedor","vendedora",
    "precio","precios","costo","costos","vale","pagar","pagué","pague","pago",
    "envio","envío","envios","envíos","entrega","llegó","llego","llegada",
    "pedido","pedidos","orden","ordenes","órdenes",
    "cliente","clientes","servicio","atención","atencion",
    
    # Palabras sobre uso/experiencia (muy genéricas)
    "uso","usar","usada","utilizar","utilizando","utilizó","utilizo",
    "funcionamiento","función","funciona","funcionan","funcionar",
    
    # Adjetivos vagos
    "útil","util","útiles","utiles","opciones","opción","opcion","expectativas",
    "características","caracteristicas","materiales","material",
    "tamaño","tamano","color","colores","modelo","modelos", "único","opiniones",
    
    # Verbos comunes poco informativos
    "recomiendo","recomendar","recomendada","recomendable",
    "cumple","cumplir","esperar","esperaba","esperado","esperando","geniales","mejor",
    
    # Temporalidad genérica
    "dias","día","dias","meses","mes","año","anos","tiempo","veces","primera","primer",
    
    # Meses
    "ene","feb","mar","abr","may","jun","jul","ago","sept","oct","nov","dic",
    "enero","febrero","marzo","abril","mayo","junio","julio","agosto",
    "septiembre","octubre","noviembre","diciembre",
    
    # Números y variaciones
    "uno","dos","tres","cuatro","cinco","seis","siete","ocho","nueve","diez",
}

def limpiar_texto(texto: str) -> str:
    """
    Limpia el texto eliminando stopwords y palabras poco informativas.
    Mantiene solo palabras relevantes para análisis de sentimiento.
    """
    if not texto:
        return ""
    
    texto = str(texto).lower()
    
    # Eliminar puntuación pero mantener espacios
    texto = re.sub(r'[^\w\s]', ' ', texto)
    
    # Eliminar números
    texto = re.sub(r'\d+', '', texto)
    
    palabras = texto.split()
    
    # Filtrar palabras:
    # 1. No en stopwords
    # 2. Longitud >= 4 (más estricto)
    # 3. No sean solo vocales repetidas (aaaa, eee, etc)
    palabras_filtradas = [
        p for p in palabras 
        if (p not in STOPWORDS_ES and 
            len(p) >= 4 and
            len(set(p)) > 2)  # Al menos 3 caracteres diferentes
    ]
    
    return " ".join(palabras_filtradas)


st.set_page_config(
    page_title="Sentimiento de productos - Mercado Libre",
    layout="wide"
)

st.title("Dashboard de Sentimiento de Productos (Mercado Libre)")
st.caption("Análisis de opiniones de clientes usando PLN")

df = cargar_datos()

if df.empty:
    st.warning("No hay reseñas enriquecidas en la base de datos. "
               "Asegúrate de haber ejecutado el script enrich_sentiment.py.")
    st.stop()

# ----- Filtro por categoría -----
st.sidebar.header("Filtros")

if "categoria" in df.columns:
    categorias_unicas = df["categoria"].dropna().unique().tolist()
    categorias_unicas.sort()
    categorias_opciones = ["Todas"] + categorias_unicas

    categoria_seleccionada = st.sidebar.selectbox(
        "Categoría",
        options=categorias_opciones,
        index=0
    )

    if categoria_seleccionada == "Todas":
        df_filtrado = df.copy()
    else:
        df_filtrado = df[df["categoria"] == categoria_seleccionada].copy()
else:
    st.sidebar.info("No hay campo 'categoria' en los datos.")
    df_filtrado = df.copy()


# ----- Métricas generales -----
st.subheader("Resumen general")

total, pct_pos, pct_neu, pct_neg = calcular_metricas_generales(df_filtrado)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total reseñas", total)
col2.metric(" Positivas (%)", pct_pos)
col3.metric(" Neutras (%)", pct_neu)
col4.metric(" Negativas (%)", pct_neg)

st.markdown("---")

# ----- Distribución por categoría -----
st.subheader("Sentimiento por categoría")

if "categoria" in df_filtrado.columns:
    agrupado = (
        df_filtrado.groupby(["categoria", "sentiment_label"])
                   .size()
                   .reset_index(name="conteo")
    )

    chart = alt.Chart(agrupado).mark_bar().encode(
        x=alt.X("categoria:N", title="Categoría"),
        y=alt.Y("conteo:Q", title="Número de reseñas"),
        color=alt.Color("sentiment_label:N", 
                       title="Sentimiento",
                       scale=alt.Scale(
                           domain=["positivo", "neutral", "negativo"],
                           range=["#2ecc71", "#f39c12", "#e74c3c"]
                       )),
        tooltip=["categoria", "sentiment_label", "conteo"]
    ).properties(
        width=600,
        height=400
    )

    st.altair_chart(chart, width='stretch')
else:
    st.info("Los documentos no tienen campo 'categoria' definido.")

st.markdown("---")

# ----- Análisis por producto -----
st.subheader("Detalle por producto")

if "titulo_producto" in df_filtrado.columns:
    productos_unicos = df_filtrado["titulo_producto"].dropna().unique().tolist()
    productos_unicos.sort()

    producto_seleccionado = st.selectbox(
        "Selecciona un producto",
        options=productos_unicos
    )

    df_prod = df_filtrado[df_filtrado["titulo_producto"] == producto_seleccionado]

    # Métricas por producto
    total_p, pct_pos_p, pct_neu_p, pct_neg_p = calcular_metricas_generales(df_prod)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reseñas del producto", total_p)
    c2.metric(" Positivas (%)", pct_pos_p)
    c3.metric(" Neutras (%)", pct_neu_p)
    c4.metric(" Negativas (%)", pct_neg_p)

    # Tabla de reseñas
    st.write("Reseñas del producto (muestra):")
    st.dataframe(
        df_prod[["reseña_texto", "sentiment_label", "sentiment_stars"]]
          .reset_index(drop=True),
        height=300
    )
else:
    st.info("Los documentos no tienen campo 'titulo_producto' definido.")

st.markdown("---")
st.subheader(" Nube de palabras por sentimiento")
st.caption("Palabras más frecuentes en opiniones positivas vs negativas (filtrado inteligente)")

col_pos, col_neg = st.columns(2)

# ---- Nube de reseñas positivas ----
with col_pos:
    st.markdown("** Reseñas positivas**")
    df_pos = df_filtrado[df_filtrado["sentiment_label"] == "positivo"]
    if not df_pos.empty:
        texto_pos = " ".join(df_pos["reseña_texto"].astype(str).apply(limpiar_texto).tolist())
        if texto_pos.strip():
            wc_pos = WordCloud(
                width=800,
                height=400,
                background_color="white",
                colormap="Greens",
                max_words=30,  # Reducido a 30 palabras más relevantes
                relative_scaling=0.5,
                min_font_size=12,
                prefer_horizontal=0.7
            ).generate(texto_pos)

            fig_pos, ax_pos = plt.subplots(figsize=(10, 5))
            ax_pos.imshow(wc_pos, interpolation="bilinear")
            ax_pos.axis("off")
            st.pyplot(fig_pos)
        else:
            st.info("No hay suficiente texto positivo para generar la nube.")
    else:
        st.info("Aún no hay reseñas positivas.")

# ---- Nube de reseñas negativas ----
with col_neg:
    st.markdown("** Reseñas negativas**")
    df_neg = df_filtrado[df_filtrado["sentiment_label"] == "negativo"]
    if not df_neg.empty:
        texto_neg = " ".join(df_neg["reseña_texto"].astype(str).apply(limpiar_texto).tolist())
        if texto_neg.strip():
            wc_neg = WordCloud(
                width=800,
                height=400,
                background_color="white",
                colormap="Reds",
                max_words=30,  # Reducido a 30 palabras más relevantes
                relative_scaling=0.5,
                min_font_size=12,
                prefer_horizontal=0.7
            ).generate(texto_neg)

            fig_neg, ax_neg = plt.subplots(figsize=(10, 5))
            ax_neg.imshow(wc_neg, interpolation="bilinear")
            ax_neg.axis("off")
            st.pyplot(fig_neg)
        else:
            st.info("No hay suficiente texto negativo para generar la nube.")
    else:
        st.info("Aún no hay reseñas negativas.")

# ----- Análisis adicional -----
st.markdown("---")
st.subheader(" Top palabras por sentimiento")

col_top1, col_top2 = st.columns(2)

with col_top1:
    st.markdown("** Top 10 palabras positivas**")
    if not df_pos.empty:
        texto_pos_limpio = " ".join(df_pos["reseña_texto"].astype(str).apply(limpiar_texto).tolist())
        palabras_pos = texto_pos_limpio.split()
        if palabras_pos:
            from collections import Counter
            top_pos = Counter(palabras_pos).most_common(10)
            df_top_pos = pd.DataFrame(top_pos, columns=["Palabra", "Frecuencia"])
            st.dataframe(df_top_pos, hide_index=True)

with col_top2:
    st.markdown("** Top 10 palabras negativas**")
    if not df_neg.empty:
        texto_neg_limpio = " ".join(df_neg["reseña_texto"].astype(str).apply(limpiar_texto).tolist())
        palabras_neg = texto_neg_limpio.split()
        if palabras_neg:
            from collections import Counter
            top_neg = Counter(palabras_neg).most_common(10)
            df_top_neg = pd.DataFrame(top_neg, columns=["Palabra", "Frecuencia"])
            st.dataframe(df_top_neg, hide_index=True)

# ----- Exportar datos -----
st.markdown("---")
st.subheader(" Exportar datos")

if st.button("Descargar CSV de reseñas filtradas"):
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=" Descargar archivo CSV",
        data=csv,
        file_name="reviews_sentiment.csv",
        mime="text/csv"
    )
