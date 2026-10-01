"""Central de Crédito e Cobrança — Distribuidora Aurora.

Uso:  python central.py      (abre http://127.0.0.1:8000 no navegador)
Só biblioteca padrão do Python 3.8+. Lê Base_bruta.xlsx (somente leitura) a cada abertura de página.
Os registros de cobrança ficam à parte, em dados/ (ver registro.py). Nada aqui chama serviço externo.
"""
import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pagina
import pagina_cobranca
import pagina_previsao
import pagina_relatorio
import pagina_risco
import previsao
import regua
import registro
import relatorio
import risco
import servico
from validacao import BaseInvalida
from frases import reais
from relogio import agora



def _json(handler, codigo, dados):
    corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
    handler.send_response(codigo)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(corpo)))
    handler.end_headers()
    handler.wfile.write(corpo)


def _titulos_validos(r, numeros):
    validos = {t["numero"] for t in r["vencidos"]}
    return [n for n in numeros if n in validos]


class Handler(BaseHTTPRequestHandler):
    # ------------------------------------------------------------ GET
    def do_GET(self):
        url = urlparse(self.path)
        caminho = url.path.rstrip("/") or "/"
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        try:
            if caminho == "/regua/texto":
                return self._texto(q)
            if caminho.startswith("/estatico/"):
                return self._estatico(caminho[len("/estatico/"):])
            tipo, corpo, nome = "text/html; charset=utf-8", None, None
            if caminho in ("/", "/hoje"):
                p = servico.painel()
                corpo = pagina.hoje(p["resumo"], p["fila"], p["avisos"], p["rs"], p["n_lista"])
            elif caminho == "/regua":
                p = servico.painel()
                reg = int(q["registrado"]) if q.get("registrado", "").isdigit() else None
                corpo = pagina_cobranca.regua_pagina(p, registro.assinatura(), reg)
            elif caminho == "/cobrancas":
                p = servico.painel()
                corpo = pagina_cobranca.historico_pagina(p, agora(p["ref"]))
            elif caminho == "/risco":
                p = servico.painel()
                corpo = pagina_risco.lista(p["ref"], p["rs"], p["n_lista"], p["avisos"])
            elif caminho == "/previsao":
                ref, rs, _ = risco.analisar(servico.caminho_base())
                corpo = pagina_previsao.pagina(ref, rs, previsao.prever(ref, rs))
            elif caminho == "/relatorio":
                p = servico.painel()
                prev = previsao.prever(p["ref"], p["rs"])
                corpo = pagina_relatorio.pagina(p["ref"], relatorio.blocos(p, prev, agora(p["ref"])), p, prev)
            elif caminho == "/relatorio.docx":
                p = servico.painel()
                prev = previsao.prever(p["ref"], p["rs"])
                corpo = relatorio.docx_bytes(p, prev, agora(p["ref"]))
                tipo = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                nome = "Relatorio_da_semana_%s.docx" % p["ref"].isoformat()
            elif caminho.startswith("/risco/") and caminho[7:].isdigit():
                ref, rs, _ = risco.analisar(servico.caminho_base())
                r = next((x for x in rs if x["cliente"]["codigo"] == int(caminho[7:])), None)
                if r is None:
                    return self.send_error(404)
                corpo = pagina_risco.ficha(ref, r)
            else:
                return self.send_error(404)
            dados = corpo if isinstance(corpo, bytes) else corpo.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            if nome:
                self.send_header("Content-Disposition", 'attachment; filename="%s"' % nome)
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
        except Exception as e:  # mostra o erro na tela em vez de página em branco
            if isinstance(e, BaseInvalida):
                dados = ("<!doctype html><meta charset='utf-8'><title>A planilha tem um problema</title>"
                         "<body style='font:16px system-ui;max-width:720px;margin:40px auto;padding:0 16px'>"
                         "<h1>A planilha tem um problema</h1><p>%s</p><p>Corrija a planilha (%s) e recarregue esta página.</p></body>"
                         % (str(e).replace("<", "&lt;"), os.path.basename(servico.caminho_base()))).encode("utf-8")
                self.send_response(422)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)
                return
            dados = ("Erro: %s" % e).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

    def _estatico(self, rel):
        """Arquivos do visual (CSS, JavaScript, fontes). Só lê dentro da pasta estatico/; qualquer caminho fora dela dá 404."""
        raiz = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "estatico"))
        alvo = os.path.realpath(os.path.join(raiz, *rel.split("/")))
        tipos = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
        ext = os.path.splitext(alvo)[1].lower()
        if not alvo.startswith(raiz + os.sep) or ext not in tipos or not os.path.isfile(alvo):
            return self.send_error(404)
        with open(alvo, "rb") as f:
            dados = f.read()
        self.send_response(200)
        self.send_header("Content-Type", tipos[ext])
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(dados)

    def _texto(self, q):
        p = servico.painel()
        cod = int(q.get("cliente", "0") or 0)
        r = p["risco_por_cliente"].get(cod)
        if r is None or not r["vencidos"]:
            return _json(self, 404, {"erro": "cliente sem título vencido"})
        chave, canal = q.get("tom", ""), q.get("canal", "")
        if chave not in regua.TONS or canal not in registro.CANAIS:
            return _json(self, 400, {"erro": "tom ou canal inválido"})
        titulos = _titulos_validos(r, [x for x in q.get("titulos", "").split(",") if x])
        if not titulos:
            return _json(self, 400, {"erro": "escolha ao menos um título"})
        sug, razoes = regua.escolher(p["ref"], r, regua.contatos_do_cliente(p["cobrancas"], cod))
        saida, ctx = pagina_cobranca.texto_da_cobranca(p["ref"], p, cod, chave, canal, titulos, registro.assinatura())
        _json(self, 200, {"texto": saida["texto"], "assunto": saida["assunto"], "sugerido": sug,
                          "porque_html": pagina_cobranca.porque_html(p["ref"], chave, sug, razoes),
                          "total": reais(ctx["total"])})

    # ------------------------------------------------------------ POST
    def do_POST(self):
        caminho = urlparse(self.path).path.rstrip("/")
        try:
            if "application/json" not in self.headers.get("Content-Type", ""):
                return _json(self, 415, {"erro": "conteúdo deve ser JSON"})  # barra envio vindo de outras páginas
            n = int(self.headers.get("Content-Length", "0"))
            dados = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            if caminho == "/regua/registrar":
                return self._registrar(dados)
            if caminho == "/regua/assinatura":
                registro.salvar_assinatura(str(dados.get("assinatura", "")))
                return _json(self, 200, {"ok": True})
            if caminho == "/cobrancas/desfazer":
                return _json(self, 200, {"ok": registro.remover(int(dados.get("id", 0)))})
            self.send_error(404)
        except Exception as e:
            _json(self, 500, {"ok": False, "erro": str(e)})

    def _registrar(self, d):
        p = servico.painel()
        cod = int(d.get("cliente", 0))
        r = p["risco_por_cliente"].get(cod)
        if r is None or not r["vencidos"]:
            return _json(self, 400, {"ok": False, "erro": "cliente sem título vencido"})
        chave, canal = d.get("tom", ""), d.get("canal", "")
        if not chave and d.get("ligacao"):  # "Já liguei" na tela Hoje: o tom é o que a Régua sugere, e todos os vencidos entram
            chave = regua.escolher(p["ref"], r, regua.contatos_do_cliente(p["cobrancas"], cod))[0]
            d = dict(d, titulos=[t["numero"] for t in r["vencidos"]])
        if chave not in regua.TONS or canal not in registro.CANAIS:
            return _json(self, 400, {"ok": False, "erro": "tom ou canal inválido"})
        titulos = _titulos_validos(r, [str(x) for x in d.get("titulos", [])])
        if not titulos:
            return _json(self, 400, {"ok": False, "erro": "escolha ao menos um título"})
        valor = sum(t["valor"] for t in r["vencidos"] if t["numero"] in titulos)  # o valor sai dos títulos, não da tela
        rid, quando = registro.registrar(p["ref"], cod, canal, chave, regua.nome_tom(chave), valor, titulos,
                                         str(d.get("mensagem", "")))
        _json(self, 200, {"ok": True, "id": rid, "quando": quando.isoformat(timespec="minutes")})

    def log_message(self, *a):
        pass


def main():
    base = servico.caminho_base()
    if not os.path.exists(base):
        sys.exit("Não encontrei a planilha da empresa (%s). Ela deve se chamar Base_bruta.xlsx e ficar ao lado de central.py, "
                 "ou ser apontada pela variável de ambiente CENTRAL_BASE." % base)
    try:
        servico.painel()  # falha cedo, com mensagem clara, se a planilha estiver inconsistente
    except BaseInvalida as e:
        sys.exit("A planilha tem um problema: %s" % e)
    porta = int(os.environ.get("PORTA", 8000))
    servidor = None
    for p in range(porta, porta + 20):
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    if servidor is None:
        sys.exit("Nenhuma porta livre entre %d e %d." % (porta, porta + 19))
    url = "http://127.0.0.1:%d/" % servidor.server_address[1]
    print("Central de Crédito e Cobrança no ar em %s  (Ctrl+C para encerrar)" % url)
    print("Registros de cobrança: %s" % registro.arquivo())
    if not os.environ.get("SEM_NAVEGADOR"):
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
