"""Estrutura de dados de um lead."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Lead:
    """Um escritório ou contador encontrado nos dados abertos do CNPJ."""

    cnpj: str  # só dígitos, 14 caracteres
    razao_social: str
    nome_fantasia: str
    natureza_juridica: str
    porte: str
    municipio: str
    codigo_municipio_ibge: str
    uf: str
    bairro: str
    endereco: str
    telefones: list[str] = field(default_factory=list)  # só dígitos, com DDD
    email: str = ""
    data_abertura: date | None = None
    fonte: str = "Receita Federal (via Minha Receita)"

    # Preenchidos depois pelo agente
    score: int = 0
    motivos: list[str] = field(default_factory=list)
    mensagem: str = ""

    @property
    def raiz_cnpj(self) -> str:
        """Os 8 primeiros dígitos identificam a empresa (matriz e filiais)."""
        return self.cnpj[:8]
