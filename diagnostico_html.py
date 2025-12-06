import requests
from bs4 import BeautifulSoup

url = "https://listado.mercadolibre.com.ec/audifonos"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Guardar HTML completo
with open("pagina_completa.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

print("✅ HTML guardado en pagina_completa.html")

# Buscar diferentes contenedores
print("\n🔍 Buscando contenedores de productos...")

# Opción 1: li.ui-search-layout__item
items_li = soup.select("li.ui-search-layout__item")
print(f"1. li.ui-search-layout__item: {len(items_li)} encontrados")

# Opción 2: div.ui-search-result
items_div = soup.select("div.ui-search-result")
print(f"2. div.ui-search-result: {len(items_div)} encontrados")

# Opción 3: article
items_article = soup.select("article")
print(f"3. article: {len(items_article)} encontrados")

# Si encontramos items, analizar el primero
if items_li:
    print("\n📦 Analizando primer item (li.ui-search-layout__item):")
    primer_item = items_li[0]
    
    # Buscar todos los h2
    h2_tags = primer_item.find_all("h2")
    print(f"\n  H2 encontrados: {len(h2_tags)}")
    for idx, h2 in enumerate(h2_tags, 1):
        print(f"    {idx}. Clases: {h2.get('class')}")
        print(f"       Texto: {h2.get_text(strip=True)[:60]}...")
    
    # Buscar todos los enlaces
    a_tags = primer_item.find_all("a", href=True)
    print(f"\n  Enlaces encontrados: {len(a_tags)}")
    for idx, a in enumerate(a_tags[:3], 1):
        print(f"    {idx}. Clases: {a.get('class')}")
        print(f"       Href: {a.get('href')[:80]}...")
    
    # Guardar solo el primer item para análisis
    with open("primer_item.html", "w", encoding="utf-8") as f:
        f.write(str(primer_item.prettify()))
    
    print("\n✅ Primer item guardado en primer_item.html")

print("\n🔍 Ejecuta este script y revisa los archivos generados")