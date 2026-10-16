"""Etapa 4: exportação em CSV e TXT, escrita em FLUXO direto para dentro do .zip."""
import csv
import io
import zipfile


def _numero(numero: str, com_mais: bool) -> str:
    return numero if com_mais else numero.lstrip("+")


def escrever_numeros(saida, pares, formato: str, com_mais: bool = False) -> None:
    """saida: arquivo de texto. pares: iterável de (número, nome). TXT: um número por linha."""
    if formato == "txt":
        for numero, _ in pares:
            saida.write(_numero(numero, com_mais) + "\n")
    else:
        escritor = csv.writer(saida, lineterminator="\n")
        escritor.writerow(["nome", "numero"])
        for numero, nome in pares:
            escritor.writerow([nome, _numero(numero, com_mais)])


def escrever_descartados(saida, itens) -> None:
    """CSV para fixos/inválidos: nome,original,motivo."""
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(["nome", "original", "motivo"])
    for item in itens:
        escritor.writerow([item.nome, item.original, item.motivo])


def gerar_zip(resultado, formato: str, incluir_mesclados: bool, destino) -> None:
    """Escreve o .zip em `destino` (arquivo binário) sem montar os arquivos inteiros na memória."""
    if formato not in ("csv", "txt"):
        raise ValueError("formato deve ser 'csv' ou 'txt'")

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        def adicionar(nome, escrever):
            with z.open(nome, "w") as bruto:
                with io.TextIOWrapper(bruto, encoding="utf-8", newline="") as saida:
                    escrever(saida)

        if incluir_mesclados:  # união das duas listas (já contatados + novos)
            adicionar(f"mesclados.{formato}",
                      lambda s: escrever_numeros(s, resultado.iter_mesclados(), formato))
        adicionar(f"novos.{formato}", lambda s: escrever_numeros(s, resultado.iter_novos(), formato))
        adicionar("fixos.csv", lambda s: escrever_descartados(s, resultado.iter_fixos()))
        adicionar("invalidos.csv", lambda s: escrever_descartados(s, resultado.iter_invalidos()))


# ---- atalhos em texto, só para testes e listas pequenas ----
def exportar_txt(pares, com_mais: bool = False) -> str:
    saida = io.StringIO()
    escrever_numeros(saida, pares, "txt", com_mais)
    return saida.getvalue()


def exportar_csv(pares, com_mais: bool = False) -> str:
    saida = io.StringIO()
    escrever_numeros(saida, pares, "csv", com_mais)
    return saida.getvalue()


def _testes():
    from mesclar import mesclar
    from processador import processar_csv

    pares = [("+5521994833600", "Lucia"), ("+5521970121596", "")]
    assert exportar_txt(pares) == "5521994833600\n5521970121596\n"
    assert exportar_txt(pares, com_mais=True).startswith("+55")
    assert exportar_csv(pares) == "nome,numero\nLucia,5521994833600\n,5521970121596\n"

    contatados = processar_csv("Nome do Contato,WhatsApp do Contato\nLucia,5521994833600\n")
    talvez = processar_csv("Telefone\n5521994833600\n5521970121596\n(34) 3234-5678\nabc\n")
    r = mesclar(contatados, talvez)

    buf = io.BytesIO()
    gerar_zip(r, "txt", True, buf)
    with zipfile.ZipFile(buf) as z:
        assert z.namelist() == ["mesclados.txt", "novos.txt", "fixos.csv", "invalidos.csv"]
        assert z.read("mesclados.txt").decode() == "5521994833600\n5521970121596\n"
        assert z.read("novos.txt").decode() == "5521970121596\n"
        assert "telefone fixo" in z.read("fixos.csv").decode()
        assert "sem dígitos" in z.read("invalidos.csv").decode()

    buf = io.BytesIO()
    gerar_zip(r, "csv", False, buf)  # "somente processar": sem o arquivo mesclados
    with zipfile.ZipFile(buf) as z:
        assert z.namelist() == ["novos.csv", "fixos.csv", "invalidos.csv"]

    try:
        gerar_zip(r, "xml", False, io.BytesIO())
        raise AssertionError("deveria ter recusado")
    except ValueError:
        pass
    print("testes da etapa 4 OK")


if __name__ == "__main__":
    _testes()