"""Cliente HTTP com espera automática quando a API pede para ir mais devagar."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

import requests

log = logging.getLogger(__name__)

# Identificador genérico: alguns serviços bloqueiam o padrão do Python.
USER_AGENT = "agente-lead/0.1"


class ErroHTTP(RuntimeError):
    pass


class ClienteHTTP:
    def __init__(
        self,
        tentativas: int = 5,
        espera_limite: float = 65.0,
        timeout: float = 90.0,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self.sessao = requests.Session()
        self.sessao.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self.tentativas = tentativas
        self.espera_limite = espera_limite
        self.timeout = timeout
        self.dormir = dormir

    def get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        ultima_falha = ""
        for tentativa in range(1, self.tentativas + 1):
            try:
                resposta = self.sessao.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as erro:
                ultima_falha = f"falha de rede: {erro}"
                log.warning("%s (tentativa %d/%d)", ultima_falha, tentativa, self.tentativas)
                self.dormir(min(5 * tentativa, self.espera_limite))
                continue

            if resposta.status_code == 200:
                return resposta.json()
            if resposta.status_code == 404:
                return None
            if resposta.status_code == 429 or resposta.status_code >= 500:
                espera = self._espera(resposta, tentativa)
                ultima_falha = f"HTTP {resposta.status_code}"
                log.info("%s em %s; aguardando %.0fs", ultima_falha, url, espera)
                self.dormir(espera)
                continue
            raise ErroHTTP(f"HTTP {resposta.status_code} em {url}: {resposta.text[:200]}")
        raise ErroHTTP(f"desisti de {url} após {self.tentativas} tentativas ({ultima_falha})")

    def _espera(self, resposta: requests.Response, tentativa: int) -> float:
        retry_after = resposta.headers.get("Retry-After", "")
        if retry_after.isdigit():
            return min(float(retry_after) + 1, self.espera_limite)
        if resposta.status_code == 429:
            return self.espera_limite  # Minha Receita e CNPJ.ws liberam em ~1 minuto
        return min(5.0 * tentativa, self.espera_limite)
