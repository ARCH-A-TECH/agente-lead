"""Testes com dados fictícios no formato real das APIs (sem internet)."""

from __future__ import annotations

from datetime import date

import pytest

from agente_lead.config import Config
from agente_lead.messages import OPT_OUT, RedatorModelo, garantir_regras, saudacao
from agente_lead.models import Lead
from agente_lead.normalize import exibir_telefone, limpar_razao_social, nome_bonito, normalizar_telefone
from agente_lead.pipeline import executar
from agente_lead.scoring import pontuar
from agente_lead.sources import CnpjWs, MinhaReceita, lead_da_receita
from agente_lead.storage import COLUNAS, ArquivoCsv, linha_da_planilha

HOJE = date(2026, 11, 22)
ARAGUAINA = "1702109"
PALMAS = "1721000"


def linha_receita(cnpj, municipio="ARAGUAINA", ibge=1702109, situacao=2, telefone="6392277054",
                  natureza="Sociedade Empresária Limitada", razao="ESCRITORIO TESTE LTDA",
                  fantasia="", abertura="2025-06-01"):
    return {
        "cnpj": cnpj, "uf": "TO", "municipio": municipio, "codigo_municipio_ibge": ibge,
        "situacao_cadastral": situacao, "razao_social": razao, "nome_fantasia": fantasia,
        "natureza_juridica": natureza, "porte": "MICRO EMPRESA", "bairro": "CENTRO",
        "descricao_tipo_de_logradouro": "RUA", "logradouro": "DAS FLORES", "numero": "10",
        "complemento": "", "ddd_telefone_1": telefone, "ddd_telefone_2": "", "email": None,
        "data_inicio_atividade": abertura,
    }


# --- normalização -------------------------------------------------------------

@pytest.mark.parametrize("bruto,esperado", [
    ("6392277054", ("63992277054", True)),    # celular antigo sem o 9
    ("63992277054", ("63992277054", True)),
    ("6332151501", ("6332151501", False)),    # fixo
    ("", None),
    ("123", None),
    ("556392277054", ("63992277054", True)),  # com código do país
])
def test_normalizar_telefone(bruto, esperado):
    assert normalizar_telefone(bruto) == esperado


def test_exibir_telefone():
    assert exibir_telefone("63992277054") == "(63) 99227-7054"
    assert exibir_telefone("6332151501") == "(63) 3215-1501"


def test_razao_social_sem_cpf_mascarado_nem_prefixo_de_cnpj():
    assert limpar_razao_social("REIJANE FRANCISCA LUZ DIAS ***28723***") == "REIJANE FRANCISCA LUZ DIAS"
    assert limpar_razao_social("64.145.809 MARIA RODRIGUES LOIOLA") == "MARIA RODRIGUES LOIOLA"


def test_nome_bonito():
    assert nome_bonito("ESCRITORIO DE CONTABILIDADE SILVA LTDA") == "Escritorio de Contabilidade Silva Ltda"


# --- fontes -------------------------------------------------------------------

def test_lead_da_receita_ignora_empresa_baixada():
    assert lead_da_receita(linha_receita("11111111000111", situacao=8)) is None


def test_lead_da_receita_converte_campos():
    lead = lead_da_receita(linha_receita("11111111000111"))
    assert lead.telefones == ["63992277054"]
    assert lead.codigo_municipio_ibge == ARAGUAINA
    assert lead.endereco == "RUA DAS FLORES, 10"
    assert lead.data_abertura == date(2025, 6, 1)


class HttpFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def get_json(self, url, params=None):
        self.chamadas.append((url, params))
        return self.respostas.pop(0)


def test_minha_receita_percorre_paginas_pelo_cursor():
    http = HttpFalso([
        {"data": [linha_receita("11111111000111")], "cursor": "abc"},
        {"data": [linha_receita("22222222000122")], "cursor": None},
    ])
    leads = list(MinhaReceita(http, dormir=lambda s: None).buscar("TO", "6920601", ARAGUAINA))
    assert [l.cnpj for l in leads] == ["11111111000111", "22222222000122"]
    assert http.chamadas[0][1]["municipio"] == ARAGUAINA
    assert http.chamadas[1][1]["cursor"] == "abc"


def test_cnpj_ws_completa_email_e_respeita_intervalo():
    http = HttpFalso([
        {"estabelecimento": {"email": "Contato@Exemplo.com", "ddd1": "63", "telefone1": "33334444"}},
        {"estabelecimento": {"email": None}},
    ])
    esperas = []
    ws = CnpjWs(http, intervalo=21, dormir=esperas.append, relogio=lambda: 100.0)
    a = lead_da_receita(linha_receita("11111111000111", telefone=""))
    ws.completar(a)
    ws.completar(lead_da_receita(linha_receita("22222222000122")))
    assert a.email == "contato@exemplo.com"
    assert a.telefones == ["6333334444"]
    assert esperas == [21]


# --- nota ---------------------------------------------------------------------

def test_lead_de_araguaina_com_celular_pontua_mais_que_palmas_sem_telefone():
    bom = lead_da_receita(linha_receita("11111111000111"))
    fraco = lead_da_receita(linha_receita("22222222000122", "PALMAS", 1721000, telefone="",
                                          abertura="2005-01-01"))
    pontuar(bom, {ARAGUAINA}, HOJE)
    pontuar(fraco, {ARAGUAINA}, HOJE)
    assert bom.score == 85  # 30 cidade + 25 celular + 15 escritório + 15 recente
    assert fraco.score == 20  # 15 escritório + 5 consolidado
    assert 0 <= fraco.score <= bom.score <= 100


# --- mensagem -----------------------------------------------------------------

def test_mensagem_modelo_tem_saida_e_saudacao_pelo_primeiro_nome():
    lead = lead_da_receita(linha_receita("11111111000111", natureza="Empresário (Individual)",
                                         razao="MARIA RODRIGUES ***55542***"))
    config = Config(seu_nome="Ana", beneficio="faz o cálculo X em segundos")
    texto = RedatorModelo().escrever(lead, config, HOJE)
    assert texto.startswith("Olá, Maria!")
    assert "Aqui é Ana." in texto
    assert texto.endswith(OPT_OUT)
    assert "55542" not in texto


def test_saudacao_de_escritorio_usa_nome_fantasia():
    lead = lead_da_receita(linha_receita("11111111000111", fantasia="IALY ASSESSORIA CONTABIL"))
    assert saudacao(lead) == "Olá, equipe da Ialy Assessoria Contabil!"


def test_garantir_regras_acrescenta_opt_out_e_corta_texto_longo():
    assert garantir_regras("Oi").endswith(OPT_OUT)
    assert len(garantir_regras("a" * 5000)) <= 900 + len(OPT_OUT) + 1


# --- fluxo completo -----------------------------------------------------------

class FonteFalsa:
    def __init__(self, por_municipio):
        self.por_municipio = por_municipio
        self.buscas = []

    def buscar(self, uf, cnae, municipio_ibge=None):
        self.buscas.append(municipio_ibge)
        if municipio_ibge:
            return [lead_da_receita(l) for l in self.por_municipio.get(municipio_ibge, [])]
        return [lead_da_receita(l) for linhas in self.por_municipio.values() for l in linhas]


def test_fluxo_prioriza_araguaina_tira_repetidos_e_completa_com_o_estado(tmp_path):
    fonte = FonteFalsa({
        ARAGUAINA: [
            linha_receita("11111111000111"),
            linha_receita("11111111000292"),  # filial da mesma empresa
            linha_receita("33333333000133", telefone=""),
            linha_receita("44444444000144"),  # já está na planilha
        ],
        PALMAS: [linha_receita(f"5555555{i}000155", "PALMAS", 1721000) for i in range(5)],
    })
    csv = ArquivoCsv(tmp_path / "leads.csv")
    csv.adicionar([["2026-11-01"] + [""] * (COLUNAS.index("CNPJ") - 1) + ["44.444.444/0001-44"]])

    config = Config(leads_por_dia=4)
    resultado = executar(config, fonte, None, RedatorModelo(), csv, HOJE)

    cnpjs = [l.cnpj for l in resultado.leads]
    assert cnpjs[:2] == ["11111111000111", "33333333000133"]  # Araguaína primeiro, matriz no lugar da filial
    assert all(c.startswith("5555555") for c in cnpjs[2:])
    assert "44444444000144" not in cnpjs
    assert fonte.buscas == [ARAGUAINA, None]
    assert resultado.candidatos_restantes == 3

    # Segunda execução não repete ninguém
    resultado2 = executar(config, fonte, None, RedatorModelo(), csv, HOJE)
    assert not set(cnpjs) & {l.cnpj for l in resultado2.leads}


def test_nao_busca_o_estado_quando_araguaina_basta():
    fonte = FonteFalsa({ARAGUAINA: [linha_receita(f"1111111{i}000111") for i in range(5)]})
    executar(Config(leads_por_dia=3), fonte, None, RedatorModelo(), None, HOJE)
    assert fonte.buscas == [ARAGUAINA]


def test_linha_da_planilha_tem_todas_as_colunas_e_whatsapp():
    lead = lead_da_receita(linha_receita("11111111000111"))
    pontuar(lead, {ARAGUAINA}, HOJE)
    linha = linha_da_planilha(lead, HOJE)
    assert len(linha) == len(COLUNAS)
    dados = dict(zip(COLUNAS, linha))
    assert dados["WhatsApp"] == "https://wa.me/5563992277054"
    assert dados["CNPJ"] == "11.111.111/0001-11"
    assert dados["Status"] == "Novo"
