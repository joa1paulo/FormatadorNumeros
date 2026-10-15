"""Etapa 1: formatação de números brasileiros para E.164."""
import re
from typing import NamedTuple

DDDS_VALIDOS = {
    *range(11, 20), 21, 22, 24, 27, 28, *range(31, 36), 37, 38,
    *range(41, 50), 51, 53, 54, 55, *range(61, 70), 71, 73, 74, 75,
    77, 79, *range(81, 90), *range(91, 100),
}


class Resultado(NamedTuple):
    status: str          # "ok" | "fixo" | "invalido"
    numero: str | None   # E.164 (+55...) quando status == "ok"; None nos demais
    motivo: str = ""


def formatar_numero(bruto: str) -> Resultado:
    # 1. remove tudo que não for dígito (parênteses, traços, espaços, "+")
    digitos = re.sub(r"\D", "", str(bruto or "")).lstrip("0")

    # 2. remove o código do país, se existir (55 + DDD + 8/9 dígitos = 12/13)
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]

    # 3. número nacional deve ter DDD + 8 ou 9 dígitos
    if len(digitos) not in (10, 11):
        return Resultado("invalido", None, "tamanho fora do padrão")

    ddd, numero = digitos[:2], digitos[2:]
    if int(ddd) not in DDDS_VALIDOS:
        return Resultado("invalido", None, "DDD inexistente")

    # 4. regra do 9
    if len(numero) == 8:
        if numero[0] in "6789":      # celular antigo: falta o 9
            numero = "9" + numero
        else:                         # começa em 2-5: telefone fixo
            return Resultado("fixo", None, "telefone fixo")
    elif numero[0] != "9":            # 9 dígitos mas não começa com 9
        return Resultado("invalido", None, "celular deve começar com 9")

    return Resultado("ok", f"+55{ddd}{numero}")


def _testes():
    casos = {
        "(34) 99123-4567": ("ok", "+5534991234567"),
        "34991234567": ("ok", "+5534991234567"),
        "+55 34 99123-4567": ("ok", "+5534991234567"),
        "5534991234567": ("ok", "+5534991234567"),
        "(34) 9123-4567": ("ok", "+5534991234567"),     # faltava o 9
        "034 9123 4567": ("ok", "+5534991234567"),      # zero à esquerda
        "(55) 99123-4567": ("ok", "+5555991234567"),    # DDD 55 (RS)
        "(34) 3234-5678": ("fixo", None),
        "(34) 99123-45": ("invalido", None),
        "(00) 99123-4567": ("invalido", None),
        "(34) 89123-4567": ("invalido", None),
        "": ("invalido", None),
    }
    for entrada, (status, numero) in casos.items():
        r = formatar_numero(entrada)
        assert (r.status, r.numero) == (status, numero), (entrada, r)
    print(f"{len(casos)} testes OK")


if __name__ == "__main__":
    _testes()