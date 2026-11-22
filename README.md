# Agente de leads: contadores no Tocantins

Todo dia útil, este agente encontra de 6 a 10 contadores e escritórios de contabilidade, começando por **Araguaína** e depois pelo resto do **Tocantins**. Ele grava cada um numa planilha do Google com telefone, WhatsApp, e-mail, uma nota de prioridade e uma mensagem de abordagem pronta para você revisar e enviar.

Tudo roda de graça: dados públicos da Receita Federal, GitHub Actions e Google Sheets. A IA para personalizar mensagens é opcional (e paga).

## Como funciona

```
Minha Receita              →  tira quem já está  →  nota 0–100  →  CNPJ.ws          →  mensagem    →  Google Sheets
(CNPJs ativos com CNAE        na planilha           (prioridade)     (e-mail e          sugerida       (aba "Leads")
 6920-6/01, contabilidade)    (por CNPJ)                              telefones)
```

1. **Busca** na [Minha Receita](https://minhareceita.org), que usa os dados abertos do CNPJ, todas as empresas **ativas** com CNAE 6920-6/01 (atividades de contabilidade). Primeiro em Araguaína; quando os de lá acabarem, no estado todo.
2. **Descarta repetidos.** Empresas que já estão na planilha nunca voltam. Matriz e filiais contam como uma empresa só.
3. **Dá uma nota** de 0 a 100 (ver tabela abaixo) e pega os melhores do dia.
4. **Completa o contato** na [CNPJ.ws](https://www.cnpj.ws), que tem o e-mail cadastrado na Receita. O plano grátis aceita 3 consultas por minuto, por isso essa etapa leva uns 4 minutos.
5. **Escreve uma mensagem** de primeira abordagem, sempre com a opção de a pessoa pedir para não receber mais mensagens.
6. **Grava na planilha.**

Números reais de novembro de 2026: **153** escritórios ativos em Araguaína e **1.076** no Tocantins. A 10 por dia útil, isso dá uns 5 meses de leads.

### Como a nota é calculada

| Critério | Pontos |
|---|---|
| Fica em Araguaína | +30 |
| Tem celular (WhatsApp) / só telefone fixo | +25 / +15 |
| Tem e-mail | +10 |
| Escritório (sociedade) / contador individual | +15 / +10 |
| Porte maior que microempresa | +5 |
| Aberto há menos de 2 anos / 2 a 10 anos / mais de 10 | +15 / +10 / +5 |

A coluna **"Por que este lead"** da planilha mostra os critérios de cada um.

## Instalação (uma vez, uns 20 minutos)

### 1. Crie a planilha

1. Crie uma planilha nova no [Google Sheets](https://sheets.new).
2. Copie o **ID** dela, que é o trecho da URL entre `/d/` e `/edit`:
   `https://docs.google.com/spreadsheets/d/`**`ESTE_TRECHO_AQUI`**`/edit`

A aba "Leads" e o cabeçalho são criados sozinhos na primeira execução.

### 2. Crie uma "conta de serviço" no Google (grátis)

É um usuário-robô que o agente usa para escrever na planilha.

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/) e crie um projeto (ex.: `agente-lead`).
2. Em **APIs e serviços → Biblioteca**, procure **Google Sheets API** e clique em **Ativar**.
3. Em **APIs e serviços → Credenciais → Criar credenciais → Conta de serviço**, dê um nome e conclua.
4. Abra a conta criada, vá em **Chaves → Adicionar chave → Criar nova chave → JSON**. Um arquivo `.json` será baixado. **Guarde-o com cuidado e nunca o coloque no repositório.**
5. Copie o e-mail da conta de serviço (algo como `agente@seu-projeto.iam.gserviceaccount.com`).
6. Na sua planilha, clique em **Compartilhar**, cole esse e-mail e dê permissão de **Editor**.

### 3. Cadastre os segredos no GitHub

No repositório: **Settings → Secrets and variables → Actions → New repository secret**.

| Nome | Valor |
|---|---|
| `PLANILHA_ID` | o ID copiado no passo 1 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | o conteúdo inteiro do arquivo `.json` do passo 2 |
| `ANTHROPIC_API_KEY` | *(opcional)* sua chave da API do Claude, para mensagens personalizadas |

### 4. Ajuste o `config.toml`

Preencha seu nome e uma frase com o principal benefício da sua ferramenta:

```toml
[mensagem]
seu_nome = "Seu Nome"
produto = "uma ferramenta de cálculo para contadores"
beneficio = "faz em segundos os cálculos de X que hoje tomam horas na planilha"
```

Ali também dá para mudar a quantidade de leads por dia e as cidades prioritárias. Use o código IBGE do município; Araguaína é `1702109`.

### 5. Coloque na branch principal e teste

O GitHub só roda agendamentos que estão na branch principal (`main`). Depois de juntar este código à `main`:

1. Vá em **Actions → Prospectar leads → Run workflow**.
2. Marque **"Só mostrar os leads no log"** para um teste sem gravar nada, ou deixe desmarcado para gravar de verdade.

A partir daí, ele roda sozinho **de segunda a sexta às 08:23**. Para mudar o horário, edite o `cron` em `.github/workflows/prospectar.yml` (o horário é em UTC: 11:23 UTC = 08:23 no Tocantins).

## Usando a planilha

- **Status**: comece em `Novo`. Mude para `Contatado`, `Respondeu`, `Reunião`, `Cliente` ou **`Não contatar`**.
- **Não apague linhas.** É pela planilha que o agente sabe quem já foi trazido. Para tirar alguém, marque `Não contatar`; ele nunca volta.
- **WhatsApp**: link direto para abrir a conversa (só aparece para celulares).
- **Pesquisar na internet**: busca pronta no Google para achar site ou Instagram antes de abordar.
- **Mensagem sugerida**: revise antes de enviar.

## Boas práticas e LGPD

- **Você envia as mensagens, não o robô.** Mandar mensagens em massa automaticamente leva a bloqueio do número no WhatsApp e a e-mails no spam. O agente pesquisa e prepara; uma pessoa revisa e envia.
- **Opção de sair em toda mensagem.** Quem pedir para sair vira `Não contatar` na hora.
- **Só dados profissionais e públicos.** Os dados vêm do cadastro público de CNPJ. O agente apaga o pedaço de CPF que a Receita deixa no nome de empresários individuais e não guarda dados de sócios.
- **Se perguntarem de onde veio o contato**, responda a verdade: "do cadastro público de CNPJ da Receita Federal".

## Custos

| Item | Custo |
|---|---|
| Minha Receita, CNPJ.ws (plano público), Google Sheets | grátis |
| GitHub Actions | grátis: cada execução leva ~5–15 min, e repositórios privados têm 2.000 min/mês |
| IA (opcional) | o modelo padrão (`claude-opus-5-5`) custa uns US$ 0,01 por mensagem, ~US$ 2–3 por mês para 10 por dia útil. Dá para trocar o modelo em `config.toml`, seção `[ia]`. |

Sem a chave de IA, as mensagens saem de um modelo de texto fixo, e o agente continua 100% grátis.

## Rodar no seu computador

Requer Python 3.11 ou mais novo.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q                                  # testes, sem internet
python -m agente_lead --teste --limite 3             # mostra 3 leads reais sem gravar
python -m agente_lead --csv leads.csv                # grava num CSV em vez do Sheets
```

Para gravar no Sheets localmente, defina as variáveis `PLANILHA_ID` e `GOOGLE_SERVICE_ACCOUNT_JSON`.

## Estrutura do código

| Arquivo | O que faz |
|---|---|
| `agente_lead/sources.py` | Busca na Minha Receita e completa contato na CNPJ.ws |
| `agente_lead/scoring.py` | Nota de 0 a 100 |
| `agente_lead/messages.py` | Mensagem sugerida (modelo de texto ou Claude) |
| `agente_lead/storage.py` | Google Sheets e CSV |
| `agente_lead/pipeline.py` | O fluxo do dia |
| `config.toml` | Configurações sem segredo |
