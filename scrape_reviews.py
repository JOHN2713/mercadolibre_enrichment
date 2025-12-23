from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import time

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError("No se encontró MONGODB_URI en el .env")

client = MongoClient(MONGODB_URI)
db = client["ml_reviews"]
products_col = db["products"]
reviews_col = db["raw_reviews"]

def setup_driver():
    """Configura el navegador Chrome en modo headless"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = None
    
    # Intento 1: Usar chromedriver del sistema (sin descargar)
    try:
        print("Intentando usar ChromeDriver del sistema...")
        driver = webdriver.Chrome(options=chrome_options)
        print("✓ ChromeDriver del sistema funcionando")
        return driver
    except Exception as e:
        print(f"  No disponible: {e}")
    
    # Intento 2: Usar ChromeDriverManager con caché offline
    try:
        print("Intentando usar ChromeDriver desde caché...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✓ ChromeDriver desde caché funcionando")
        return driver
    except Exception as e:
        print(f"  Error: {e}")
        raise Exception(
            "No se pudo iniciar ChromeDriver.\n"
            "Soluciones:\n"
            "1. Verifica tu conexión a internet\n"
            "2. Instala ChromeDriver manualmente y agrégalo al PATH\n"
            "3. Descarga desde: https://chromedriver.chromium.org/"
        )

def extract_reviews_selenium(driver, url, max_reviews=20):  # Aumentado a 20
    """Extrae reseñas usando Selenium"""
    print(f"   Cargando página con Selenium...")
    driver.get(url)
    
    reviews_data = []
    
    try:
        # Esperar a que cargue la página
        time.sleep(3)
        
        # Scroll para cargar más contenido
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Intentar hacer clic en "Ver más opiniones" múltiples veces
        for _ in range(3):  # Intentar hasta 3 veces
            try:
                ver_mas_btns = driver.find_elements(By.XPATH, 
                    "//button[contains(text(), 'Ver más') or contains(text(), 'opiniones') or contains(text(), 'Mostrar más')]")
                if ver_mas_btns:
                    ver_mas_btns[0].click()
                    print("  ✓ Click en 'Ver más opiniones'")
                    time.sleep(2)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                else:
                    break
            except:
                break
        
        # Selectores posibles para reseñas
        review_selectors = [
            "//div[@class='ui-review-capability__comment']",
            "//p[contains(@class, 'ui-review-capability-comments__comment__text')]",
            "//article[contains(@class, 'ui-review')]",
            "//div[contains(@class, 'ui-pdp-review__comment')]",
            "//*[contains(@class, 'review')]//p",
            "//div[contains(@class, 'ui-review-capability-comments__comment')]//p",
        ]
        
        review_elements = []
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    review_elements = elements
                    print(f"  ✓ Encontradas {len(elements)} reseñas con selector: {selector[:50]}...")
                    break
            except:
                continue
        
        if not review_elements:
            print("   No se encontraron reseñas con los selectores conocidos")
            # DEBUG: Guardar HTML solo del primer producto sin reseñas
            if not os.path.exists("debug_product_page.html"):
                with open("debug_product_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("   Página guardada en debug_product_page.html")
            return []
        
        # Extraer texto de cada reseña
        for idx, element in enumerate(review_elements[:max_reviews]):
            try:
                texto = element.text.strip()
                if not texto or len(texto) < 10:
                    continue
                
                # Intentar extraer calificación (estrellas)
                rating = None
                try:
                    parent = element.find_element(By.XPATH, "./ancestor::article | ./ancestor::div[@class='ui-review']")
                    rating_elem = parent.find_element(By.XPATH, ".//*[contains(@class, 'rating') or contains(@class, 'stars')]")
                    rating_text = rating_elem.get_attribute("aria-label") or rating_elem.text
                    import re
                    match = re.search(r'(\d+)', rating_text)
                    if match:
                        rating = int(match.group(1))
                except:
                    pass
                
                reviews_data.append({
                    "texto": texto,
                    "puntuacion": rating
                })
                print(f"     Reseña {idx+1}: {texto[:50]}... | Rating: {rating}")
                
            except Exception as e:
                print(f"     Error extrayendo reseña {idx+1}: {e}")
                continue
        
    except Exception as e:
        print(f"   Error general: {e}")
    
    return reviews_data

def scrape_reviews_for_product(driver, product_doc, max_reviews=20):  # Aumentado a 20
    url = product_doc["url_producto"]
    categoria = product_doc.get("categoria")
    titulo = product_doc.get("titulo")

    print(f"\n{'='*80}")
    print(f" Producto: {titulo}")
    print(f" Categoría: {categoria}")
    print(f" URL: {url}")

    # Verificar si ya tiene reseñas en la BD
    existing_count = reviews_col.count_documents({"producto_mongo_id": product_doc["_id"]})
    if existing_count > 0:
        print(f"   Este producto ya tiene {existing_count} reseñas. Saltando...")
        return

    reviews = extract_reviews_selenium(driver, url, max_reviews)

    if not reviews:
        print("   No se encontraron reseñas para este producto.")
        return

    docs_to_insert = []
    for r in reviews:
        doc = {
            "producto_mongo_id": product_doc["_id"],
            "categoria": categoria,
            "url_producto": url,
            "titulo_producto": titulo,
            "reseña_texto": r["texto"],
            "puntuacion": r["puntuacion"],
            "origen": "mercadolibre_reviews"
        }
        docs_to_insert.append(doc)

    result = reviews_col.insert_many(docs_to_insert)
    print(f" Insertadas {len(result.inserted_ids)} reseñas en MongoDB.")

def main():
    # Obtener TODOS los productos (sin limit)
    productos = list(products_col.find())

    if not productos:
        print(" No hay productos en la colección 'products'.")
        print("   Ejecuta primero scrape_products.py")
        return

    print(f" Total de productos a procesar: {len(productos)}")
    print(f" Reseñas actuales en BD: {reviews_col.count_documents({})}")

    driver = setup_driver()
    
    try:
        productos_procesados = 0
        reseñas_totales = 0
        
        for idx, p in enumerate(productos, 1):
            print(f"\n[{idx}/{len(productos)}]")
            before_count = reviews_col.count_documents({})
            scrape_reviews_for_product(driver, p, max_reviews=20)
            after_count = reviews_col.count_documents({})
            
            nuevas_reseñas = after_count - before_count
            if nuevas_reseñas > 0:
                productos_procesados += 1
                reseñas_totales += nuevas_reseñas
            
            time.sleep(3)  # Pausa entre productos
            
    finally:
        driver.quit()
        print(f"\n{'='*80}")
        print(f" Scraping completado.")
        print(f" Productos con reseñas: {productos_procesados}/{len(productos)}")
        print(f" Total de reseñas obtenidas: {reseñas_totales}")
        print(f" Total en BD: {reviews_col.count_documents({})}")

if __name__ == "__main__":
    main()
