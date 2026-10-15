"""Etapa 2: leitura dos CSVs (dois estilos), formatação e remoção de duplicados."""
import csv
import io
from dataclasses import dataclass, field

from formatador import formatar_numero

NOMES_COLUNA_NUMERO = ("whatsapp", "telefone", "celular", "phone", "numero", "número")


@dataclass
class Resumo:
    total: int = 0
    duplicados: int = 0
    ok: list = field(default_factory=list)         # [{nome, numero, extras...}]
    fixos: list = field(default_factory=list)      # [{nome, original, motivo}]
    invalidos: list = field(default_factory=list)  # [{nome, original, motivo}]


def _achar_colunas(cabecalho: list[str]) -> tuple[int, int | None]:
    """Retorna (índice da coluna de número, índice da coluna de nome ou None)."""
    baixo = [c.strip().lower() for c in cabecalho]
    idx_num = next(
        (i for i, c in enumerate(baixo) if any(n in c for n in NOMES_COLUNA_NUMERO)),
        0,  # sem cabeçalho reconhecido: assume a primeira coluna
    )
    idx_nome = next((i for i, c in enumerate(baixo) if "nome" in c), None)
    return idx_num, idx_nome


def processar_csv(conteudo: str | bytes) -> Resumo:
    if isinstance(conteudo, bytes):
        conteudo = conteudo.decode("utf-8-sig")
    linhas = list(csv.reader(io.StringIO(conteudo)))
    resumo = Resumo()
    if not linhas:
        return resumo

    idx_num, idx_nome = _achar_colunas(linhas[0])
    vistos: set[str] = set()

    for linha in linhas[1:]:
        if not linha or not any(c.strip() for c in linha):
            continue  # ignora linhas vazias
        bruto = linha[idx_num] if idx_num < len(linha) else ""
        nome = linha[idx_nome].strip() if idx_nome is not None and idx_nome < len(linha) else ""
        resumo.total += 1

        r = formatar_numero(bruto)
        if r.status == "ok":
            if r.numero in vistos:
                resumo.duplicados += 1
                continue
            vistos.add(r.numero)
            resumo.ok.append({"nome": nome, "numero": r.numero})
        elif r.status == "fixo":
            resumo.fixos.append({"nome": nome, "original": bruto, "motivo": r.motivo})
        else:
            resumo.invalidos.append({"nome": nome, "original": bruto, "motivo": r.motivo})
    return resumo


def _testes():
    contatados = (
        "Nome do Contato,WhatsApp do Contato,Etapa da Jornada\n"
        "Lucia,5521994833600,Fez Contato\n"
        "Daniele ,5521978785757,Fez Contato\n"
        ",5521970121596,Fez Contato\n"
        "Lucia repetida,5521994833600,Fez Contato\n"
    )
    r = processar_csv(contatados)
    assert (r.total, len(r.ok), r.duplicados) == (4, 3, 1)
    assert r.ok[1]["nome"] == "Daniele"          # espaço removido
    assert r.ok[2]["nome"] == ""                 # nome vazio tolerado

    talvez = (
        "Telefone\n5521986128098\n5521973701889\n5521986128098\n"
        "209083319713962\n"
    )
    r = processar_csv(talvez)
    assert (r.total, len(r.ok), r.duplicados) == (4, 2, 1)
    assert len(r.invalidos) == 1                 # 15 dígitos, não é telefone
    assert r.invalidos[0]["motivo"] == "tamanho fora do padrão"
    print("testes da etapa 2 OK")


if __name__ == "__main__":
    _testes()