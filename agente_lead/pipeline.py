"""O fluxo do agente: buscar → filtrar repetidos → pontuar → completar contato → mensagem → gravar."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Protocol

from .config import Config
from .messages import Redator
from .models import Lead
from .scoring import pontuar
from .storage import Armazenamento, linha_da_planilha

log = logging.getLogger(__name__)


class Fonte(Protocol):
    def buscar(self, uf: str, cnae: str, municipio_ibge: str | None = None) -> Iterable[Lead]: ...


class Completador(Protocol):
    def completar(self, lead: Lead) -> None: ...


@dataclass
class Resultado:
    leads: list[Lead]
    candidatos_restantes: int


def _novos(leads: Iterable[Lead], ja_vistos: set[str]) -> list[Lead]:
    """Tira repetidos (mesma empresa = mesma raiz de CNPJ). Prefere a matriz à filial."""
    por_raiz: dict[str, Lead] = {}
    for lead in leads:
        if lead.raiz_cnpj in ja_vistos:
            continue
        atual = por_raiz.get(lead.raiz_cnpj)
        eh_matriz = lead.cnpj[8:12] == "0001"
        if atual is None or (eh_matriz and atual.cnpj[8:12] != "0001"):
            por_raiz[lead.raiz_cnpj] = lead
    return list(por_raiz.values())


def _ordenar(leads: list[Lead], prioritarias: set[str]) -> list[Lead]:
    # Primeiro as cidades prioritárias, depois a maior nota; CNPJ desempata de forma estável.
    return sorted(leads, key=lambda l: (l.codigo_municipio_ibge not in prioritarias, -l.score, l.cnpj))


def selecionar(config: Config, fonte: Fonte, ja_vistos: set[str], hoje: date) -> tuple[list[Lead], int]:
    """Escolhe os melhores candidatos novos. Só busca o estado todo se a cidade prioritária não bastar."""
    prioritarias = set(config.cidades_prioritarias_ibge)
    candidatos: list[Lead] = []
    for ibge in config.cidades_prioritarias_ibge:
        candidatos += fonte.buscar(config.uf, config.cnae, ibge)
    candidatos = _novos(candidatos, ja_vistos)
    log.info("Cidades prioritárias: %d candidatos novos", len(candidatos))

    if len(candidatos) < config.leads_por_dia:
        log.info("Poucos na cidade prioritária; buscando no estado todo (%s)", config.uf)
        do_estado = fonte.buscar(config.uf, config.cnae, None)
        candidatos = _novos(list(candidatos) + list(do_estado), ja_vistos)
        log.info("Estado todo: %d candidatos novos", len(candidatos))

    for lead in candidatos:
        pontuar(lead, prioritarias, hoje)
    candidatos = _ordenar(candidatos, prioritarias)
    escolhidos = candidatos[: config.leads_por_dia]
    return escolhidos, len(candidatos) - len(escolhidos)


def executar(config: Config, fonte: Fonte, completador: Completador | None, redator: Redator,
             armazenamento: Armazenamento | None, hoje: date) -> Resultado:
    ja_vistos = armazenamento.raizes_existentes() if armazenamento else set()
    log.info("Já estão na planilha: %d empresas", len(ja_vistos))

    escolhidos, restantes = selecionar(config, fonte, ja_vistos, hoje)
    prioritarias = set(config.cidades_prioritarias_ibge)
    for lead in escolhidos:
        if completador:
            completador.completar(lead)
        pontuar(lead, prioritarias, hoje)  # e-mail novo pode mudar a nota
        lead.mensagem = redator.escrever(lead, config, hoje)

    escolhidos = _ordenar(escolhidos, prioritarias)
    if armazenamento and escolhidos:
        armazenamento.adicionar([linha_da_planilha(lead, hoje) for lead in escolhidos])
    return Resultado(leads=escolhidos, candidatos_restantes=restantes)
