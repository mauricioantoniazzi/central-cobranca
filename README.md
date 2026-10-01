# Central de Crédito e Cobrança

Painel local para o financeiro de uma distribuidora de alimentos e bebidas que vende a prazo para o varejo (a empresa do exemplo é a **Distribuidora Aurora**, fictícia).
Ele lê uma planilha do Excel e responde, em português e sem jargão, a perguntas como:

- **Quem eu ligo primeiro hoje?** (e por quê, em uma frase por cliente)
- **Quem mudou de comportamento?** Quem aparece como atrasado mas sempre pagou assim, e quem piora sem aparecer em lista nenhuma?
- **Quanto de fato vai entrar nas próximas quatro semanas**, comparado com o que a soma dos vencimentos promete?
- **O que escrevo para cada cliente cobrado**, e **o que digo à diretoria** esta semana?

Roda no seu computador, só com Python. **Não instala nada, não tem conta, chave, login nem internet, e não usa IA.** Tudo o que aparece na tela é conta feita em cima da planilha.

## As seis telas

| Tela | Para que serve |
|---|---|
| **Hoje** | O valor vencido, o que a lista por data não mostra e a fila "quem ligar primeiro". A ordem combina valor vencido, risco do histórico de pagamento do próprio cliente e uma regra de 48 horas (quem foi cobrado há pouco desce). Dá para buscar, filtrar, reordenar e marcar "já liguei". |
| **Régua de cobrança** | Um texto pronto por cliente (WhatsApp, e-mail ou roteiro de telefone), com o tom escolhido pelos números e trocável na hora. Você copia e envia; a Central não manda nada. |
| **Cobranças feitas** | Quem foi cobrado, quando, por qual canal e de quanto, separando o que veio da planilha do que foi registrado na Central. |
| **Risco por cliente** | Índice de risco de 0 a 100 com seis fatores explicados, valor em risco, gráficos de quem deve muito e de quem está piorando, e os casos em que a lista de vencidos engana. Cada cliente tem uma ficha com o gráfico do atraso mês a mês. |
| **Previsão de caixa** | As próximas quatro semanas lendo como cada cliente paga de verdade (e não só o vencimento): a diferença entre a planilha e o esperado, de onde ela vem, a faixa conservador–otimista e o acumulado por semana. Só a carteira que já existe. |
| **Relatório da semana** | Texto corrido para a diretoria, em cerca de quatro minutos de leitura, com download em Word (`.docx`). Não refaz conta: lê os mesmos números das outras telas. |

## Como rodar

Precisa só do **Python 3.8 ou mais novo** ([python.org](https://www.python.org/downloads/)).

```bash
python central.py
```

ou dois cliques em `iniciar.bat` (Windows). O navegador abre em <http://127.0.0.1:8000>. Se a porta estiver ocupada, ele tenta as 19 seguintes.

Variáveis de ambiente opcionais (úteis para teste):

| Variável | O que faz |
|---|---|
| `PORTA` | porta inicial (padrão 8000) |
| `SEM_NAVEGADOR=1` | não abre o navegador sozinho |
| `CENTRAL_BASE=arquivo.xlsx` | usa outra planilha no lugar de `Base_bruta.xlsx` |
| `CENTRAL_HORA=HH:MM` | fixa a hora do "agora" (senão vale a do computador) |
| `CENTRAL_DADOS=pasta` | onde ficam os registros de cobrança |

## A planilha

A Central lê `Base_bruta.xlsx` (ao lado de `central.py`) e **nunca escreve nela**. Ela tem quatro abas, e os nomes das abas e das colunas importam:

- **Leia-me**: com a linha `DATA DE REFERÊNCIA`. Todo cálculo é feito "como se hoje fosse" essa data, nunca a do computador.
- **Clientes**: código, nome, categoria, região, prazo, limite de crédito, cliente desde, contato e telefone.
- **Títulos**: um por linha; pagamento em branco quer dizer título em aberto.
- **Cobranças**: contatos de cobrança já feitos.

Se a planilha tiver um problema que impede o cálculo, a Central para e diz a aba e a linha; problemas leves aparecem num quadro de avisos. Os dados do exemplo são **fictícios**.

Para trocar pela planilha do mês, o passo a passo (com a conferência de que os números continuam fechando) está na seção 11 do [CLAUDE.md](CLAUDE.md).

## Arquivo único para enviar a alguém

```bash
python gerar_arquivo_unico.py
```

Gera `arquivo_unico/Central_AAAA-MM-DD.html`: um arquivo só, com as telas, o visual, as fontes, os textos de cobrança e o relatório em Word dentro. Quem recebe abre com dois cliques, sem instalar nada. É um **retrato** da base no momento de gerar (não se atualiza sozinho); registrar cobrança, desfazer e salvar assinatura ficam desligados e isso aparece escrito na tela.

## Conferência

```bash
python conferir.py
```

Leva um ou dois minutos e sai com código 0 se tudo passou. Confere que os números se mantêm entre as telas, que a previsão fecha no centavo, que nenhum item que deve estar numa tela sumiu (`inventario_telas.py`), a escrita dos textos e o arquivo único. Com o pacote opcional `openpyxl` (só para conferir, a Central não precisa dele) refaz as contas direto na planilha por um caminho independente e compara com o que está na tela.

`ferramentas/navegador/` tem o que abre a Central num Edge de verdade, tira foto de cada tela e confere o uso (busca, filtros, Régua, listas de escolha, celular). Usa o Microsoft Edge instalado, via protocolo de depuração, sem instalar nada.

## Como o código está organizado

| Arquivo | Papel |
|---|---|
| `central.py` | servidor local (`http.server`) e rotas; sem regra de negócio |
| `motor.py` | leitura da planilha, resumo de Hoje e a fila |
| `risco.py` | **fonte única** de tudo o que se diz de um cliente: padrão de pagamento, piora, sazonalidade, compras, índice, alertas |
| `previsao.py` | previsão de caixa (usa o `risco.py`, não refaz conta) |
| `regua.py` e `redacao.py` | escolha do tom; **único lugar onde se escreve texto** para cliente e diretoria |
| `relatorio.py`, `docx_min.py` | junta os números para o relatório e gera o `.docx` só com `zipfile` |
| `registro.py` | registros de cobrança feitos na Central (pasta `dados/`) |
| `visual.py`, `navegacao.py`, `pagina*.py` | as telas em HTML (sem JavaScript obrigatório: a página nasce completa) |
| `estatico/` | `tema.css`, `app.js` e as fontes (Inter e Manrope, licença OFL) |
| `inventario_telas.py`, `conferir.py`, `independente/` | a conferência |
| `fixtures/`, `conferencia_base.json` | planilha de referência e retrato dos números; **não editar** |

A regra de arquitetura: **cada número mora num lugar só** e as telas leem dele. Dinheiro em centavos inteiros; valor fechado mostra centavo, estimativa não.

## Regras que não mudam

- A planilha nunca é escrita pela Central.
- "Hoje" é a data da planilha.
- Não se inventa número: quando falta dado, a tela diz que faltou.
- Nada de internet, conta, chave ou IA; o conferidor falha se algum módulo importar rede, e-mail ou IA.
- Os registros de cobrança ficam à parte, em `dados/` (fora do repositório), nunca na planilha.

O guia completo para quem for mexer no projeto (decisões e por quê, o que parece defeito e não é, como acrescentar uma tela) está no [CLAUDE.md](CLAUDE.md).

## Licença

[MIT](LICENSE). As fontes em `estatico/fontes/` seguem a SIL Open Font License (ver `LICENCAS.txt` na pasta).
