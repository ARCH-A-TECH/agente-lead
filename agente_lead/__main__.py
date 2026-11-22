"""Uso: python -m agente_lead [--teste] [--csv arquivo.csv] [--limite N]"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta, timezone

from .config import Config
from .http import ClienteHTTP
from .messages import criar_redator, nome_exibicao
from .pipeline import executar
from .sources import CnpjWs, MinhaReceita
from .storage import ArquivoCsv, PlanilhaGoogle

FUSO_TOCANTINS = timezone(timedelta(hours=-3))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agente de prospecção de contadores no Tocantins")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--teste", action="store_true", help="mostra os leads sem gravar em lugar nenhum")
    parser.add_argument("--csv", help="grava num arquivo CSV em vez do Google Sheets")
    parser.add_argument("--limite", type=int, help="quantos leads buscar hoje")
    parser.add_argument("--sem-email", action="store_true", help="não consulta a CNPJ.ws (mais rápido)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("agente_lead")

    config = Config.carregar(args.config)
    if args.limite:
        config.leads_por_dia = args.limite

    if args.teste:
        armazenamento = None
    elif args.csv:
        armazenamento = ArquivoCsv(args.csv)
    elif config.planilha_id and config.google_credenciais_json:
        armazenamento = PlanilhaGoogle(config.planilha_id, config.google_credenciais_json)
    else:
        log.error("Faltam PLANILHA_ID e GOOGLE_SERVICE_ACCOUNT_JSON. Use --csv ou --teste para rodar sem planilha.")
        return 2

    http = ClienteHTTP()
    hoje = datetime.now(FUSO_TOCANTINS).date()
    resultado = executar(
        config=config,
        fonte=MinhaReceita(http),
        completador=None if args.sem_email else CnpjWs(http),
        redator=criar_redator(config),
        armazenamento=armazenamento,
        hoje=hoje,
    )

    for lead in resultado.leads:
        print(f"[{lead.score:3d}] {nome_exibicao(lead)} — {lead.municipio.title()} — "
              f"tel: {', '.join(lead.telefones) or '-'} — e-mail: {lead.email or '-'}")
        if args.teste:
            print(f"      {lead.mensagem}\n")
    log.info("%d leads novos hoje; ainda restam %d candidatos na fila",
             len(resultado.leads), resultado.candidatos_restantes)
    if not resultado.leads:
        log.warning("Nenhum lead novo encontrado. A base pode ter se esgotado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
