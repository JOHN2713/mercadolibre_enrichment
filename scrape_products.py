import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import time

# ------------------------
# Configuración MongoDB
# ------------------------
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError("No se encontró MONGODB_URI en el .env")

client = MongoClient(MONGODB_URI)
db = client["ml_reviews"]
products_col = db["products"]

# ------------------------
# Configuración de listados
# ------------------------
LISTING_CONFIG = {
    "audifonos": {
        "base_url": "https://listado.mercadolibre.com.ec/audifonos",
        "max_pages": 20
    },
    "laptops": {
        "base_url": "https://listado.mercadolibre.com.ec/computacion-notebooks/laptops",
        "max_pages": 20
    },
    "televisores": {
        "base_url": "https://listado.mercadolibre.com.ec/electronica-audio-y-video/televisores/televisores",
        "max_pages": 20
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def scrape_listing(category_name, url, debug_mode=False):
    print(f"\n Scrapeando: {url}")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f" Error: {e}")
        return 0, False

    soup = BeautifulSoup(resp.text, "html.parser")

    # Buscar items
    items = soup.select("li.ui-search-layout__item")
    if not items:
        items = soup.select("div.ui-search-result__wrapper")
    if not items:
        items = soup.select("div.ui-search-result")

    print(f" Encontrados {len(items)} items en la página")

    if not items:
        print(f" No se encontraron items")
        return 0, False

    docs_to_insert = []
    productos_duplicados = 0
    productos_sin_datos = 0

    for idx, item in enumerate(items, 1):
        # NUEVO: Buscar el enlace con clase poly-component__title
        link_tag = item.select_one("a.poly-component__title")
        
        # Fallback a otros selectores si no encuentra
        if not link_tag:
            link_tag = (
                item.select_one("a.ui-search-item__group__element") or
                item.select_one("a.ui-search-link") or
                item.find("a", href=True)
            )
        
        # El título está DENTRO del enlace
        if link_tag:
            title = link_tag.get_text(strip=True)
            product_url = link_tag.get("href", "")
        else:
            productos_sin_datos += 1
            if debug_mode and idx <= 5:
                print(f" Item {idx}: No se encontró enlace")
            continue
        
        # Buscar precio
        price_tag = (
            item.select_one("span.andes-money-amount__fraction") or
            item.select_one("span.price-tag-fraction") or
            item.select_one("span.price-tag-amount")
        )

        price = price_tag.get_text(strip=True) if price_tag else "N/A"

        # Validar y limpiar URL
        if not product_url:
            productos_sin_datos += 1
            continue
        
        # Limpiar URL de tracking (remover todo después de ?)
        if "?" in product_url:
            product_url = product_url.split("?")[0]
            
        if not product_url.startswith("http"):
            product_url = "https://www.mercadolibre.com.ec" + product_url

        # Validar título
        if not title or len(title) < 5:
            productos_sin_datos += 1
            continue

        # Verificar duplicados
        if products_col.find_one({"url_producto": product_url}):
            productos_duplicados += 1
            if debug_mode and idx <= 5:
                print(f" Item {idx}: Duplicado - {title[:40]}...")
            continue

        doc = {
            "categoria": category_name,
            "titulo": title,
            "url_producto": product_url,
            "precio_texto": price,
            "origen": "mercadolibre_listado",
        }
        docs_to_insert.append(doc)
        
        if debug_mode and idx <= 5:
            print(f"    ✓ Item {idx}: NUEVO - {title[:40]}...")

    insertados = 0
    if docs_to_insert:
        result = products_col.insert_many(docs_to_insert)
        insertados = len(result.inserted_ids)
        print(f" Insertados: {insertados} productos nuevos")
    else:
        print(f" No hay productos nuevos")
    
    print(f" {insertados} nuevos | {productos_duplicados} duplicados | {productos_sin_datos} sin datos")
    
    # Retornar si hay más contenido disponible
    hay_mas = len(items) >= 40
    
    return insertados, hay_mas


def scrape_categoria_interactivo(category_name, base_url, max_pages):
    """Scrapea una categoría con control manual de páginas"""
    print(f"\n{'='*80}")
    print(f"CATEGORÍA: {category_name.upper()}")
    print(f"{'='*80}")
    
    page = 0
    total_nuevos = 0
    
    while page < max_pages:
        # Construir URL de la página
        if page == 0:
            page_url = base_url
        else:
            offset = (page * 48) + 1
            page_url = f"{base_url}_Desde_{offset}_NoIndex_True"
        
        print(f"\nPágina {page + 1}/{max_pages}")
        
        # Scrapear la página (debug_mode=True en primeras 2 páginas)
        nuevos, hay_mas = scrape_listing(category_name, page_url, debug_mode=(page < 2))
        total_nuevos += nuevos
        
        # Mostrar estadísticas actuales
        count_actual = products_col.count_documents({"categoria": category_name})
        print(f"\n  Total en BD para {category_name}: {count_actual} productos")
        
        if not hay_mas:
            print(f"\n No hay más páginas disponibles para {category_name}")
            break
        
        # Preguntar si continuar
        print(f"\n  {'─'*76}")
        print(f"  ¿Qué deseas hacer?")
        print(f"    1. Continuar a la siguiente página")
        print(f"    2. Saltar a la siguiente categoría")
        print(f"    3. Terminar scraping")
        
        opcion = input("\n  Opción (1/2/3): ").strip()
        
        if opcion == "1":
            page += 1
            time.sleep(1)
        elif opcion == "2":
            break
        elif opcion == "3":
            return total_nuevos, True
        else:
            print(" Opción inválida, continuando...")
            page += 1
            time.sleep(1)
    
    print(f"\n✅ Total nuevos en {category_name}: {total_nuevos}")
    return total_nuevos, False


def main():
    print("="*80)
    print("SCRAPING INTERACTIVO - MERCADOLIBRE ECUADOR")
    print("="*80)
    
    # Mostrar estado actual
    print(f"\nEstado actual de la base de datos:")
    for category in LISTING_CONFIG.keys():
        count = products_col.count_documents({"categoria": category})
        print(f"  • {category.capitalize()}: {count} productos")
    
    total_bd = products_col.count_documents({})
    print(f"\n  Total: {total_bd} productos")
    
    # Preguntar si quiere limpiar
    print("\nOPCIONES:")
    print("1. Continuar agregando productos")
    print("2. LIMPIAR base de datos y empezar de cero")
    print("3. Ver muestra de productos en BD")
    
    opcion = input("\nSelecciona una opción (1/2/3): ").strip()
    
    if opcion == "2":
        confirmar = input("¿Estás seguro de ELIMINAR todos los productos? (si/no): ").strip().lower()
        if confirmar == "si":
            result = products_col.delete_many({})
            print(f"Eliminados {result.deleted_count} productos")
        else:
            print("Operación cancelada")
            return
    elif opcion == "3":
        print("\nMuestra de productos en BD (primeros 5):")
        for doc in products_col.find().limit(5):
            print(f"  • {doc.get('titulo', 'Sin título')[:60]}...")
            print(f"    URL: {doc.get('url_producto', 'Sin URL')[:80]}...")
            print()
        return
    
    # Scrapear categorías
    total_productos = 0
    terminar = False
    
    for category, cfg in LISTING_CONFIG.items():
        if terminar:
            break
            
        nuevos, terminar = scrape_categoria_interactivo(
            category, 
            cfg["base_url"], 
            cfg["max_pages"]
        )
        total_productos += nuevos
    
    # Resumen final
    print(f"\n{'='*80}")
    print(f"SCRAPING FINALIZADO")
    print(f"{'='*80}")
    print(f"Total de productos NUEVOS agregados: {total_productos}")
    print(f"Total de productos en BD: {products_col.count_documents({})}")
    
    print(f"\nDISTRIBUCIÓN FINAL:")
    for category in LISTING_CONFIG.keys():
        count = products_col.count_documents({"categoria": category})
        print(f"  • {category.capitalize()}: {count} productos")
    
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
