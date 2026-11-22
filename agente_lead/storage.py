"""Onde os leads ficam: Google Sheets (uso normal) ou CSV (testes locais)."""

from __future__ import annotations

import csv
import json
import logging
from datetime import date
from pathlib import Path
from typing import Protocol

from .messages import nome_exibicao
from .models import Lead
from .normalize import (exibir_telefone, formatar_cnpj, limpar_razao_social, link_whatsapp, nome_bonito,
                        normalizar_telefone, so_digitos)
from .scoring import eh_individual

log = logging.getLogger(__name__)

ABA = "Leads"
COLUNAS = [
    "Data", "Status", "Score", "Nome", "Tipo", "Cidade", "Telefone", "WhatsApp", "E-mail",
    "Abertura", "Porte", "CNPJ", "Razão social", "Endereço", "Por que este lead",
    "Mensagem sugerida", "Pesquisar na internet", "Fonte", "Observações",
]
COLUNA_CNPJ = COLUNAS.index("CNPJ")


def _pesquisa(lead: Lead) -> str:
    termos = f"{nome_exibicao(lead)} {lead.municipio.title()} TO".replace(" ", "+")
    return f"https://www.google.com/search?q={termos}"


def linha_da_planilha(lead: Lead, hoje: date) -> list[str]:
    telefones = [exibir_telefone(t) for t in lead.telefones]
    celular = next((t for t in lead.telefones if (normalizar_telefone(t) or ("", False))[1]), "")
    endereco = ", ".join(p for p in (lead.endereco, lead.bairro) if p)
    return [
        hoje.isoformat(),
        "Novo",
        str(lead.score),
        nome_exibicao(lead),
        "Contador individual" if eh_individual(lead) else "Escritório",
        lead.municipio.title(),
        " / ".join(telefones),
        link_whatsapp(celular) if celular else "",
        lead.email,
        lead.data_abertura.isoformat() if lead.data_abertura else "",
        lead.porte.title(),
        formatar_cnpj(lead.cnpj),
        nome_bonito(limpar_razao_social(lead.razao_social)),
        endereco.title(),
        "; ".join(lead.motivos),
        lead.mensagem,
        _pesquisa(lead),
        lead.fonte,
        "",
    ]


def _raizes(valores: list[str]) -> set[str]:
    return {so_digitos(v)[:8] for v in valores if len(so_digitos(v)) >= 8}


class Armazenamento(Protocol):
    def raizes_existentes(self) -> set[str]: ...
    def adicionar(self, linhas: list[list[str]]) -> None: ...


class PlanilhaGoogle:
    """Grava na aba 'Leads'. Cria a aba e o cabeçalho na primeira execução."""

    def __init__(self, planilha_id: str, credenciais_json: str) -> None:
        import gspread

        cliente = gspread.service_account_from_dict(json.loads(credenciais_json))
        planilha = cliente.open_by_key(planilha_id)
        try:
            self.aba = planilha.worksheet(ABA)
        except gspread.WorksheetNotFound:
            self.aba = planilha.add_worksheet(title=ABA, rows=1000, cols=len(COLUNAS))
            self.aba.append_row(COLUNAS, value_input_option="RAW")
            self.aba.freeze(rows=1)

    def raizes_existentes(self) -> set[str]:
        cabecalho = self.aba.row_values(1)
        indice = cabecalho.index("CNPJ") + 1 if "CNPJ" in cabecalho else COLUNA_CNPJ + 1
        return _raizes(self.aba.col_values(indice)[1:])

    def adicionar(self, linhas: list[list[str]]) -> None:
        # RAW: o texto entra como texto; nada vindo de fora vira fórmula na planilha.
        self.aba.append_rows(linhas, value_input_option="RAW")


class ArquivoCsv:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)

    def raizes_existentes(self) -> set[str]:
        if not self.caminho.exists():
            return set()
        with self.caminho.open(newline="", encoding="utf-8") as arquivo:
            return _raizes([linha.get("CNPJ", "") for linha in csv.DictReader(arquivo)])

    def adicionar(self, linhas: list[list[str]]) -> None:
        novo = not self.caminho.exists()
        with self.caminho.open("a", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            if novo:
                escritor.writerow(COLUNAS)
            escritor.writerows(linhas)
