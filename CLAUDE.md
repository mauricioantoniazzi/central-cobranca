# Central de Crédito e Cobrança — Distribuidora Aurora

Guia para quem for mexer aqui (gente da equipe ou uma conversa nova do Claude, sem memória do que foi decidido).
Leia as seções 0 a 3 antes de qualquer coisa. O resto é consulta.

Quem é "o dono": a pessoa que encomendou a Central e decide o que ela faz (lado financeiro da Aurora). Conversa em português do Brasil, quer respostas
claras, com número, sem jargão. Tudo que está aqui como "decisão" foi dele (ou foi proposta e ele aceitou).

## 0. Em resumo

- É um programa local em Python puro (só biblioteca padrão, Python 3.8+), que lê a planilha `Base_bruta.xlsx` da Aurora
  (distribuidora de alimentos e bebidas que vende a prazo para o varejo) e mostra 6 telas no navegador:
  **Hoje** (quem ligar primeiro), **Régua de cobrança** (texto pronto para copiar), **Cobranças feitas**, **Risco por cliente**,
  **Previsão de caixa** e **Relatório da semana** (Word para a diretoria).
- Sobe com `python central.py` (ou dois cliques em `iniciar.bat`). Abre em http://127.0.0.1:8000.
- Regras que valem acima de tudo: **não inventar número**; **nunca escrever na planilha**; **"hoje" é a data da planilha, nunca a do computador**;
  **nada de internet, conta, chave, login, pacote instalado nem IA**; **uma conta só por assunto** (a mesma coisa não pode ter dois números).
- O dono pediu: **se bater dúvida, pergunte em vez de escolher por ele**. Aqui isso vale sempre (seção 1).
- Toda mudança se prova com `python conferir.py` (seção 9). Se ele falhar, o conserto é no código, nunca na verificação.
- Para trocar a planilha do mês: seção 11.

## 1. Como trabalhar com o dono (o que ele pediu, repetidas vezes)

1. **Pergunte, não escolha.** Dúvida que muda o resultado (formato, regra de negócio, o que fazer com dado que não bate): use uma pergunta curta,
   com as opções e a sua recomendação. Decisão já tomada (seção 5) não se reabre.
2. **Não invente número.** Tudo que aparece na tela sai de conta em cima da planilha. Se faltar dado para uma conta, a tela **diz que faltou** (etiqueta
   "Falta dado em alguma conta", índice "parcial"); nunca estima para tapar buraco. As poucas premissas que são escolhas nossas (não medidas) estão
   em constantes com comentário, e a tela diz que são premissas (seção 5).
3. **Confirme antes de consertar.** Achou algo que parece defeito? Reproduza, ache a causa, só então corrija. A seção 7 lista o que parecia defeito e não era.
   Procure a causa antes de remendar a aparência (um espaçamento estranho pode ser outra coisa dividindo o mesmo nome).
4. **Olhe de verdade.** Tela se confere abrindo no navegador (inclusive celular estreito), clicando, registrando uma cobrança e desfazendo;
   não lendo o próprio código. Ferramenta pronta em `ferramentas/navegador/` (seção 9).
5. **Refaça a conta por outro caminho.** Número que aparece na tela é conferido contra uma recontagem feita direto na planilha (`independente/`),
   e **de tela para tela**: o mesmo cliente com dois valores em dois lugares é defeito grave (já aconteceu, seção 7).
   Desconfie do que vier redondo demais (0%, 100%, sequência de dias iguais, total exato, categoria vazia): quase sempre é conta que não rodou.
6. **Diga o que mudou de número, em qual tela.** Ao terminar qualquer mudança, relate: o que era, o que virou, o que mudou de número e onde,
   se a ordem da fila de Hoje mudou, e o que você achou que era defeito e não era. Escreva em português do financeiro, sem jargão
   (sem "mediana", "score", "sigma", nome de arquivo na tela).
7. **Não mexa em número de tela antiga sem declarar.** O conferidor compara as telas com um retrato (seção 9). Mudança intencional de número é
   permitida, mas entra na lista de mudanças declaradas com o motivo e é relatada ao dono.
8. **Desfaça o que testou.** Registrou cobrança para testar? Desfaça e deixe a pasta como estava (`dados/` não deve existir ao terminar os testes,
   a não ser que o dono esteja usando a Central de verdade; veja a seção 8).
9. **Antes de entregar um texto que outra pessoa vai ler** (cobrança para cliente, relatório), leia como se fosse quem recebe. Se soar como robô ou
   carta de banco, reescreva.
10. **Não mate processo que não é seu.** Pode haver uma Central do dono rodando na porta 8000 (já foi vista voltando sozinha depois de encerrada). Nos testes use
    `PORTA=82xx` e encerre só o que você subiu (pela porta: nunca "todos os python").

## 2. Como rodar

```
python central.py                 # sobe em http://127.0.0.1:8000 (se a porta estiver ocupada, tenta as 19 seguintes)
iniciar.bat                       # o mesmo, por dois cliques (Windows; tenta "python" e depois "py")
python conferir.py                # a conferência completa (seção 9)
```

Só precisa de Python 3.8 ou mais novo instalado (python.org). **Não há `pip install` para rodar a Central.** (O pacote `openpyxl` é opcional e só serve à recontagem da conferência.)

Variáveis de ambiente (todas opcionais; servem para teste):

| Variável | O que faz |
|---|---|
| `PORTA` | porta inicial (padrão 8000) |
| `SEM_NAVEGADOR=1` | não abre o navegador sozinho |
| `CENTRAL_HORA=HH:MM` | fixa a hora do dia do "agora" da Central (senão vale a hora do computador; seção 5, "Hora") |
| `CENTRAL_DADOS=pasta` | onde ficam os registros de cobrança (padrão: `dados/` ao lado do código) |
| `CENTRAL_BASE=arquivo.xlsx` | usa outra planilha no lugar de `Base_bruta.xlsx` |

PowerShell: `$env:PORTA="8250"; $env:SEM_NAVEGADOR="1"; python central.py`. Git Bash: `PORTA=8250 SEM_NAVEGADOR=1 python central.py`.

Armadilhas do ambiente (Windows):
- O terminal em cp1252 não imprime acento: use `PYTHONIOENCODING=utf-8` ao imprimir texto da Central.
- Git Bash converte argumentos que começam com `/` em caminho de Windows: use `MSYS_NO_PATHCONV=1` ao passar `/risco` etc. para scripts.
- Este projeto **não é um repositório git**. Backup é copiar a pasta.

## 3. O que a planilha tem e o que a Central lê

`Base_bruta.xlsx` (dado fictício, "como se viesse dos sistemas da empresa"). Quatro abas; os **nomes das abas e das colunas importam**:

- **Leia-me**: linha `DATA DE REFERÊNCIA` com a data ao lado (aceita `12 de setembro de 2026`, `12/09/2026`, `2026-09-12` ou data do Excel;
  mês abreviado como `set` também). Todo cálculo é feito "como se hoje fosse" essa data.
- **Clientes**: código, nome, categoria, região, prazo contratado em dias, limite de crédito, "cliente desde", contato (nome de quem se fala).
- **Títulos**: um por linha: número, código do cliente, emissão, valor, vencimento, pagamento. **Pagamento em branco = título em aberto.**
  Valores são reais cheios (a leitura aceita centavos). Tratamos a **emissão como a data do pedido** (é daí que saem "último pedido" e "compras"; é uma leitura nossa, a planilha não diz isso).
- **Cobranças**: contatos de cobrança já feitos (cliente, data e hora, canal, tom, valor, nº de títulos, mensagem).

O que a leitura faz (`leitor_xlsx.py`, `motor.carregar`, `validacao.py`): lê o `.xlsx` sem pacote (zip + XML), converte dinheiro para **centavos inteiros**,
valida e, se a planilha tiver um problema que impede o cálculo, **para com uma mensagem que diz a aba e a linha** (classe `BaseInvalida`). Problemas
que não impedem o cálculo aparecem num quadro amarelo "Avisos sobre a planilha" em Hoje, Risco e Régua (cliente sem título, data de pagamento
depois da data de referência, etc.).

## 4. Mapa dos arquivos (cada um tem a explicação no topo; leia o docstring antes de editar)

| Arquivo | Papel |
|---|---|
| `central.py` | servidor web local (`http.server`), rotas GET/POST. Não tem regra de negócio. |
| `servico.py` | junta os dados que as telas usam (`painel()`), na ordem certa, e escolhe a planilha (`caminho_base()`). |
| `leitor_xlsx.py` | leitor de `.xlsx` só com a biblioteca padrão e leitor da data de referência. |
| `validacao.py` | erros (param) e avisos (seguem) sobre a planilha. |
| `relogio.py` | o "agora" da Central: data da planilha + hora do computador. |
| `motor.py` | leitura da planilha, resumo de Hoje (totais, semana) e a **fila de Hoje** (pontuação). **Não tem cálculo de risco próprio.** |
| `risco.py` | **a fonte única de tudo que se diz de um cliente**: padrão de pagamento, piora, sazonalidade, compras, limite, índice 0–100, tags, alerta. |
| `previsao.py` | previsão de caixa das 4 semanas seguintes (usa `risco.py`, não refaz conta de cliente). |
| `regua.py` | escolhe o tom da cobrança e por quê; monta os fatos do texto. Não escreve texto. |
| `redacao.py` | **o único lugar onde se escreve texto para gente ler** (cobrança e relatório). Contrato do `Redator` no docstring. |
| `relatorio.py`, `docx_min.py` | junta os números já calculados para o relatório; gera o `.docx` só com `zipfile`. **Não calcula nada.** |
| `registro.py` | registros de cobrança feitos na Central (`dados/`), hora pelo relógio da base. |
| `frases.py` | formatadores (`reais`, `reais_est`, `pct1`, `pl`, `arred`) e as frases da tela Hoje. |
| `visual.py`, `navegacao.py` | a **casca** comum de todas as telas: coluna do menu à esquerda (só o nome da empresa, o nome das 6 telas e a data embaixo; no celular vira barra no pé), aviso da planilha, selo de gravidade. Toda página passa por `visual.pagina()`. |
| `pagina*.py` | HTML de cada tela no tema Aurora. **O HTML já nasce completo**: o JavaScript só acrescenta conveniência. Textos longos ficam atrás de dobra (`<details>`), nunca somem. |
| `estatico/` | `tema.css` (regras do visual no topo do arquivo), `app.js` (busca/filtro/ordem da fila e da lista de Risco, "já liguei", Régua lista+texto, contagem do número grande) e `fontes/` (Inter no texto, Manrope nos títulos e números; licença OFL em `LICENCAS.txt`). Servidos por `central.py` em `/estatico/`. |
| `inventario_telas.py` | **a lista do que não pode sumir de cada tela** (alertas, links, a frase de cada cliente, números), tirada dos DADOS. A parte 7 da conferência cobra. `python inventario_telas.py` mostra a lista. |
| `gerar_arquivo_unico.py` | gera `arquivo_unico/Central_AAAA-MM-DD.html`: um arquivo só, abre com dois cliques (seção 14). |
| `conferir.py` | a conferência (seção 9). |
| `independente/` | recontagem feita direto na planilha, por código separado; varredura de escrita. Precisa do pacote `openpyxl` **só para conferir**. |
| `fixtures/` | cópia da planilha de agosto/2026, referência de teste. **Não apague, não edite.** |
| `conferencia_base.json` | o "retrato" das telas Hoje e Risco com a planilha de agosto. **Nunca regravar** (seção 9). |
| `ferramentas/navegador/` | dirige o Edge de verdade: foto de cada tela e medição (seção 9). |
| `dados/` | criada na primeira cobrança registrada. Registros e assinatura. **Não é da planilha; não apague nem copie para fora sem o dono.** |

**Onde ler mais (já está bem explicado lá; não repito aqui):** o topo de cada `.py` (o que é e o que não faz); `conferir.py` (os dois modos e como declarar mudança); `fixtures/LEIAME.txt`;
`redacao.py` (contrato do `Redator`); `registro.py` (onde ficam os dados); `relogio.py` (o "agora"); `validacao.py` (erros × avisos); `ferramentas/navegador/olhar_telas.py` (como olhar as telas);
as constantes comentadas no topo de `risco.py`, `motor.py`, `previsao.py` e `regua.py` (os parâmetros do método); e a aba **Leia-me** da própria planilha (o que cada aba é).

A regra de ouro de arquitetura: **cada número mora num lugar só** e as telas (e o relatório) **leem** dele. Se uma tela precisa de um número que ainda não
existe, ele passa a existir onde os outros moram (`motor.resumo`, `risco.totais`, `previsao.prever`) e **todas** as telas que falam do assunto usam ele.
Relatório que calcula por conta própria é o jeito mais fácil de terminar com dois números para a mesma coisa.

## 5. Decisões e por quê (não reabrir sem o dono)

**Fila de Hoje** (`motor.py`). Pontuação = 40% do valor vencido (raiz do vencido ÷ maior vencido) + 60% do **índice de risco da tela Risco**, e
multiplicada por 0,35 se o cliente foi cobrado nas últimas 48 h. Não é por data de vencimento nem só por valor: era o problema original ("ninguém
sabe por quem começar"). A frase de cada linha é a parte mais importante da tela: tem que dizer, em português, por que o cliente está ali.
*Por que o índice da Risco:* a Hoje tinha um "risco" próprio (só atraso atual + piora recente) com o mesmo nome e outro número; três clientes saíam
com 75%. Foi tratado como defeito grave e removido. Pesos em `PESO_VALOR`/`PESO_RISCO`/`HORAS_SEM_INSISTIR`/`FATOR_COBRADO_RECENTE` (`motor.py`).

**Índice de risco 0–100** (`risco.py`, constantes no topo). Seis fatores com peso e frase cada um (o dono exigiu "índice fechado ninguém confia"):
atraso habitual 10, imprevisibilidade 15, piora recente 25, compras 20, uso do limite 10, vencido fora do padrão 20. Falta dado → o fator sai e o índice
é "parcial" (proporcional aos pesos com dado). Tela Risco é ordenada por **valor em risco = saldo em aberto × índice**, não pelo índice
("onde está o meu dinheiro", não "quem é o pior"). O peso do cliente no faturamento aparece mas **não entra** no índice (o saldo já carrega o tamanho).

**Piora só se acusa com duas condições juntas:** passou de 7 dias **e** de 2 vezes a variação do próprio cliente. "Quem já atrasava 35 e passou
a 42 não deteriorou." Janela recente = 90 dias. O atraso "de hoje" de quem piorou vem **só dos títulos já pagos** (título aberto ainda não tem atraso final,
só piso); a detecção, por prudência, conta os abertos.

**Sazonalidade:** mês do calendário em que o atraso dispara em **dois anos diferentes** é tratado como negócio do cliente (não risco) e fica fora das comparações.

**Os dois casos com nome e sobrenome** (o dono pediu; a planilha erra neles): (1) "atrasa sempre igual" (hoje Serra Azul e Rede Bom Preço): aparece na lista
de vencidos quase todo mês, mas não é risco; o prazo real é contrato + atraso típico; (2) "nunca aparece em lista, mas piora e compra menos": **hoje nenhum cliente
passa nos critérios** e a tela diz isso; o mais parecido (Vila Nova) aparece na lista, escondido entre outros por ordem de data.

**Dinheiro:** guardado em **centavos, inteiros**. Valor **fechado** (título, soma de títulos, total vencido) mostra centavo. **Estimativa**
(valor em risco, previsão, médias) é arredondada em reais, **sem centavo**. **Indicadores do topo** de Hoje, ficha de Risco e Previsão também sem centavo
(pedido do dono). O "R$" não se separa do valor (espaço inseparável, `frases.NB`). Percentual com vírgula (`pct1`). Arredondamento **meio para cima**
(`frases.arred`: 6,5 → 7); o `round` do Python arredonda 6,5 para 6 e já causou número diferente entre telas. Plural: use `frases.pl`.

**Hora.** O "hoje" é a **data da planilha**. A **hora** do dia vem do relógio do computador (o dono escolheu assim). Consequência que **não é defeito**:
a regra das 48 h usa essa hora, então a ordem da fila de Hoje pode mudar ao longo do dia (um cliente cobrado às 14:20 do dia anterior à data sai da janela
às 14:20 do dia da data). E como a data não anda, um registro feito na Central nunca "envelhece" além do dia até a planilha trazer outra data.
Para teste, `CENTRAL_HORA=10:00` deixa tudo reprodutível.

**Previsão de caixa** (`previsao.py`, só a carteira que já existe, sem venda nova; a tela escreve isso). Cada título em aberto: data esperada = vencimento + atraso
típico do cliente (comportamento **recente** para quem piorou; atraso do mês para mês sazonal). Chance de entrar = (1 − 30% × índice) × (1 − 50% × posição do
atraso atual, só para vencido). **As duas taxas são premissas, não medidas** (a base não tem nenhum título perdido para calibrar) e a tela diz isso.
Vencido que já passou de todo atraso que o cliente teve fica **"sem data"** (não se chuta). Conservador/otimista = pior/melhor 10% dos atrasos do cliente.
A faixa conservador–otimista só existe no **acumulado**: semana a semana os cenários se cruzam (atrasar só empurra o dinheiro), e a tela explica.
O elemento dominante da tela é a **diferença** entre a soma de vencimentos (o que a planilha diz) e o esperado, decomposta em adiado / sem data / chance de não entrar / antecipado.

**Régua de cobrança** (`regua.py` escolhe, `redacao.py` escreve). 8 tons, escolhidos pelos números nesta ordem: parou de comprar → Conversa comercial (**não lista títulos**, só o total);
piorou → Conversa sobre a mudança (conversa, não ameaça); fora do padrão → escada pelos contatos já feitos depois do vencimento (0: primeiro aviso, cordial ou a cliente grande;
1: objetiva; 2 ou mais: formal); atrasa sempre igual → lembrete com sugestão de acertar o prazo no contrato; resto → lembrete leve. "Cliente grande" = pesa ≥10% do
faturamento de 12 meses. Prazo de resposta da formal: 3 dias. A tela mostra **por que** aquele tom e deixa trocar na mão (o texto se reescreve na hora). Texto por canal:
WhatsApp curto, e-mail com assunto, telefone vira roteiro. Sem "Prezado" nem "obrigado" (não assumem gênero); sem ameaça nem consequência inventada;
nunca expõe a análise interna ao cliente. **A Central redige e copia; quem manda é a pessoa.** Nenhuma integração.

**Registro de cobrança** (`registro.py`): fica em `dados/cobrancas_registradas.json` (+ `configuracao.json` com a assinatura), **fora da planilha**, e a tela diz de onde vem
cada coisa (planilha da empresa × registrada na Central). Hora do registro = data da planilha + hora do computador. Dá para desfazer (só os da Central).
Cobrado nas últimas 48 h desce na fila. **Decisão do dono (base nova):** ao trocar a planilha, os registros da Central **continuam como histórico**
(não se arquivam), porque a empresa provavelmente não vai lançar esses contatos na aba Cobranças; se isso mudar, duplicam (seção 7) e será preciso arquivar.

**Relatório da semana:** documento Word (`.docx`), texto corrido, números dentro das frases, ~4 minutos de leitura, termina em decisões em ordem de valor em risco. Semana = 7 dias até a
data da planilha, inclusive. Escrito por `redacao.py`; não calcula nada.

**Sem IA:** todo texto é montado por regras a partir dos números. O ponto de troca por um modelo de linguagem está isolado em `redacao.REDATOR` (um `Redator` com `cobranca(ctx)` e
`relatorio(ctx)`; o resto da Central só entrega fatos e recebe texto). O conferidor falha se algum módulo importar biblioteca de rede, e-mail ou IA.

**Linguagem e forma:** tudo em português do Brasil; o público é financeiro/diretoria. Nada de jargão estatístico na tela. HTML sem JavaScript (exceto a Régua) e sem recurso externo.
Claro e escuro pelo navegador. Tela de celular (390 px) precisa funcionar: tabelas viram cartões até 860 px.

## 6. O que não pode mudar de jeito nenhum

1. `Base_bruta.xlsx` nunca é escrita pela Central. (A conferência compara o hash antes e depois.)
2. "Hoje" = data da planilha. Nunca `date.today()`/`datetime.now()` para decidir nada além da **hora** do registro (`relogio.py`).
3. Dinheiro em centavos inteiros, sem `float` no caminho do dinheiro. Fechado com centavo, estimativa sem.
4. **Uma conta por assunto, um nome por conta.** `risco.py` é o dono das contas de cliente; Hoje, Previsão, Régua e Relatório leem dele. Não recalcule mediana, índice, posição, limite ocupado, etc. em outro lugar.
   Se duas telas usam a mesma palavra ("risco", "limite", "atraso"), é o mesmo número.
5. `conferencia_base.json` e `fixtures/Base_2026-08.xlsx` não se alteram. O conferidor recusa `--gravar` com outra planilha.
6. Nenhum texto para cliente/diretoria fora de `redacao.py`. Nenhuma importação de rede/IA (o conferidor checa).
7. Quem foi cobrado nas últimas 48 h desce na fila (regra de negócio do dono).
8. Toda estimativa diz que é estimativa e nunca mostra centavo. Toda premissa nossa está escrita na tela.
9. Quando faltar dado, a tela diz que faltou. Não estimar para tapar.

## 7. O que parece defeito e não é

- **Vila Nova, Dona Zica etc. "no topo" mudando de posição ao longo do dia:** é a janela de 48 h com a hora do computador (seção 5, "Hora").
- **Dona Zica com índice "parcial"** mesmo tendo 37 pagamentos: o que falta é pagamento **recente** para medir piora (só 1 título venceu em 90 dias). A etiqueta diz "Falta dado em alguma conta", com o motivo na ficha.
- **"Vencido fora do padrão 20 de 20"** para qualquer atraso acima do máximo histórico (44 ou 112 dias dão o mesmo): é o desenho (satura). Não distingue gravidade acima do máximo.
- **Previsão: "Antecipado R$ 0":** nenhum cliente tem atraso típico negativo, então nenhum título aberto entra antes do vencimento. É zero de verdade.
- **Previsão semana a semana: conservador à frente do otimista:** é esperado (o otimista já recebeu antes). Por isso a faixa só vale no acumulado.
- **A soma "sem vencidos" da planilha parecer perto do esperado** (R$ 595.710 × R$ 607.674 em agosto): coincidência, e a tela explica.
- **Polo Norte pagando "7, 7, 7, 7, 7":** está assim na base.
- **Hoje: "% do limite" = saldo em aberto ÷ limite** (limite ocupado), o mesmo da ficha de Risco. Não é vencido ÷ limite (esse número existiu e foi removido por colidir com o nome).
- **"Última cobrança … há 44 horas" na Hoje e na Cobranças feitas:** as duas usam a mesma régua de tempo (`frases._tempo`).
- **Dois clientes "aparecem como atrasados mas não são risco"** e mesmo assim o relatório manda "não cobrar antes de N dias": é o caso nº 1 da seção 5.
- **Tabelas que rolam para o lado em tela média:** o que estiver dentro de `.tbl` rola de propósito (a sonda do navegador lista esses textos como "fora do quadro"; ignore os de `DIV.tbl`).
- **A sonda `sonda.js` dizendo "0" × "hoje" sobrepostos no eixo da Previsão:** as caixas se tocam em 1–2 px; não cobrem nada.
- **Registros da Central aparecendo duplicados depois da troca da planilha:** só acontece se a aba Cobranças nova **também** trouxer esses contatos. Hoje é a hipótese contrária (seção 5).
- **Conferência `FALHOU ... mudou sem declarar`:** significa que uma tela antiga mudou de número. Não é para "consertar a conferência": ou é bug (corrija o código) ou é mudança
  intencional (declare em `DECLARADAS`, com o motivo, e relate ao dono).
- **Ruído do medidor:** já houve "valor quebrado em duas linhas" que era a barra ao lado do valor contando como segunda linha. Confirme com a foto antes de corrigir.

## 8. Dados de verdade × dados de teste

- `dados/` (registros e assinatura) é do **uso real**. Nos testes aponte `CENTRAL_DADOS` para uma pasta temporária. A conferência já faz isso sozinha.
- Se você registrar cobrança na pasta real para testar (por exemplo, pelo navegador), **desfaça** e apague `dados/` se ela não existia antes.
- Dados da planilha são **fictícios** (empresa, clientes, telefones `(11) 9XXXX-XXXX`). Não há dado pessoal real.

## 9. Conferência (`conferir.py`) e ferramentas de teste

`python conferir.py` (leva 1 a 2 minutos). Sai com código 0 se tudo passou. **Dois modos, escolhidos sozinhos pela planilha em uso:**

- **REFERÊNCIA** (a planilha é idêntica a `fixtures/Base_2026-08.xlsx`): roda tudo, inclusive a comparação das telas Hoje e Risco com o retrato. É o modo para provar
  que uma mudança de código/tela não mexeu em número. Depois de trocar a planilha: `CENTRAL_BASE=fixtures/Base_2026-08.xlsx python conferir.py`
  (PowerShell: `$env:CENTRAL_BASE="fixtures/Base_2026-08.xlsx"; python conferir.py`).
- **BASE NOVA** (qualquer outra): a comparação com o retrato não se aplica (os números mudaram de verdade); as demais partes rodam.

O **retrato** (`conferencia_base.json`) é um arquivo com os números e os textos das telas Hoje e Risco de cada cliente, tirado com a planilha de agosto/2026 **antes** de a Previsão existir.
Ele é a prova de que as telas antigas não mudaram de número sem ninguém declarar. Foi gerado por `python conferir.py --gravar` (que só roda com a planilha de referência) e **não se regrava**.

As partes da conferência (em BASE NOVA a 2 não se aplica):
  1. verificações internas (os `assert` de `motor.py` e `risco.py` rodam ao calcular);
  2. *(só referência)* telas × retrato, com a lista de mudanças declaradas (`DECLARADAS`);
  3. as telas não se contradizem (soma por cliente = total, vencido igual nas duas telas);
  4. previsão: fecha em centavos, faixa monotônica no acumulado, decomposição da diferença fecha;
  5. régua e relatório: um tom para cada cliente, todos os 8 tons × 3 canais para cada cliente sem marca de modelo não preenchida, registro (hora da base, persistência, planilha intocada, a fila mexe, desfazer volta ao que era), `.docx` válido, números do relatório iguais aos das telas, sem rede/IA;
  6. auditoria: o risco da Hoje = índice da Risco; mesmo atraso do cliente que piorou em Hoje/Risco/Previsão/Régua; faixa do gráfico = quadro da ficha; estimativa sem centavo; "R$" sem quebra; vírgula decimal;
     concordância; sem jargão; tabelas rolam ou viram cartão; e a **recontagem independente** (`independente/comparar.py`: lê a planilha com `openpyxl`, refaz totais, índice, valor em risco, fila, previsão e compara com o HTML servido; `independente/escrita.py`: varre ~240 textos).
     Sem `openpyxl` a recontagem é **pulada com aviso** (a Central não precisa dele).
  7. **inventário**: cada item de `inventario_telas.py` está na página (visível ou atrás de dobra) em todas as telas e nas 12 fichas;
  8. **visual e arquivo único**: anel = vencido/aberto, gravidade sempre com palavra, 1 só "primeiro" na fila, descobertas com link, todo valor do relatório na cor do dinheiro, contraste ≥ 4,5:1,
     e o arquivo único (nenhum endereço de internet, 18 telas dentro, inventário completo, 168 textos de cobrança, relatório .docx de verdade, o que está desligado escrito na tela).
  O que só um navegador prova (cabe sem rolar, nada em cima de nada, usar de verdade) está em `ferramentas/navegador/conferir_visual.py PORTA [arquivo.html]` (1920x1080, 1366x768, 390; busca, filtro, "já liguei"+desfazer, Régua, listas de escolha legíveis).
  Suba antes a Central de teste: `bash ferramentas/navegador/reiniciar_teste.sh` (porta 8250, nunca a 8000, dados de teste em pasta temporária).
  Cuidado: a varredura de escrita tem trava (espera 8 tons × 3 canais × clientes); se a marcação da Régua mudar e a trava acusar, **conserte a varredura**, não a desligue.

Como ler: `ok` passou; `FALHOU <o quê>` é o que quebrou; `(pulado ...)` não se aplica a esta planilha.
**Se uma verificação quebrar, o conserto é no código, não na verificação.** Verificação nova deve nascer do defeito que ela teria pegado.

Ferramentas que **não** fazem parte da Central (só para conferir):
- `ferramentas/navegador/olhar_telas.py PORTA [larguras]` abre o Edge sem janela, fotografa cada tela (1280 e 390 px por padrão) e mede (rolagem horizontal, texto cortado, botão quebrado,
  rótulo de gráfico sobreposto, texto colado na borda de quadro). Suba a Central antes numa porta de teste. As fotos vão para `ferramentas/navegador/saida/` (pode apagar).
  Para clicar (trocar tom, registrar, desfazer) use `cdp.py` (`Browser`, `.ir()`, `.js()`, `.foto()`).
- `independente/independente.py` sozinho imprime os totais da planilha (em aberto, vencido, a vencer, entrou na semana...) por um caminho que não usa a Central: bom para um olhômetro rápido.

## 10. Como mexer nas telas ou acrescentar coisa

1. Antes de começar, rode `python conferir.py` **na base de referência** (`CENTRAL_BASE=fixtures/Base_2026-08.xlsx`) e veja tudo passar. Essa é a sua linha de base.
2. **Mudança só de aparência** (CSS, texto, espaçamento): o conferidor vai listar o HTML da tela como mudado. Isso é esperado; ele só aceita se estiver em `DECLARADAS` (ex.: `^/hoje/html$`).
   Acrescente a linha com o motivo. Os números (`indice`, `valor_em_risco`, `saldo`, ordem, pontos dos fatores, resumo de Hoje) **não podem** mudar e o conferidor checa isso separadamente.
3. **Tela nova:** crie `pagina_x.py` (HTML), a rota em `central.py`, o item em `navegacao.py`, e acrescente a tela ao dicionário `paginas` da parte 6 em `conferir.py` e à lista de `paginas` de `independente/escrita.py`.
4. **Número novo:** calcule onde o assunto mora (seção 4), exponha, e faça **todas** as telas que falam dele usarem. Acrescente uma checagem de tela-para-tela em `conferir.py` (parte 6) e, se for conta, a recontagem em `independente/`.
5. **Tom novo de cobrança:** `regua.TONS` + a regra em `regua.escolher` + o texto em `redacao._PARTES` (partes para WhatsApp/e-mail e o roteiro de telefone). A conferência gera todos os tons × canais × clientes.
6. **Mudar peso/limite de método:** só nas constantes (topo de `risco.py`, `motor.py`, `previsao.py`, `regua.py`). Vai mudar número: siga a seção 1, item 7.
7. **Texto para gente:** só em `redacao.py` (cobrança e relatório) ou em `frases.py`/`pagina*.py` (frases de tela). Use `frases.reais`, `reais_est`, `pct1`, `pl`, `arred`, e reveja com o olho de quem recebe.
8. Depois de mudar: `python conferir.py` (referência), olhe as telas com `olhar_telas.py` em 1280 e 390 px, registre e **desfaça** uma cobrança pela Régua, gere o relatório.
9. Relate ao dono na forma da seção 1, item 6.

## 11. Passo a passo: trocar a planilha pela do mês novo e conferir que continua fechando

Antes: feche a Central. Faça **backup**: copie `Base_bruta.xlsx` para um nome datado (por exemplo `bases_antigas/Base_2026-08.xlsx`, fora de `fixtures/`) e copie a pasta `dados/` se ela existir.

1. **Coloque a planilha nova como `Base_bruta.xlsx`**, ao lado de `central.py` (mesmo nome, substitui a antiga). Precisa ter as quatro abas (Leia-me, Clientes, Títulos, Cobranças) com os mesmos títulos de coluna,
   e a linha `DATA DE REFERÊNCIA` na Leia-me com a **nova** data. (Se quiser testar sem substituir: `CENTRAL_BASE=caminho\da\nova.xlsx`.)
2. **Suba**: `python central.py`. Se aparecer `A planilha tem um problema: ...`, a mensagem diz a aba e a linha; corrija a planilha e suba de novo. Não contorne no código.
3. **Leia os avisos** no quadro amarelo de Hoje e de Risco (cliente sem título, data de pagamento depois da data de referência, cliente novo etc.). Avisos não impedem, mas alguém precisa olhar.
4. **Confira a data**: Hoje deve dizer "posição em <nova data>". Se disser a data antiga, a Leia-me não foi atualizada.
5. **Rode a conferência**: `python conferir.py`. Vai dizer `(modo BASE NOVA ...)`. Esperado: todas as verificações das partes 3 a 6 passam (a parte 2 "não se aplica"; a recontagem independente,
   no fim da parte 6, diz "pulada" se faltar `openpyxl`; para tê-la, instale `openpyxl` **só nesta máquina de conferência**: `pip install openpyxl`).
   - `FALHOU` em "soma por cliente = total", "planilha: soma dos vencimentos", "decomposição", "recontagem independente": **número que não fecha**. Pare, ache a causa (planilha com dado estranho ou bug), não entregue.
   - `FALHOU` em escrita/concordância/centavo: o dado novo expôs um texto que só aparece em certos casos (ex.: "1 títulos"). Corrija o texto com `frases.pl`/`arred` e acrescente o caso.
6. **Olhe as telas de verdade**: `olhar_telas.py` (seção 9) e abra, no mínimo, Hoje, Risco (um cliente novo, se houver), Previsão e o Relatório. Veja se a fila de Hoje faz sentido com o que a equipe sabe.
7. **Confira por olho três totais** contra a planilha aberta no Excel: em aberto, vencido, entrou na semana (`python independente/independente.py` os imprime por outro caminho).
8. **Registros da Central (`dados/`)**: ficam como histórico. Abra "Cobranças feitas": deve mostrar as duas fontes separadas. Como a data da planilha avançou, os registros antigos já passaram das 48 h (não interferem na fila).
   Se a aba Cobranças nova **já trouxer** os contatos que a equipe registrou pela Central, vão aparecer em duplicata: avise o dono (a decisão combinada foi "não" trazer; se mudou, é preciso criar um passo de arquivar `dados/`).
9. **Regressão do código (só se você mudou código nesta rodada):** `CENTRAL_BASE=fixtures/Base_2026-08.xlsx python conferir.py` precisa continuar `Todas as verificações passaram` no modo REFERÊNCIA.
10. **Atualize este arquivo**: acrescente uma linha na tabela abaixo e, se alguma decisão mudou, ajuste a seção 5.
11. Se a base nova trouxer clientes novos, confira as fichas deles: um cliente novo aparece com "Falta dado" até juntar 20 pagamentos pagos (e o motivo está escrito na ficha); isso é correto, não invente padrão para ele.

O que a troca **não** exige: apagar `dados/`, regravar `conferencia_base.json` (**nunca**; o conferidor recusa), mexer em `fixtures/`, reinstalar nada.

| Planilha | Data de referência | Observação |
|---|---|---|
| `fixtures/Base_2026-08.xlsx` | 12/08/2026 | planilha original e referência de teste (12 clientes, 754 títulos, 5 cobranças) |

## 12. Limites conhecidos e perguntas em aberto para o dono

- Situações testadas em cópias da planilha e tratadas (param com mensagem ou seguem com aviso): nenhum título vencido; cliente sem título; título de cliente fora do cadastro (para, com mensagem);
  cliente novo com poucos pagamentos e título vencido; data da Leia-me em outro formato; aba Cobranças vazia; coluna renomeada, data em branco, texto no lugar do valor (param, com aba e linha).
- **Não testado com planilha real do mês seguinte**: a Central foi validada com a de agosto/2026 e com variações sintéticas. Na primeira troca de verdade, siga a seção 11 sem pular o passo 6.
- A recontagem independente cobre o que está descrito na seção 9; **não** julga se a regra de negócio (pesos, limites, premissas) é boa. Isso é decisão do dono.
- O cliente "silencioso" (seção 5, caso 2) é definido por critérios fixos; pode não aparecer nunca. Se o dono quiser critérios mais frouxos, pergunte antes de mudar.
- Hora do computador no "agora": dono escolheu assim sabendo do efeito (seção 5, "Hora"). Se a fila mudando de ordem ao longo do dia atrapalhar, a alternativa é fixar a hora (`CENTRAL_HORA`); **pergunte**.

## 14. O visual (tema Aurora) e o arquivo único

**Regras do visual** (também no topo de `estatico/tema.css`). O dono pediu tela escura, bonita (degradê, vidro, brilho) **e limpa**: na 2ª rodada de visual disse "está poluído" e mandou cortar:
- **Menos blocos.** Cada tela abre com UM painel (o que é a mesma ideia vive junto), uma linha de ferramentas e o conteúdo. Nada de título + subtítulo + frase de explicação antes do conteúdo (o título é só para leitor de tela; a data da base fica na coluna da esquerda).
- **Letra de sistema normal** (15 px, fixa). Nada de "modo telão"; quem projeta dá zoom no navegador. Fonte dos títulos e números: Manrope (o dono não gostou da Unbounded).
- **Cartão da fila = 4 fileiras**: (1) posição, nome, selos, valor; (2) quem é o cliente + categoria/região + com quem falar + telefone; (3) a frase (2 linhas nos 3 primeiros, 1 linha do 4º para baixo); (4) botões e links na mesma linha. Do 4º para baixo os botões viram só links. O resto fica em "Por que está aqui". Contas de quem está visível: `app.js` refaz isso ao filtrar/ordenar.
- **Lista = tabela, cartão = destaque.** Risco por cliente é uma tabela; a linha de atraso por cliente usa uma escala única e só aparece se o atraso variou 8 dias ou mais ("estável" nos demais).
- **Casos que a lista engana**: todos, curtos (`risco.achados`), o texto longo atrás de clique.
- **Gráficos onde o desenho conta mais rápido que o parágrafo**: Risco (bolhas índice × saldo com anel nos que pioram; concentração do valor em risco), Previsão (cascata, acumulado, por semana, quem pesa na diferença), ficha (pagamento e compras). Cada um diz por que está ali.
- Uma cor, um trabalho: coral = risco alto, âmbar = atenção, verde = normal, **ciano-claro = dinheiro** (`frases.envolve_dinheiro`), violeta = ação/seleção. **Cor nunca vem sozinha**: gravidade é "Risco alto/médio/baixo" (`frases.faixa_risco`: 60+, 30 a 59, abaixo) com forma e palavra.
- Brilho só no principal; vidro e degradê em todo lugar; animação nunca esconde conteúdo (`prefers-reduced-motion` desliga tudo).
- Listas de escolha (`select`): fundo escuro opaco e `color-scheme: dark` (antes ficavam claro sobre claro).
- **Encurtar/juntar/esconder atrás de clique pode; sumir não** (inventário). A página inteira de cada tela deve ficar mais curta que a anterior.
- "Já liguei" registra uma ligação (canal Telefone, tom sugerido, todos os vencidos) com desfazer. O telefone vem da coluna Telefone da planilha (opcional).

**Arquivo único** (`python gerar_arquivo_unico.py`): retrato da base no momento de gerar. CSS, JavaScript, fontes, as 18 telas, todos os textos de cobrança e o .docx vão dentro; rotas por `#`.
Muda em relação à versão local (e cada item aparece escrito na tela do arquivo): não atualiza sozinho; registrar/desfazer/assinatura e escolher títulos ficam **desligados**; "já liguei" só é lembrado no navegador (localStorage, desce o cliente ×0,35 por 48 h como na Central);
a hora é a de quando o arquivo foi gerado. Antes de enviar: gerar de novo, `python conferir.py` (parte 8) e `conferir_visual.py PORTA arquivo.html`.

## 13. Histórico resumido (para entender por que tem tanta verificação)

1. **Hoje:** fila por valor vencido × risco do próprio histórico × 48 h; frase por linha; stdlib; centavos inteiros.
2. **Risco por cliente:** índice com fatores e frases; casos "atrasa sempre igual" e "silencioso"; sazonalidade; ficha com gráfico.
3. **Previsão de caixa:** data esperada pelo comportamento real; chance de entrar; faixa só no acumulado; diferença em destaque.
4. **Régua de cobrança + Relatório da semana** (dono respondeu: `.docx`; hora do computador; conversa comercial sem listar título; texto por canal).
5. **Auditoria no navegador:** achou a conta de risco duplicada (Hoje × Risco), a faixa do gráfico diferente do quadro, centavo em estimativa, "1 dias", "R$" quebrando linha, rótulos de gráfico, celular.
6. **Indicadores sem centavo, "limite" e "há quanto tempo" unificados** (nomes iguais com números diferentes).
7. Preparar a troca de planilha (validação, `CENTRAL_BASE`, fixture, dois modos de conferência, este arquivo).
8. **Visual Aurora + arquivo único (2 rodadas):** a 2ª enxugou tudo (menu à esquerda, painel único, cartão de 4 fileiras, tabela, mais gráficos, fonte nova).
   Antes: toda a camada visual refeita; nenhum número mudou (o anel "31%" é vencido/aberto, derivado); inventário do que não pode sumir; conferência visual no Edge; arquivo único.
   Lição: a varredura de escrita ficou "cega" (0 textos de cobrança) quando a marcação da Régua mudou e ninguém percebeu; agora tem trava de contagem.
