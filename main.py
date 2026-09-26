import asyncio
import threading
import tkinter as tk
from tkinter import messagebox
import urllib.request
from io import BytesIO
from PIL import Image, ImageTk
from playwright.async_api import async_playwright


# ==========================================
# 1. NÚCLEO DO SCRAPER (ESTRUTURA MANTIDA)
# ==========================================
async def buscar_skin_dolar_core(codigo_skin: str):
    url = f"https://steamcommunity.com/market/listings/730/{codigo_skin}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded")

            try:
                await page.wait_for_function('document.body.innerText.includes("$")', timeout=10000)
            except:
                pass  # Continua mesmo se der timeout para tentar ler o que carregou

            # 1. Título
            titulo = await page.title()
            nome_skin = titulo.replace(" Steam Community Market :: Listings for ", "").strip()

            # 2. Imagem
            imagem_url = ""
            try:
                imagens = await page.locator('img[src*="economy/image"]').all()
                for img in imagens:
                    src = await img.get_attribute("src")
                    if src and "avatar" not in src.lower():
                        imagem_url = src
                        break
            except:
                pass

            # 3. Extração de Preços (Mesmo script JS)
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

            return {"sucesso": True, "nome": nome_skin, "imagem": imagem_url, "precos": precos}

        except Exception as erro:
            return {"sucesso": False, "erro": str(erro)}

        finally:
            await browser.close()


# ==========================================
# 2. INTERFACE GRÁFICA (TKINTER)
# ==========================================
class SkinScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Skin Scraper")
        self.root.geometry("550x650")
        self.root.configure(padx=20, pady=20)

        # Entrada do Código
        tk.Label(root, text="Código da Skin (Ex: G180720F7083004):", font=("Arial", 10, "bold")).pack(pady=5)
        self.entry_codigo = tk.Entry(root, width=40, font=("Arial", 12))
        self.entry_codigo.pack(pady=5)

        # Botão de Busca
        self.btn_buscar = tk.Button(root, text="Buscar Skin", command=self.iniciar_busca, bg="#4CAF50", fg="white",
                                    font=("Arial", 10, "bold"))
        self.btn_buscar.pack(pady=10)

        # Status
        self.lbl_status = tk.Label(root, text="", fg="blue", font=("Arial", 10, "italic"))
        self.lbl_status.pack()

        # Frame de Resultados
        self.frame_resultados = tk.Frame(root)
        self.frame_resultados.pack(fill=tk.BOTH, expand=True, pady=10)

        self.lbl_nome = tk.Label(self.frame_resultados, text="", font=("Arial", 14, "bold"), fg="#333")
        self.lbl_nome.pack(pady=5)

        self.lbl_imagem = tk.Label(self.frame_resultados)
        self.lbl_imagem.pack(pady=10)

        self.txt_precos = tk.Text(self.frame_resultados, height=8, width=50, font=("Arial", 11), state=tk.DISABLED,
                                  bg="#f4f4f4")
        self.txt_precos.pack(pady=5)

    def iniciar_busca(self):
        codigo = self.entry_codigo.get().strip()
        if not codigo:
            messagebox.showwarning("Aviso", "Digite o código da skin!")
            return

        # Prepara a UI para carregamento
        self.btn_buscar.config(state=tk.DISABLED)
        self.lbl_status.config(text="Buscando dados no Mercado da Steam... Aguarde.")
        self.lbl_nome.config(text="")
        self.lbl_imagem.config(image='')
        self.atualizar_caixa_texto("Limpando resultados anteriores...")

        # Inicia o Playwright em uma Thread separada para não travar a janela
        thread = threading.Thread(target=self.rodar_asyncio, args=(codigo,))
        thread.start()

    def rodar_asyncio(self, codigo):
        # Cria um novo loop de eventos para a Thread em background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resultado = loop.run_until_complete(buscar_skin_dolar_core(codigo))

        # Agenda a atualização da interface na Thread principal
        self.root.after(0, self.atualizar_interface, resultado)

    def atualizar_interface(self, resultado):
        self.btn_buscar.config(state=tk.NORMAL)
        self.lbl_status.config(text="")

        if not resultado["sucesso"]:
            messagebox.showerror("Erro Crítico", f"Falha na extração:\n{resultado['erro']}")
            return

        # Atualiza o Nome
        self.lbl_nome.config(text=resultado["nome"])

        # Baixa e Atualiza a Imagem
        if resultado["imagem"]:
            try:
                req = urllib.request.Request(resultado["imagem"], headers={'User-Agent': 'Mozilla/5.0'})
                raw_data = urllib.request.urlopen(req).read()
                img = Image.open(BytesIO(raw_data))
                img.thumbnail((300, 300))  # Redimensiona para caber na tela
                img_tk = ImageTk.PhotoImage(img)
                self.lbl_imagem.config(image=img_tk)
                self.lbl_imagem.image = img_tk  # Mantém a referência da imagem
            except Exception as e:
                self.lbl_status.config(text="Erro ao carregar a imagem.", fg="red")

        # Formata e Atualiza os Preços
        texto_precos = "💰 PREÇOS POR DESGASTE:\n" + "-" * 40 + "\n"
        lista_desgastes = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]

        for desgaste in lista_desgastes:
            valor = resultado["precos"].get(desgaste, "Indisponível")
            texto_precos += f"• {desgaste}: {valor}\n"

        self.atualizar_caixa_texto(texto_precos)

    def atualizar_caixa_texto(self, texto):
        self.txt_precos.config(state=tk.NORMAL)
        self.txt_precos.delete(1.0, tk.END)
        self.txt_precos.insert(tk.END, texto)
        self.txt_precos.config(state=tk.DISABLED)


if __name__ == "__main__":
    janela_principal = tk.Tk()
    app = SkinScraperApp(janela_principal)
    janela_principal.mainloop()