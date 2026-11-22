"""Configurações: o que não é segredo fica em config.toml; chaves ficam em variáveis de ambiente."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    uf: str = "TO"
    cnae: str = "6920601"  # Atividades de contabilidade
    cidades_prioritarias_ibge: list[str] = field(default_factory=lambda: ["1702109"])  # Araguaína
    leads_por_dia: int = 10

    seu_nome: str = ""
    produto: str = "uma ferramenta de cálculo para contadores"
    beneficio: str = ""
    convite: str = "Posso te mostrar em 10 minutos como funciona?"

    modelo_ia: str = "claude-opus-5-5"

    # Segredos (variáveis de ambiente)
    planilha_id: str = ""
    google_credenciais_json: str = ""
    anthropic_api_key: str = ""

    @classmethod
    def carregar(cls, caminho: str | Path = "config.toml") -> "Config":
        dados: dict = {}
        caminho = Path(caminho)
        if caminho.exists():
            with caminho.open("rb") as arquivo:
                dados = tomllib.load(arquivo)
        busca = dados.get("busca", {})
        mensagem = dados.get("mensagem", {})
        ia = dados.get("ia", {})
        padrao = cls()
        return cls(
            uf=busca.get("uf", padrao.uf),
            cnae=str(busca.get("cnae", padrao.cnae)),
            cidades_prioritarias_ibge=[str(c) for c in busca.get(
                "cidades_prioritarias_ibge", padrao.cidades_prioritarias_ibge)],
            leads_por_dia=int(os.environ.get("LEADS_POR_DIA") or busca.get("leads_por_dia", padrao.leads_por_dia)),
            seu_nome=mensagem.get("seu_nome", padrao.seu_nome),
            produto=mensagem.get("produto", padrao.produto),
            beneficio=mensagem.get("beneficio", padrao.beneficio),
            convite=mensagem.get("convite", padrao.convite),
            modelo_ia=ia.get("modelo", padrao.modelo_ia),
            planilha_id=os.environ.get("PLANILHA_ID", "").strip(),
            google_credenciais_json=os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip(),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", "").strip(),
        )
