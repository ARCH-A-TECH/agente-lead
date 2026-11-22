"""Limpeza e formatação de dados: nomes, telefones, CNPJ."""

from __future__ import annotations

import re

_CPF_MASCARADO = re.compile(r"\s*\**\d{3,}\**\s*$")  # ex.: "FULANO DE TAL ***28723***"
_PREFIXO_CNPJ = re.compile(r"^\d{2}\.\d{3}\.\d{3}\s+")  # ex.: "64.145.809 MARIA ..."
_PALAVRAS_MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "em"}
_SIGLAS = {"ltda": "Ltda", "me": "ME", "epp": "EPP", "eireli": "Eireli", "s/s": "S/S", "ss": "SS"}


def so_digitos(valor: str | None) -> str:
    return re.sub(r"\D", "", valor or "")


def formatar_cnpj(cnpj: str) -> str:
    d = so_digitos(cnpj).zfill(14)
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def limpar_razao_social(razao: str) -> str:
    """Remove pedaços de CPF mascarado e o prefixo de CNPJ que a Receita põe em MEIs.

    Não guardamos CPF de ninguém (LGPD), nem mascarado.
    """
    texto = _PREFIXO_CNPJ.sub("", (razao or "").strip())
    texto = _CPF_MASCARADO.sub("", texto)
    return texto.strip()


def nome_bonito(texto: str) -> str:
    """'ESCRITORIO DE CONTABILIDADE SILVA LTDA' -> 'Escritorio de Contabilidade Silva Ltda'."""
    palavras = []
    for i, palavra in enumerate((texto or "").lower().split()):
        if palavra in _SIGLAS:
            palavras.append(_SIGLAS[palavra])
        elif i > 0 and palavra in _PALAVRAS_MINUSCULAS:
            palavras.append(palavra)
        else:
            palavras.append(palavra[:1].upper() + palavra[1:])
    return " ".join(palavras)


def normalizar_telefone(bruto: str | None) -> tuple[str, bool] | None:
    """Devolve (telefone só com dígitos e DDD, é_celular) ou None se inválido.

    A Receita guarda muitos celulares antigos sem o 9 na frente (8 dígitos começando
    com 6, 7, 8 ou 9). Nesses casos o 9 é acrescentado. Fixos começam com 2 a 5.
    """
    d = so_digitos(bruto)
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    if d.startswith("0"):
        d = d.lstrip("0")
    if len(d) == 10:
        ddd, numero = d[:2], d[2:]
        if numero[0] in "6789":
            return ddd + "9" + numero, True
        if numero[0] in "2345":
            return d, False
        return None
    if len(d) == 11 and d[2] == "9":
        return d, True
    return None


def exibir_telefone(telefone: str) -> str:
    """'63992277054' -> '(63) 99227-7054'."""
    ddd, numero = telefone[:2], telefone[2:]
    return f"({ddd}) {numero[:-4]}-{numero[-4:]}"


def link_whatsapp(telefone: str) -> str:
    return f"https://wa.me/55{telefone}"
