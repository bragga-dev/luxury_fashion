"""
Converte os erros de validação do Ninja/Pydantic no formato estável da API:

    {"field": "email", "message": "Field required", "type": "missing"}

- `field` é o caminho do campo SEM o prefixo técnico do Ninja (`body.payload.`, `query.`), pronto
  pra casar com o nome do campo no formulário do front (`address.cep`, `items.0.quantity`).
  Erro que não é de um campo específico fica com `field=""`.
- Só `loc`, `msg` e `type` sobrevivem: `input` (o valor enviado, que pode ser senha/CPF) e `ctx`
  nunca voltam na resposta.
"""
from typing import Any, Iterable


def _field_from_loc(loc: Iterable[Any]) -> str:
    parts = [str(p) for p in loc]
    if not parts:
        return ""
    source, rest = parts[0], parts[1:]
    if source == "body" and rest:
        rest = rest[1:]
    return ".".join(rest)


def format_validation_errors(errors: Iterable[dict]) -> list[dict]:
    return [
        {
            "field": _field_from_loc(error.get("loc", ())),
            "message": str(error.get("msg", "")),
            "type": str(error.get("type", "")),
        }
        for error in errors
    ]