"""Camada de serviço: junta processamento, mesclagem e exportação (sem depender do FastAPI)."""
import io
import zipfile

from exportar import gerar_arquivos
from mesclar import mesclar
from processador import Resumo, processar_csv


def executar(talvez: bytes, contatados: bytes | None = None, formato: str = "csv"):
    """Retorna (zip_em_bytes, estatisticas).

    talvez     -> lista a ser formatada (obrigatória)
    contatados -> lista de quem já foi contatado (opcional); é removida da lista anterior
    """
    resumo_talvez = processar_csv(talvez)
    resumo_contatados = processar_csv(contatados) if contatados else Resumo()

    resultado = mesclar(resumo_contatados, resumo_talvez)
    arquivos = gerar_arquivos(resultado, formato, incluir_mesclados=bool(contatados))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)

    # lista principal: novos + já contatados + fixos + inválidos + duplicados == total
    estatisticas = {
        "lista": {
            "total": resumo_talvez.total,
            "novos": len(resultado.novos),
            "ja_contatados_removidos": len(resultado.ja_contatados),
            "fixos": len(resumo_talvez.fixos),
            "invalidos": len(resumo_talvez.invalidos),
            "duplicados": resumo_talvez.duplicados,
            "mesclados": len(resultado.mesclados) if contatados else None,
        },
        "contatados": {
            "total": resumo_contatados.total,
            "validos": len(resumo_contatados.ok),
            "fixos": len(resumo_contatados.fixos),
            "invalidos": len(resumo_contatados.invalidos),
            "duplicados": resumo_contatados.duplicados,
        } if contatados else None,
    }
    return buffer.getvalue(), estatisticas


def _testes():
    contatados = b"Nome do Contato,WhatsApp do Contato,Etapa da Jornada\nLucia,5521994833600,Fez Contato\n"
    talvez = b"Telefone\n5521994833600\n(21) 98612-8098\n5521986128098\n(34) 3234-5678\n209083319713962\n"

    zip_bytes, est = executar(talvez, contatados, "txt")
    assert est["lista"] == {
        "total": 5, "novos": 1, "ja_contatados_removidos": 1,
        "fixos": 1, "invalidos": 1, "duplicados": 1, "mesclados": 2,
    }, est
    assert est["contatados"] == {
        "total": 1, "validos": 1, "fixos": 0, "invalidos": 0, "duplicados": 0,
    }, est
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        assert sorted(z.namelist()) == ["fixos.csv", "invalidos.csv", "mesclados.txt", "novos.txt"]
        assert z.read("novos.txt").decode() == "5521986128098\n"
        assert z.read("mesclados.txt").decode() == "5521994833600\n5521986128098\n"

    # sem o arquivo de contatados
    _, est = executar(talvez, None, "csv")
    assert est["lista"]["novos"] == 2 and est["lista"]["ja_contatados_removidos"] == 0
    assert est["contatados"] is None and est["lista"]["mesclados"] is None
    print("testes da etapa 5 (serviço) OK")


if __name__ == "__main__":
    _testes()