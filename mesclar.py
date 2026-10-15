"""Etapa 3: mesclagem das listas "já contatados" e "talvez não contatados"."""
from dataclasses import dataclass, field

from processador import Resumo, processar_csv


@dataclass
class ResultadoMesclagem:
    novos: list            # números da lista "talvez" que ainda NÃO foram contatados
    ja_contatados: list    # números da lista "talvez" removidos por já terem sido contatados
    fixos: list            # fixos de ambas as listas (arquivo separado)
    invalidos: list        # inválidos de ambas as listas
    duplicados: int        # duplicados removidos dentro de cada lista
    mesclados: list = field(default_factory=list)  # união das duas listas, sem repetidos


def mesclar(contatados: Resumo, talvez: Resumo) -> ResultadoMesclagem:
    # o cruzamento é feito pelos números já formatados (E.164), não pelo texto original
    numeros_contatados = {c["numero"] for c in contatados.ok}

    novos, removidos = [], []
    for c in talvez.ok:
        (removidos if c["numero"] in numeros_contatados else novos).append(c)

    # união: primeiro os já contatados, depois os novos (sem repetir nenhum número).
    # Se o contato não tem nome na lista de contatados, aproveita o nome da outra lista.
    nomes_talvez = {c["numero"]: c["nome"] for c in talvez.ok}
    mesclados = [
        {**c, "nome": c["nome"] or nomes_talvez.get(c["numero"], "")}
        for c in contatados.ok
    ] + novos

    return ResultadoMesclagem(
        mesclados=mesclados,
        novos=novos,
        ja_contatados=removidos,
        fixos=contatados.fixos + talvez.fixos,
        invalidos=contatados.invalidos + talvez.invalidos,
        duplicados=contatados.duplicados + talvez.duplicados,
    )


def _testes():
    contatados = processar_csv(
        "Nome do Contato,WhatsApp do Contato,Etapa da Jornada\n"
        "Lucia,5521994833600,Fez Contato\n"
        "Ana Laura,5532988176797,Fez Contato\n"
    )
    talvez = processar_csv(
        "Telefone\n"
        "5521994833600\n"        # já contatado
        "(21) 94833-600\n"       # mesmo número sem o 9: vira duplicado do anterior
        "(21) 98612-8098\n"      # novo, formato diferente
        "5521986128098\n"        # duplicado do anterior
        "209083319713962\n"      # inválido
    )
    r = mesclar(contatados, talvez)
    assert [c["numero"] for c in r.novos] == ["+5521986128098"]
    assert [c["numero"] for c in r.ja_contatados] == ["+5521994833600"]
    assert r.duplicados == 2
    assert len(r.invalidos) == 1
    assert [(c["nome"], c["numero"]) for c in r.mesclados] == [
        ("Lucia", "+5521994833600"),
        ("Ana Laura", "+5532988176797"),
        ("", "+5521986128098"),
    ], r.mesclados
    print("testes da etapa 3 OK")


if __name__ == "__main__":
    _testes()