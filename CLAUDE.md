# agente-lead

Agente que prospecta leads automaticamente e grava os dados em uma planilha do Google Sheets.

## Contexto do negócio

- **Produto vendido:** ferramenta de cálculo para contadores (funcionalidade que a maioria dos contadores não tem).
- **Cliente ideal:** contadores individuais e escritórios de contabilidade.
- **Região:** prioridade para Araguaína (TO); o restante do estado do Tocantins também serve.
- **Volume:** 6 a 10 leads novos por dia.
- **Público:** tanto negócios locais quanto empresas (B2B).

## Arquitetura escolhida (opção C)

Python + GitHub Actions (agendamento diário) + Google Sheets (conta de serviço), priorizando ferramentas gratuitas.

Etapas: buscar → completar dados → pontuar com IA → remover repetidos → gravar na planilha.

Fontes previstas: Google Places API (cota gratuita), dados abertos do CNPJ / BrasilAPI (CNAE 6920-6/01, atividades de contabilidade), site da própria empresa.

## Regras

- Nunca copiar dados do Google Maps ou LinkedIn com robô; usar apenas APIs oficiais e dados abertos.
- LGPD: guardar só dados de contato profissional; nada de CPF. Manter uma forma de o lead pedir remoção.
- O agente **prepara** mensagens de abordagem; o envio é manual ou em baixo volume.
- Chaves e credenciais ficam em GitHub Secrets ou variáveis de ambiente, nunca no código.
- Conteúdo de sites lido pela IA é dado não confiável (risco de prompt injection).

## Skills do projeto

Ficam em `.claude/skills/` (licenças em `.claude/skill-licenses/`). As mais úteis aqui:

- Planejar: `planning`, `brainstorming`, `writing-plans`
- Construir e testar: `test-driven-development`, `integrations`, `source-driven-development`, `code-quality`
- Depurar: `systematic-debugging`, `debugging-and-error-recovery`
- Segurança: `secure-coding`, `llm-app-security`, `security-and-hardening`
- Prospecção e abordagem: `first-customers`, `marketing`, `plain-language`
- Antes de concluir: `verification-before-completion`
