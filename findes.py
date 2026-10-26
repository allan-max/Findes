from playwright.sync_api import sync_playwright
import time
import unicodedata
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

os.environ["NODE_SKIP_PLATFORM_CHECK"] = "1"

# CARREGA VARIÁVEIS DE AMBIENTE DO ARQUIVO .env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import json
import smtplib
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# CONFIGURAÇÃO DE LOGS
PASTA_LOGS = os.getenv("FINDES_LOGS_DIR", os.path.join(BASE_DIR, "logs"))
ARQUIVO_LOG = os.path.join(PASTA_LOGS, "findes.txt")

class DualLogger:
    def __init__(self, filepath, stream):
        self.terminal = stream
        self.filepath = filepath
        self.buffer = ""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        except Exception:
            pass

    def write(self, message):
        try:
            self.terminal.write(message)
            self.terminal.flush()
        except Exception:
            pass

        self.buffer += message
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line_clean = line.rstrip("\r")
            if line_clean.strip():
                timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
                try:
                    with open(self.filepath, "a", encoding="utf-8", errors="replace") as f:
                        f.write(f"{timestamp} {line_clean}\n")
                except Exception:
                    pass

    def flush(self):
        try:
            self.terminal.flush()
        except Exception:
            pass
        if self.buffer.strip():
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            try:
                with open(self.filepath, "a", encoding="utf-8", errors="replace") as f:
                    f.write(f"{timestamp} {self.buffer.rstrip(chr(13))}\n")
            except Exception:
                pass
            self.buffer = ""

# Redireciona a saída padrão e erros para console + arquivo de log
sys.stdout = DualLogger(ARQUIVO_LOG, sys.stdout)
sys.stderr = DualLogger(ARQUIVO_LOG, sys.stderr)

# CONFIGURAÇÕES DE DIRETÓRIOS E PORTAL
URL_MURAL = os.getenv("FINDES_MURAL_URL", "https://portaldecompras.findes.org.br/Portal/Mural.aspx")
PASTA_DOWNLOAD = os.getenv("FINDES_DOWNLOAD_DIR", os.path.join(BASE_DIR, "downloads"))

# CONFIGURAÇÕES DE E-MAIL
SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

def _carregar_emails(nome_var):
    valor = os.getenv(nome_var, "")
    if valor:
        return [e.strip() for e in valor.split(",") if e.strip()]
    return []

EMAILS_DESTINO_PADRAO = _carregar_emails("EMAILS_DESTINO_PADRAO")
EMAILS_DESTINO_FLUIG = _carregar_emails("EMAILS_DESTINO_FLUIG")

# DADOS DO CADASTRO DE VISITANTE
CADASTRO_CNPJ = os.getenv("CADASTRO_CNPJ", "")
CADASTRO_RG = os.getenv("CADASTRO_RG", "")
CADASTRO_NOME = os.getenv("CADASTRO_NOME", "")
CADASTRO_EMAIL = os.getenv("CADASTRO_EMAIL", "")
CADASTRO_TELEFONE = os.getenv("CADASTRO_TELEFONE", "")
CADASTRO_CONTATO = os.getenv("CADASTRO_CONTATO", "")
CADASTRO_ENDERECO = os.getenv("CADASTRO_ENDERECO", "")
CADASTRO_NUMERO = os.getenv("CADASTRO_NUMERO", "")
CADASTRO_COMPLEMENTO = os.getenv("CADASTRO_COMPLEMENTO", "")
CADASTRO_BAIRRO = os.getenv("CADASTRO_BAIRRO", "")
CADASTRO_CEP = os.getenv("CADASTRO_CEP", "")
CADASTRO_PAIS_VAL = os.getenv("CADASTRO_PAIS_VAL", "BR")
CADASTRO_ESTADO_NOME = os.getenv("CADASTRO_ESTADO_NOME", "ESPIRITO SANTO")
CADASTRO_CIDADE_VAL = os.getenv("CADASTRO_CIDADE_VAL", "")

def enviar_email(dados_resumo, caminho_anexo=None, erro=False):
    objeto_texto = dados_resumo.get('objeto', '').lower()
    
    if 'fluig' in objeto_texto and EMAILS_DESTINO_FLUIG:
        destinos = EMAILS_DESTINO_FLUIG
    else:
        destinos = EMAILS_DESTINO_PADRAO
        
    if not destinos:
        print("Aviso: Nenhum e-mail de destino configurado no .env.")
        return
            
    alerta_erro = '<h1 style="color: red; font-size: 24px; background-color: #ffe6e6; padding: 10px; border: 2px solid red;">FALHA AO BAIXAR O PDF</h1>' if erro else ''
        
    corpo = f'''
    <html>
    <body>
        {alerta_erro}
        <h2>Nova Licitação Encontrada: {dados_resumo['numero_processo']}</h2>
        <ul>
            <li><b>Número do Processo:</b> {dados_resumo['numero_processo']}</li>
            <li><b>Número do Edital:</b> {dados_resumo['numero_edital']}</li>
            <li><b>Objeto:</b> {dados_resumo['objeto']}</li>
            <li><b>Unidade Compradora:</b> {dados_resumo['unidade_compradora']}</li>
            <li><b>Início das Propostas:</b> {dados_resumo['inicio']}</li>
            <li><b>Término das Propostas:</b> {dados_resumo['termino']}</li>
            <li><b>Fase:</b> {dados_resumo['fase']}</li>
            <li><b>Situação:</b> {dados_resumo['situacao']}</li>
            <li><b>Modalidade:</b> <br>{dados_resumo['modalidade'].replace(chr(10), '<br>')}</li>
        </ul>
    </body>
    </html>
    '''
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(destinos)
    msg['Subject'] = f"[ERRO NO PDF] Nova Licitação - {dados_resumo['numero_processo']}" if erro else f"Nova Licitação - {dados_resumo['numero_processo']}"
    msg.attach(MIMEText(corpo, 'html'))
    
    # Anexar arquivo se existir
    if caminho_anexo and os.path.exists(caminho_anexo):
        filename = os.path.basename(caminho_anexo)
        ctype, encoding = mimetypes.guess_type(caminho_anexo)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        
        with open(caminho_anexo, 'rb') as f:
            part = MIMEBase(maintype, subtype)
            part.set_payload(f.read())
            
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(part)
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, destinos, msg.as_string())
        server.quit()
        print(f"E-mail enviado com sucesso para: {', '.join(destinos)} (Com anexo: {'Sim' if caminho_anexo else 'Não'})")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")


def limpar_texto(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()

def aprova_licitacao(objetic):
    texto = limpar_texto(objetic)
    
    if 'aquisicao' not in texto:
        return False
        
    termos_proibidos = ['instalacao', 'instalacoes', 'instalar']
    if any(termo in texto for termo in termos_proibidos):
        excecoes_permitidas = [
            'para instalacao', 
            'para instalar', 
            'p/ instalacao', 
            'p/ instalar',
            'para instalacoes',
            'p/ instalacoes',
            'destinado a instalacao'
        ]
        
        if any(excecao in texto for excecao in excecoes_permitidas):
            return True
        return False
        
    return True

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cdes.json')

print("=== SESSÃO INICIADA ===")
print(f"Log sendo gravado em: {ARQUIVO_LOG}")

while True:
    print("\\n" + "="*60)
    print("Iniciando novo ciclo de verificação...")
    
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chrome", headless=False)
        findes = navegador.new_page()

        print("Carregando página principal de murais...")
        try:
            findes.goto(URL_MURAL, timeout=60000)
        except Exception as e:
            print(f"Erro ao carregar a página principal: {e}")
            continue
        
        try:
            findes.wait_for_selector("td.areaClique", timeout=15000)
        except Exception:
            print("Nenhum item carregado. O site pode estar lento.")
        
        print("Fazendo scroll para carregar CDEs na tela...")
        for _ in range(5):
            findes.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
        linhas = findes.locator('tr:has(td.areaClique)')
        total_linhas = linhas.count()
        
        if total_linhas > 50:
            total_linhas = 50

        cdes_processados = set()
        if os.path.exists(db_path):
            with open(db_path, 'r', encoding='utf-8') as f:
                try:
                    dados = json.load(f)
                    for reg in dados:
                        cdes_processados.add(reg['cde'])
                except json.JSONDecodeError:
                    pass

        dados_filtrados = []

        print(f"Analisando os {total_linhas} primeiros CDEs da tela...")
        for i in range(total_linhas):
            linha = linhas.nth(i)
            texto_cde = linha.locator("td.areaClique").inner_text().strip()
            
            if texto_cde in cdes_processados:
                continue
                
            texto_objetic = linha.locator('td[width="22%"]').inner_text().strip()
            texto_disputa = linha.locator('td[width="19%"]').inner_text().strip()
            
            datas = linha.locator('td[width="14%"]')
            data_inicio = datas.nth(0).inner_text().strip() if datas.count() > 0 else "Não informada"
            data_termino = datas.nth(1).inner_text().strip() if datas.count() > 1 else "Não informada"
        
            if aprova_licitacao(texto_objetic):
                dados_filtrados.append({
                    "cde": texto_cde,
                    "objetic": texto_objetic,
                    "inicio": data_inicio,
                    "termino": data_termino,
                    "disputa": texto_disputa
                })

        print(f"Total de CDEs NOVOS encontrados após o filtro: {len(dados_filtrados)}")
        
        if dados_filtrados:
            for item in dados_filtrados:
                cde = item['cde']
                print(f"\\nEntrando no {cde}...")
                
                # Resumo básico caso o processo falhe antes de carregar o resumo completo da página
                resumo = {
                    'numero_processo': cde,
                    'numero_edital': 'Falhou ao carregar da página',
                    'objeto': item['objetic'],
                    'unidade_compradora': 'Falhou ao carregar da página',
                    'inicio': item['inicio'],
                    'termino': item['termino'],
                    'fase': 'Falhou ao carregar da página',
                    'situacao': item['disputa'],
                    'modalidade': 'Falhou ao carregar da página'
                }
                
                try:
                    findes.locator(f"td.areaClique:has-text('{cde}')").first.click(timeout=30000)
                    
                    findes.wait_for_selector('#grupoResumo', state="attached", timeout=15000)
                    time.sleep(1)
                    
                    def safe_extract(selector):
                        try:
                            el = findes.locator(selector)
                            if el.count() > 0:
                                return el.first.inner_text().strip()
                        except:
                            pass
                        return "Não informado"
                        
                    resumo = {
                        'numero_processo': safe_extract('#lblNumeroProcesso'),
                        'numero_edital': safe_extract('#lblNumeroEdital'),
                        'objeto': safe_extract('#lblObjeto'),
                        'unidade_compradora': safe_extract('#lblUnidadeCompradora'),
                        'inicio': safe_extract('#lblDataInicioProposta'),
                        'termino': safe_extract('#lblDataTerminoProposta'),
                        'fase': safe_extract('#lblFase'),
                        'situacao': safe_extract('#lblSituacao'),
                        'modalidade': safe_extract('#lblModalidade')
                    }
                    print("Informações do processo extraídas (aguardando download para enviar o e-mail)...")
                    
                    findes.wait_for_selector('a[data-acao="anexo"]', state="attached", timeout=15000)
                    time.sleep(2)
                    
                    findes.evaluate("""
                        var botoes = document.querySelectorAll('a[data-acao="anexo"]');
                        for(var i=0; i<botoes.length; i++) { botoes[i].click(); }
                    """)
                    findes.evaluate("try { btAcao_Click('anexo'); } catch(e) {}")
                    
                    arquivo_anexo = findes.locator('div[onclick*="btBaixaAnexo"]').first
                    arquivo_anexo.wait_for(state="visible", timeout=15000)
                    arquivo_anexo.evaluate("el => el.click()")
                    
                    findes.wait_for_selector('#rbConsultarCertameCadastroVisitanteAnexo', state="attached", timeout=15000)
                    
                    if findes.locator('#rbCNPJCadastroVisitanteAnexo').count() > 0:
                        findes.evaluate("document.getElementById('rbCNPJCadastroVisitanteAnexo').click()")
                        time.sleep(0.5)
                        
                    findes.locator('#rbConsultarCertameCadastroVisitanteAnexo').scroll_into_view_if_needed()
                    findes.evaluate("document.getElementById('rbConsultarCertameCadastroVisitanteAnexo').click()")
                    
                    def preencher(seletor, valor, is_select=False):
                        try:
                            el = findes.locator(seletor)
                            if el.count() > 0:
                                id_elemento = seletor.replace('#', '')
                                if is_select:
                                    el.select_option(value=valor, timeout=3000)
                                    findes.evaluate(f"document.getElementById('{id_elemento}').dispatchEvent(new Event('change', {{ bubbles: true }}))")
                                    time.sleep(0.5)
                                else:
                                    el.fill(valor, timeout=3000, force=True)
                                    findes.evaluate(f"document.getElementById('{id_elemento}').value = '{valor}'")
                                    findes.evaluate(f"document.getElementById('{id_elemento}').dispatchEvent(new Event('input', {{ bubbles: true }}))")
                                    findes.evaluate(f"document.getElementById('{id_elemento}').dispatchEvent(new Event('change', {{ bubbles: true }}))")
                                    el.press('Tab')
                        except Exception:
                            pass

                    def selecionar_por_texto(seletor, texto):
                        try:
                            js = f"""
                            var select = document.getElementById('{seletor.replace('#', '')}');
                            if(select) {{
                                for (var i = 0; i < select.options.length; i++) {{
                                    if (select.options[i].text.toUpperCase().includes('{texto.upper()}')) {{
                                        select.value = select.options[i].value;
                                        select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        break;
                                    }}
                                }}
                            }}
                            """
                            findes.evaluate(js)
                            time.sleep(0.5)
                        except Exception:
                            pass
                    
                    # Preenchendo todos os campos solicitados de texto
                    preencher('#tbDocumentoCadastroVisitanteAnexo', CADASTRO_CNPJ)
                    preencher('#tbRGCadastroVisitanteAnexo', CADASTRO_RG)
                    preencher('#tbNomeCadastroVisitanteAnexo', CADASTRO_NOME)
                    preencher('#tbEmailCadastroVisitanteAnexo', CADASTRO_EMAIL)
                    preencher('#tbTelefoneCadastroVisitanteAnexo', CADASTRO_TELEFONE)
                    preencher('#tbContatoCadastroVisitanteAnexo', CADASTRO_CONTATO)
                    preencher('#tbEnderecoCadastroVisitanteAnexo', CADASTRO_ENDERECO)
                    preencher('#tbNumeroCadastroVisitanteAnexo', CADASTRO_NUMERO)
                    preencher('#tbComplementoCadastroVisitanteAnexo', CADASTRO_COMPLEMENTO)
                    preencher('#tbBairroCadastroVisitanteAnexo', CADASTRO_BAIRRO)
                    preencher('#tbCEPCadastroVisitanteAnexo', CADASTRO_CEP)
                    
                    # Preenchimento em cascata de País -> Estado -> Cidade
                    preencher('#ddlPaisCadastroVisitanteAnexo', CADASTRO_PAIS_VAL, is_select=True)
                    selecionar_por_texto('#ddlEstadoCadastroVisitanteAnexo', CADASTRO_ESTADO_NOME)
                    selecionar_por_texto('#ddlEstadoCadastroVisitanteAnexo', unicodedata.normalize('NFKD', CADASTRO_ESTADO_NOME).encode('ASCII', 'ignore').decode('utf-8'))
                    preencher('#ddlCidadeCadastroVisitanteAnexo', CADASTRO_CIDADE_VAL, is_select=True)
                    
                    pasta_destino = PASTA_DOWNLOAD
                    os.makedirs(pasta_destino, exist_ok=True)
                    
                    with findes.expect_download(timeout=30000) as download_info:
                        botao_baixar = findes.locator('#btCadastroVisitanteConfirmarCadastroVisitanteAnexo')
                        botao_baixar.scroll_into_view_if_needed()
                        botao_baixar.click(force=True)
                    
                    download = download_info.value
                    
                    nome_cde_limpo = cde.replace('/', '-').replace('\\', '-').replace(':', '').strip()
                    
                    texto_disputa_lower = item['disputa'].lower()
                    if "sem disputa" in texto_disputa_lower or "without competition" in texto_disputa_lower:
                        sufixo_disputa = "SEM DES"
                    else:
                        sufixo_disputa = "COM DES"
                        
                    # Adiciona a marcação FLUIG se aplicável
                    texto_objeto_lower = item['objetic'].lower()
                    sufixo_fluig = " FLUIG" if "fluig" in texto_objeto_lower else ""
                        
                    # Força a extensão para ser sempre .pdf
                    nome_arquivo_novo = f"{nome_cde_limpo}{sufixo_fluig} {sufixo_disputa}.pdf"
                    
                    caminho_final = os.path.join(pasta_destino, nome_arquivo_novo)
                    download.save_as(caminho_final)
                    print(f"SUCESSO! Arquivo salvo como: {nome_arquivo_novo}")
                    
                    # Agora que o PDF foi salvo, envia o e-mail anexando ele!
                    enviar_email(resumo, caminho_final)
                    
                    novo_registro = {
                        "cde": cde,
                        "objetic": item['objetic'],
                        "inicio": item['inicio'],
                        "termino": item['termino'],
                        "disputa": item['disputa'],
                        "arquivo_baixado": nome_arquivo_novo
                    }
                    
                    dados_db = []
                    if os.path.exists(db_path):
                        with open(db_path, 'r', encoding='utf-8') as f:
                            try:
                                dados_db = json.load(f)
                            except json.JSONDecodeError:
                                pass
                                
                    dados_db.append(novo_registro)
                    with open(db_path, 'w', encoding='utf-8') as f:
                        json.dump(dados_db, f, ensure_ascii=False, indent=4)

                except Exception as e:
                    print(f"\\n--- ERRO AO PREENCHER OU BAIXAR ---")
                    print(f"O erro foi: {e}")
                    print("Enviando e-mail de alerta de falha...")
                    enviar_email(resumo, erro=True)
                    input("O robô parou para análise. Pressione ENTER para pular para o próximo CDE...")
                
                try:
                    findes.goto(URL_MURAL, timeout=60000)
                    findes.wait_for_selector("td.areaClique", timeout=15000)
                except Exception as e:
                    print(f"Erro ao retornar à página principal: {e}")
                    break

        print("\\nFechando o navegador para limpar o cache e evitar bloqueios...")

    print("Aguardando 5 minutos (300 segundos) antes de iniciar a próxima verificação...")
    time.sleep(300)