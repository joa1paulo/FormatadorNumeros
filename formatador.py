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


def formatar_numero(bruto) -> Resultado:
    texto = str(bruto if bruto is not None else "").strip()
    if not texto:
        return Resultado("invalido", None, "vazio")

    # Excel em notação científica (5.5E+12): os dígitos já foram perdidos, não dá para recuperar
    if re.fullmatch(r"\d+(?:[.,]\d+)?[eE][+-]?\d+", texto):
        return Resultado("invalido", None, "notação científica (o Excel cortou os dígitos)")

    # número virou decimal na exportação (5521994833600.0)
    decimal = re.fullmatch(r"(\d+)[.,]0+", texto)
    if decimal:
        texto = decimal.group(1)

    # 1. remove tudo que não for dígito (parênteses, traços, espaços, "+")
    digitos = re.sub(r"[^0-9]", "", texto)
    if not digitos:
        return Resultado("invalido", None, "sem dígitos")

    # número de outro país (+1..., 0034...) nunca deve virar número brasileiro
    if (texto.startswith("+") and not digitos.startswith("55")) or (
        texto.startswith("00") and not digitos.startswith("0055")
    ):
        return Resultado("invalido", None, "código de país diferente de +55")

    digitos = digitos.lstrip("0")

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
        elif numero[0] in "2345":    # telefone fixo
            return Resultado("fixo", None, "telefone fixo")
        else:                        # começa em 0 ou 1: não existe
            return Resultado("invalido", None, "número inexistente")
    elif numero[0] != "9":           # 9 dígitos mas não começa com 9
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
        # Excel / exportações
        "5521994833600.0": ("ok", "+5521994833600"),
        "5521994833600,0": ("ok", "+5521994833600"),
        "5.5219948336E+12": ("invalido", None),
        '="5521994833600"': ("ok", "+5521994833600"),
        # países e prefixos
        "+1 415 555 2671": ("invalido", None),
        "0034 91 123 4567": ("invalido", None),
        "0055 34 99123-4567": ("ok", "+5534991234567"),
        # 8 dígitos que não existem
        "(21) 0123-4567": ("invalido", None),
        "(21) 1234-5678": ("invalido", None),
        # lixo
        "sem telefone": ("invalido", None),
        "   ": ("invalido", None),
        "34991234567 / 34988887777": ("invalido", None),
    }
    for entrada, (status, numero) in casos.items():
        r = formatar_numero(entrada)
        assert (r.status, r.numero) == (status, numero), (entrada, r)
    assert formatar_numero("").motivo == "vazio"
    assert formatar_numero("+1 415 555 2671").motivo == "código de país diferente de +55"
    print(f"{len(casos)} testes OK")


if __name__ == "__main__":
    _testes()