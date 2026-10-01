"""Cliente mínimo do Chrome DevTools Protocol (só stdlib) para dirigir o Edge de verdade.

Se o Edge estiver em outro caminho, mude EDGE abaixo. Cada Browser(porta=...) usa uma porta de depuração própria e um
perfil temporário (pasta edge_auditoria_<porta> em %TEMP%); feche sempre com .fechar()."""
import base64
import json
import os
import socket
import struct
import subprocess
import time
import urllib.request

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


class WS:
    def __init__(self, url):
        assert url.startswith("ws://")
        host, rest = url[5:].split("/", 1)
        h, p = host.split(":")
        self.s = socket.create_connection((h, int(p)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (rest, host, key)).encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(1)
        self.buf = b""

    def send(self, txt):
        d = txt.encode()
        hdr = bytearray([0x81])
        n = len(d)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        hdr += mask
        self.s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(d)))

    def _read(self, n):
        while len(self.buf) < n:
            c = self.s.recv(1 << 20)
            if not c:
                raise EOFError
            self.buf += c
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            msg += self._read(n)
            if b1 & 0x80:
                return msg.decode()


class Browser:
    def __init__(self, porta=9333, largura=1280, altura=900, movel=False):
        self.proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--remote-debugging-port=%d" % porta,
                                      "--user-data-dir=" + os.path.join(os.environ["TEMP"], "edge_auditoria_%d" % porta),
                                      "--no-first-run", "--hide-scrollbars", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                alvos = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % porta))
                pag = [a for a in alvos if a["type"] == "page"][0]
                break
            except Exception:
                time.sleep(0.5)
        self.ws = WS(pag["webSocketDebuggerUrl"])
        self.id = 0
        self.eventos = []
        self.cmd("Page.enable")
        self.cmd("Runtime.enable")
        self.tela(largura, altura, movel)

    def cmd(self, metodo, **params):
        self.id += 1
        i = self.id
        self.ws.send(json.dumps({"id": i, "method": metodo, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == i:
                if "error" in m:
                    raise RuntimeError("%s: %s" % (metodo, m["error"]))
                return m.get("result", {})
            self.eventos.append(m)

    def tela(self, largura, altura=900, movel=False):
        self.cmd("Emulation.setDeviceMetricsOverride", width=largura, height=altura, deviceScaleFactor=1, mobile=movel)

    def ir(self, url, espera=0.6):
        self.cmd("Page.navigate", url=url)
        t0 = time.time()
        while time.time() - t0 < 15:
            if self.js("document.readyState") == "complete":
                break
            time.sleep(0.1)
        time.sleep(espera)

    def js(self, expr):
        r = self.cmd("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:400])
        return r["result"].get("value")

    def foto(self, caminho):
        m = self.cmd("Page.getLayoutMetrics")
        h = int(m["cssContentSize"]["height"])
        w = int(m["cssContentSize"]["width"])
        r = self.cmd("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                     clip={"x": 0, "y": 0, "width": w, "height": min(h, 16000), "scale": 1})
        open(caminho, "wb").write(base64.b64decode(r["data"]))
        return w, h

    def fechar(self):
        try:
            self.cmd("Browser.close")
        except Exception:
            pass
        self.proc.kill()


def foto_trecho(b, caminho, y0, altura, largura=None):
    m = b.cmd("Page.getLayoutMetrics")
    w = largura or int(m["cssContentSize"]["width"])
    r = b.cmd("Page.captureScreenshot", format="png", captureBeyondViewport=True,
              clip={"x": 0, "y": y0, "width": w, "height": altura, "scale": 1})
    open(caminho, "wb").write(base64.b64decode(r["data"]))
