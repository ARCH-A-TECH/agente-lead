"""Nota de 0 a 100: quanto maior, melhor o lead para abordar primeiro."""

from __future__ import annotations

from datetime import date

from .models import Lead
from .normalize import normalizar_telefone


def eh_individual(lead: Lead) -> bool:
    return "individual" in lead.natureza_juridica.lower()


def tem_celular(lead: Lead) -> bool:
    return any((normalizar_telefone(t) or ("", False))[1] for t in lead.telefones)


def anos_de_abertura(lead: Lead, hoje: date) -> float | None:
    if not lead.data_abertura:
        return None
    return (hoje - lead.data_abertura).days / 365.25


def pontuar(lead: Lead, cidades_prioritarias: set[str], hoje: date) -> None:
    """Preenche lead.score e lead.motivos. As regras somam no máximo 100."""
    score, motivos = 0, []

    if lead.codigo_municipio_ibge in cidades_prioritarias:
        score += 30
        motivos.append(f"fica em {lead.municipio.title()} (cidade prioritária)")

    if tem_celular(lead):
        score += 25
        motivos.append("tem celular (dá para chamar no WhatsApp)")
    elif lead.telefones:
        score += 15
        motivos.append("tem telefone fixo")

    if lead.email:
        score += 10
        motivos.append("tem e-mail")

    if eh_individual(lead):
        score += 10
        motivos.append("contador individual (decide sozinho)")
    else:
        score += 15
        motivos.append("escritório (mais clientes, mais cálculos)")

    if lead.porte in ("EMPRESA DE PEQUENO PORTE", "DEMAIS"):
        score += 5
        motivos.append("porte maior que microempresa")

    anos = anos_de_abertura(lead, hoje)
    if anos is not None:
        if anos < 2:
            score += 15
            motivos.append("aberto há menos de 2 anos (ainda montando suas ferramentas)")
        elif anos <= 10:
            score += 10
            motivos.append(f"aberto há {int(anos)} anos")
        else:
            score += 5
            motivos.append(f"consolidado, aberto há {int(anos)} anos")

    lead.score = min(score, 100)
    lead.motivos = motivos
