"""Camada de serviço: junta processamento, mesclagem e exportação (sem depender do FastAPI)."""
import tempfile

from exportar import gerar_zip
from mesclar import mesclar
from processador import LimiteDeLinhas, Resumo, processar_csv

ZIP_EM_RAM_ATE = 8 * 1024 * 1024  # o .zip fica na RAM até 8 MB; acima disso vai para o disco


def executar(talvez, contatados=None, formato: str = "csv", max_linhas: int | None = None):
    """Retorna (arquivo_zip, estatisticas).

    talvez     -> lista a ser formatada (obrigatória)
    contatados -> lista de quem já foi contatado (opcional); é removida da lista anterior
    Ambos podem ser bytes ou arquivos abertos (lidos em fluxo). `arquivo_zip` é um arquivo
    temporário já posicionado no início: quem chamou deve fechá-lo depois de usar.
    max_linhas -> limite de linhas somando os dois arquivos (None = sem limite).
    """
    tem_contatados = contatados is not None
    restante = max_linhas
    try:
        resumo_contatados = Resumo()
        if tem_contatados:
            resumo_contatados = processar_csv(contatados, restante)
            if restante is not None:
                restante -= resumo_contatados.total
        resumo_talvez = processar_csv(talvez, restante)
    except LimiteDeLinhas:
        limite = f"{max_linhas:,}".replace(",", ".")
        raise ValueError(f"Os arquivos passam do limite de {limite} linhas por processamento "
                         "(somando os dois). Divida em partes menores.") from None

    resultado = mesclar(resumo_contatados, resumo_talvez)

    arquivo_zip = tempfile.SpooledTemporaryFile(max_size=ZIP_EM_RAM_ATE)
    try:
        gerar_zip(resultado, formato, tem_contatados, arquivo_zip)
    except BaseException:
        arquivo_zip.close()
        raise
    arquivo_zip.seek(0)

    # lista principal: novos + já contatados + fixos + inválidos + duplicados == total
    estatisticas = {
        "lista": {
            "total": resumo_talvez.total,
            "novos": resultado.n_novos,
            "ja_contatados_removidos": resultado.n_ja_contatados,
            "fixos": len(resumo_talvez.fixos),
            "invalidos": len(resumo_talvez.invalidos),
            "duplicados": resumo_talvez.duplicados,
            "mesclados": resultado.n_mesclados if tem_contatados else None,
        },
        "contatados": {
            "total": resumo_contatados.total,
            "validos": len(resumo_contatados.ok),
            "fixos": len(resumo_contatados.fixos),
            "invalidos": len(resumo_contatados.invalidos),
            "duplicados": resumo_contatados.duplicados,
        } if tem_contatados else None,
    }
    return arquivo_zip, estatisticas


def _testes():
    import io
    import zipfile

    contatados = b"Nome do Contato,WhatsApp do Contato,Etapa da Jornada\nLucia,5521994833600,Fez Contato\n"
    talvez = b"Telefone\n5521994833600\n(21) 98612-8098\n5521986128098\n(34) 3234-5678\n209083319713962\n"

    arquivo, est = executar(talvez, contatados, "txt")
    assert est["lista"] == {
        "total": 5, "novos": 1, "ja_contatados_removidos": 1,
        "fixos": 1, "invalidos": 1, "duplicados": 1, "mesclados": 2,
    }, est
    assert est["contatados"] == {
        "total": 1, "validos": 1, "fixos": 0, "invalidos": 0, "duplicados": 0,
    }, est
    with zipfile.ZipFile(arquivo) as z:
        assert sorted(z.namelist()) == ["fixos.csv", "invalidos.csv", "mesclados.txt", "novos.txt"]
        assert z.read("novos.txt").decode() == "5521986128098\n"
        assert z.read("mesclados.txt").decode() == "5521994833600\n5521986128098\n"
    arquivo.close()

    # sem o arquivo de contatados
    arquivo, est = executar(talvez, None, "csv")
    assert est["lista"]["novos"] == 2 and est["lista"]["ja_contatados_removidos"] == 0
    assert est["contatados"] is None and est["lista"]["mesclados"] is None
    arquivo.close()

    # arquivos "de verdade", como o upload do FastAPI (que fica em disco)
    with tempfile.SpooledTemporaryFile(max_size=10) as up_t, tempfile.SpooledTemporaryFile(max_size=10) as up_c:
        up_t.write(talvez); up_c.write(contatados)
        arquivo, est = executar(up_t, up_c, "csv")
        assert est["lista"]["novos"] == 1 and est["lista"]["mesclados"] == 2
        arquivo.close()

    # limite de linhas (somando os dois arquivos) protege a memória
    try:
        executar(talvez, contatados, "csv", max_linhas=3)
        raise AssertionError("deveria ter recusado")
    except ValueError as e:
        assert "limite de 3 linhas" in str(e), str(e)
    print("testes da etapa 5 (serviço) OK")


if __name__ == "__main__":
    _testes()