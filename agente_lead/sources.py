"""Fontes de dados públicas e gratuitas.

- Minha Receita (minhareceita.org): busca empresas por UF, município e CNAE nos dados
  abertos do CNPJ da Receita Federal. Não traz e-mail.
- CNPJ.ws (publica.cnpj.ws): consulta um CNPJ por vez e traz e-mail e telefones.
  Plano público: 3 consultas por minuto.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Callable, Iterator

from .http import ClienteHTTP
from .models import Lead
from .normalize import normalizar_telefone, so_digitos

log = logging.getLogger(__name__)

SITUACAO_ATIVA = 2
MINHA_RECEITA_URL = "https://minhareceita.org/"
CNPJ_WS_URL = "https://publica.cnpj.ws/cnpj/"


def _data(valor: str | None) -> date | None:
    try:
        return date.fromisoformat(valor) if valor else None
    except ValueError:
        return None


def _endereco(linha: dict[str, Any]) -> str:
    partes = [
        " ".join(p for p in (linha.get("descricao_tipo_de_logradouro"), linha.get("logradouro")) if p),
        linha.get("numero") or "",
        linha.get("complemento") or "",
    ]
    return ", ".join(p.strip() for p in partes if p and p.strip())


def lead_da_receita(linha: dict[str, Any]) -> Lead | None:
    """Converte uma linha da Minha Receita em Lead. Ignora empresas que não estão ativas."""
    if linha.get("situacao_cadastral") != SITUACAO_ATIVA:
        return None
    telefones = []
    for campo in ("ddd_telefone_1", "ddd_telefone_2"):
        normalizado = normalizar_telefone(linha.get(campo))
        if normalizado and normalizado[0] not in telefones:
            telefones.append(normalizado[0])
    return Lead(
        cnpj=so_digitos(linha.get("cnpj")).zfill(14),
        razao_social=linha.get("razao_social") or "",
        nome_fantasia=(linha.get("nome_fantasia") or "").strip(),
        natureza_juridica=linha.get("natureza_juridica") or "",
        porte=linha.get("porte") or "",
        municipio=linha.get("municipio") or "",
        codigo_municipio_ibge=str(linha.get("codigo_municipio_ibge") or ""),
        uf=linha.get("uf") or "",
        bairro=(linha.get("bairro") or "").strip(),
        endereco=_endereco(linha),
        telefones=telefones,
        email=(linha.get("email") or "").strip().lower(),
        data_abertura=_data(linha.get("data_inicio_atividade")),
    )


class MinhaReceita:
    def __init__(self, http: ClienteHTTP, pausa_entre_paginas: float = 5.0,
                 dormir: Callable[[float], None] = time.sleep) -> None:
        self.http = http
        self.pausa = pausa_entre_paginas
        self.dormir = dormir

    def buscar(self, uf: str, cnae: str, municipio_ibge: str | None = None,
               por_pagina: int = 200) -> Iterator[Lead]:
        """Percorre todas as páginas da busca e devolve só as empresas ativas."""
        cursor = None
        while True:
            params = {"uf": uf, "cnae_fiscal": cnae, "limit": str(por_pagina)}
            if municipio_ibge:
                params["municipio"] = municipio_ibge
            if cursor:
                params["cursor"] = cursor
            pagina = self.http.get_json(MINHA_RECEITA_URL, params) or {}
            linhas = pagina.get("data") or []
            for linha in linhas:
                lead = lead_da_receita(linha)
                if lead:
                    yield lead
            cursor = pagina.get("cursor")
            if not cursor or not linhas:
                return
            self.dormir(self.pausa)


class CnpjWs:
    """Completa e-mail e telefones de um CNPJ. Respeita o limite de 3 consultas/minuto."""

    def __init__(self, http: ClienteHTTP, intervalo: float = 21.0,
                 dormir: Callable[[float], None] = time.sleep,
                 relogio: Callable[[], float] = time.monotonic) -> None:
        self.http = http
        self.intervalo = intervalo
        self.dormir = dormir
        self.relogio = relogio
        self._ultima: float | None = None

    def completar(self, lead: Lead) -> None:
        if self._ultima is not None:
            falta = self.intervalo - (self.relogio() - self._ultima)
            if falta > 0:
                self.dormir(falta)
        try:
            dados = self.http.get_json(CNPJ_WS_URL + lead.cnpj)
        except Exception as erro:  # um lead sem e-mail não deve parar o agente
            log.warning("CNPJ.ws falhou para %s: %s", lead.cnpj, erro)
            return
        finally:
            self._ultima = self.relogio()
        estab = (dados or {}).get("estabelecimento") or {}
        email = (estab.get("email") or "").strip().lower()
        if email and "@" in email:
            lead.email = email
        for ddd_campo, tel_campo in (("ddd1", "telefone1"), ("ddd2", "telefone2")):
            normalizado = normalizar_telefone(f"{estab.get(ddd_campo) or ''}{estab.get(tel_campo) or ''}")
            if normalizado and normalizado[0] not in lead.telefones:
                lead.telefones.append(normalizado[0])
