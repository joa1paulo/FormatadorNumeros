"""Etapa 4: exportação em CSV e TXT."""
import csv
import io

from mesclar import ResultadoMesclagem


def _numero(c: dict, com_mais: bool) -> str:
    n = c["numero"]
    return n if com_mais else n.lstrip("+")


def exportar_txt(contatos: list, com_mais: bool = False) -> str:
    """Um número por linha, sem o + (padrão)."""
    return "".join(_numero(c, com_mais) + "\n" for c in contatos)


def exportar_csv(contatos: list, com_mais: bool = False) -> str:
    """CSV com as colunas nome,numero."""
    saida = io.StringIO()
    w = csv.writer(saida, lineterminator="\n")
    w.writerow(["nome", "numero"])
    for c in contatos:
        w.writerow([c["nome"], _numero(c, com_mais)])
    return saida.getvalue()


def exportar_descartados_csv(itens: list) -> str:
    """CSV para fixos/inválidos: nome,original,motivo."""
    saida = io.StringIO()
    w = csv.writer(saida, lineterminator="\n")
    w.writerow(["nome", "original", "motivo"])
    for i in itens:
        w.writerow([i["nome"], i["original"], i["motivo"]])
    return saida.getvalue()


def gerar_arquivos(r: ResultadoMesclagem, formato: str = "csv", incluir_mesclados: bool = False) -> dict:
    """Retorna {nome_do_arquivo: conteúdo} pronto para download."""
    if formato not in ("csv", "txt"):
        raise ValueError("formato deve ser 'csv' ou 'txt'")
    exportar = exportar_csv if formato == "csv" else exportar_txt
    arquivos = {}
    if incluir_mesclados:  # união das duas listas (já contatados + novos)
        arquivos[f"mesclados.{formato}"] = exportar(r.mesclados)
    arquivos[f"novos.{formato}"] = exportar(r.novos)
    arquivos["fixos.csv"] = exportar_descartados_csv(r.fixos)
    arquivos["invalidos.csv"] = exportar_descartados_csv(r.invalidos)
    return arquivos


def _testes():
    contatos = [
        {"nome": "Lucia", "numero": "+5521994833600"},
        {"nome": "", "numero": "+5521970121596"},
    ]
    assert exportar_txt(contatos) == "5521994833600\n5521970121596\n"
    assert exportar_txt(contatos, com_mais=True).startswith("+55")
    assert exportar_csv(contatos) == "nome,numero\nLucia,5521994833600\n,5521970121596\n"

    r = ResultadoMesclagem(
        novos=contatos, ja_contatados=[], duplicados=0, mesclados=contatos,
        fixos=[{"nome": "Ana", "original": "(34) 3234-5678", "motivo": "telefone fixo"}],
        invalidos=[],
    )
    arquivos = gerar_arquivos(r, "txt")
    assert set(arquivos) == {"novos.txt", "fixos.csv", "invalidos.csv"}
    assert "telefone fixo" in arquivos["fixos.csv"]
    com_mescla = gerar_arquivos(r, "txt", incluir_mesclados=True)
    assert set(com_mescla) == {"mesclados.txt", "novos.txt", "fixos.csv", "invalidos.csv"}
    assert com_mescla["mesclados.txt"] == "5521994833600\n5521970121596\n"
    print("testes da etapa 4 OK")


if __name__ == "__main__":
    _testes()