"""Etapa 3: mesclagem das listas "já contatados" e "talvez não contatados".

Nada é copiado: o resultado é calculado em fluxo a partir dos dois resumos já processados.
"""
from itertools import chain

from processador import Resumo, processar_csv


class ResultadoMesclagem:
    def __init__(self, contatados: Resumo, talvez: Resumo):
        self.contatados = contatados
        self.talvez = talvez
        ja = contatados.ok
        self.n_ja_contatados = sum(1 for numero in talvez.ok if numero in ja)
        self.n_novos = len(talvez.ok) - self.n_ja_contatados
        self.n_mesclados = len(ja) + self.n_novos

    @property
    def duplicados(self) -> int:
        return self.contatados.duplicados + self.talvez.duplicados

    # ---- iteradores (usados na exportação; não geram listas na memória) ----
    def iter_novos(self):
        """(número, nome) de quem está na lista principal e ainda NÃO foi contatado."""
        ja = self.contatados.ok
        return ((numero, nome) for numero, nome in self.talvez.ok.items() if numero not in ja)

    def iter_ja_contatados(self):
        ja = self.contatados.ok
        return ((numero, nome) for numero, nome in self.talvez.ok.items() if numero in ja)

    def iter_mesclados(self):
        """União das duas listas: primeiro os já contatados, depois os novos, sem repetir."""
        nomes_talvez = self.talvez.ok
        for numero, nome in self.contatados.ok.items():
            yield numero, nome or nomes_talvez.get(numero, "")
        yield from self.iter_novos()

    def iter_fixos(self):
        return chain(self.contatados.fixos, self.talvez.fixos)

    def iter_invalidos(self):
        return chain(self.contatados.invalidos, self.talvez.invalidos)

    # ---- versões em lista, só para testes e arquivos pequenos ----
    @property
    def novos(self) -> list:
        return [{"nome": nome, "numero": numero} for numero, nome in self.iter_novos()]

    @property
    def ja_contatados(self) -> list:
        return [{"nome": nome, "numero": numero} for numero, nome in self.iter_ja_contatados()]

    @property
    def mesclados(self) -> list:
        return [{"nome": nome, "numero": numero} for numero, nome in self.iter_mesclados()]

    @property
    def fixos(self) -> list:
        return list(self.iter_fixos())

    @property
    def invalidos(self) -> list:
        return list(self.iter_invalidos())


def mesclar(contatados: Resumo, talvez: Resumo) -> ResultadoMesclagem:
    # o cruzamento é feito pelos números já formatados (E.164), não pelo texto original
    return ResultadoMesclagem(contatados, talvez)


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
    assert (r.n_novos, r.n_ja_contatados, r.n_mesclados) == (1, 1, 3)
    print("testes da etapa 3 OK")


if __name__ == "__main__":
    _testes()