import asyncio
from playwright.async_api import async_playwright

async def buscar_skin_dolar(codigo_skin: str):
    # URL limpa, sem forçar idioma
    url = f"https://steamcommunity.com/market/listings/730/{codigo_skin}"
    print(f"\n🚀 Acessando a Steam (Versão Dólar): {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Removido o context com locale="pt-BR" para deixar o padrão (Inglês/Dólar)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded")

            # Aguarda o símbolo de Dólar ($) em vez de Real (R$)
            try:
                await page.wait_for_function('document.body.innerText.includes("$")', timeout=10000)
            except:
                print("Aviso: O preço demorou muito a carregar. A Steam pode estar bloqueando a requisição.")

            # 1. Título
            titulo = await page.title()
            nome_skin = titulo.replace(" Steam Community Market :: Listings for ", "").strip()

            # 2. Imagem
            imagem_url = "Imagem não encontrada"
            try:
                imagens = await page.locator('img[src*="economy/image"]').all()
                for img in imagens:
                    src = await img.get_attribute("src")
                    if src and "avatar" not in src.lower():
                        imagem_url = src
                        break
            except:
                pass

            print("\n" + "=" * 55)
            print(f"🔫 SKIN: {nome_skin}")
            print(f"🔗 Imagem: {imagem_url}")
            print("=" * 55)

            # 3. Extração em Dólar usando JavaScript
            precos = await page.evaluate('''() => {
                const desgastes = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"];
                let resultados = {};

                document.querySelectorAll('div, a').forEach(el => {
                    let texto = el.innerText || "";

                    if (texto.length > 5 && texto.length < 150 && texto.includes('$')) {
                        desgastes.forEach(desgaste => {
                            if (texto.includes(desgaste)) {
                                let valores = texto.replace(desgaste, '').trim().split('\\n').filter(v => v.includes('$')).join(' | ');

                                if (valores) {
                                    resultados[desgaste] = valores;
                                }
                            }
                        });
                    }
                });
                return resultados;
            }''')

            print("💰 PREÇOS POR DESGASTE (Normal | StatTrak / Lembrança):")
            lista_desgastes = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]

            for desgaste in lista_desgastes:
                valor = precos.get(desgaste, "Indisponível")
                print(f" - {desgaste}: {valor}")

            print("=" * 55 + "\n")

        except Exception as erro:
            print(f"\n❌ Erro crítico: {erro}")

        finally:
            await browser.close()


if __name__ == "__main__":
    entrada = input("Digite o código da skin (ex: G180720F7083004): ")
    asyncio.run(buscar_skin_dolar(entrada))