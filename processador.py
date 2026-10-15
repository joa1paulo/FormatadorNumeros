"""Etapa 2: leitura de CSV e XLSX (vários estilos), formatação e remoção de duplicados."""
import csv
import io
from dataclasses import dataclass, field

from formatador import formatar_numero

# palavra encontrada no cabeçalho -> prioridade (menor = preferida)
PALAVRAS_NUMERO = [
    ("whatsapp", 0), ("celular", 1),
    ("telefone", 2), ("phone", 2), ("fone", 2),
    ("numero", 3), ("número", 3),
]
LINHAS_AMOSTRA = 200


@dataclass
class Resumo:
    total: int = 0
    duplicados: int = 0
    ok: list = field(default_factory=list)         # [{nome, numero}]
    fixos: list = field(default_factory=list)      # [{nome, original, motivo}]
    invalidos: list = field(default_factory=list)  # [{nome, original, motivo}]


@dataclass
class Analise:
    formato: str           # "csv" ou "xlsx"
    detalhe: str           # csv: o separador; xlsx: o nome da aba lida
    tem_cabecalho: bool
    cabecalho: list
    dados: list            # linhas de dados (sem linhas vazias)
    idx_num: int           # coluna lida como número
    idx_nome: int | None   # coluna lida como nome (None se não houver)
    ncols: int


def detectar_delimitador(texto: str) -> str:
    """Descobre o separador pela 1ª linha: vírgula, ponto e vírgula ou tabulação.
    Ignora separadores dentro de aspas. Sem nenhum separador, assume vírgula."""
    linha = next((l for l in texto.splitlines() if l.strip()), "")
    contagem = {",": 0, ";": 0, "\t": 0}
    entre_aspas = False
    for ch in linha:
        if ch == '"':
            entre_aspas = not entre_aspas
        elif not entre_aspas and ch in contagem:
            contagem[ch] += 1
    melhor = max(contagem, key=contagem.get)
    return melhor if contagem[melhor] > 0 else ","


def _prioridade(cabecalho: str) -> int | None:
    c = cabecalho.strip().lower()
    if c in ("tel", "tel."):
        return 2
    for palavra, prioridade in PALAVRAS_NUMERO:
        if palavra in c:
            return prioridade
    return None


def _decodificar(conteudo: str | bytes) -> str:
    if isinstance(conteudo, str):
        return conteudo.lstrip("\ufeff")
    if conteudo[:2] in (b"\xff\xfe", b"\xfe\xff"):  # "Texto Unicode" do Excel (UTF-16)
        return conteudo.decode("utf-16")
    try:
        return conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:  # CSV salvo pelo Excel em português costuma ser cp1252
        return conteudo.decode("cp1252", errors="replace")


def _texto_celula(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))  # 5521994833600.0 -> 5521994833600
    return str(v)


def _linhas_xlsx(conteudo: bytes):
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ValueError("Leitura de .xlsx indisponível neste servidor (falta instalar o openpyxl).")
    try:
        wb = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
        aba = wb.worksheets[0]  # primeira aba da planilha
        linhas = [[_texto_celula(c) for c in linha] for linha in aba.iter_rows(values_only=True)]
        nome_aba = aba.title
        wb.close()
    except Exception:
        raise ValueError("Não foi possível abrir o .xlsx (arquivo corrompido ou protegido por senha).")
    return linhas, "xlsx", nome_aba


def _ler_linhas(conteudo: str | bytes):
    """Devolve (linhas, formato, detalhe). Aceita CSV (, ; tab) e XLSX; recusa o resto com mensagem clara."""
    if isinstance(conteudo, bytes):
        if conteudo.startswith(b"PK\x03\x04"):  # .xlsx é um zip
            return _linhas_xlsx(conteudo)
        if conteudo.startswith(b"\xd0\xcf\x11\xe0"):  # .xls antigo ou arquivo protegido por senha
            raise ValueError("Arquivo .xls antigo ou protegido por senha. Salve como .xlsx ou .csv e envie de novo.")
        if b"\x00" in conteudo[:4096] and conteudo[:2] not in (b"\xff\xfe", b"\xfe\xff"):
            raise ValueError("Formato de arquivo não suportado. Envie um arquivo .csv ou .xlsx.")
    texto = _decodificar(conteudo)
    delimitador = detectar_delimitador(texto)
    return list(csv.reader(io.StringIO(texto), delimiter=delimitador)), "csv", delimitador


def analisar(conteudo: str | bytes) -> Analise | None:
    """Descobre separador, se há cabeçalho e quais colunas são número e nome."""
    linhas_brutas, formato, detalhe = _ler_linhas(conteudo)
    linhas = [l for l in linhas_brutas if l and any(c.strip() for c in l)]
    if not linhas:
        return None

    primeira = linhas[0]
    tem_palavra = any(_prioridade(c) is not None for c in primeira)
    parece_dado = any(formatar_numero(c).status == "ok" for c in primeira)
    tem_cabecalho = tem_palavra or not parece_dado  # lista só com números não tem cabeçalho

    cabecalho = primeira if tem_cabecalho else []
    dados = linhas[1:] if tem_cabecalho else linhas
    amostra = dados[:LINHAS_AMOSTRA]
    ncols = max(len(l) for l in linhas[: LINHAS_AMOSTRA + 1])

    def validos(i: int) -> int:  # quantos números válidos a coluna tem na amostra
        return sum(1 for l in amostra if i < len(l) and formatar_numero(l[i]).status == "ok")

    melhor_por_conteudo = max(range(ncols), key=lambda i: (validos(i), -i))
    candidatas = [(i, _prioridade(c)) for i, c in enumerate(cabecalho) if _prioridade(c) is not None]
    if candidatas:
        # cabeçalho manda (WhatsApp > Celular > Telefone > Número); empate: mais válidos, depois a da esquerda
        idx_num = min(candidatas, key=lambda t: (t[1], -validos(t[0]), t[0]))[0]
        # coluna escolhida sem nenhum número válido, mas outra tem: usa a que tem
        if validos(idx_num) == 0 and validos(melhor_por_conteudo) > 0:
            idx_num = melhor_por_conteudo
    else:
        idx_num = melhor_por_conteudo  # cabeçalho não ajuda (ex.: "ID,Contato"): decide pelo conteúdo

    idx_nome = None
    if tem_cabecalho:
        baixo = [c.strip().lower() for c in cabecalho]
        idx_nome = next((i for i, c in enumerate(baixo) if c.startswith("nome")), None)
        if idx_nome is None:
            idx_nome = next((i for i, c in enumerate(baixo) if "nome" in c and "sobrenome" not in c), None)
        if idx_nome == idx_num:
            idx_nome = None

    return Analise(formato, detalhe, tem_cabecalho, cabecalho, dados, idx_num, idx_nome, ncols)


def processar_csv(conteudo: str | bytes) -> Resumo:
    resumo = Resumo()
    a = analisar(conteudo)
    if a is None:
        return resumo

    posicao: dict[str, int] = {}  # número -> posição em resumo.ok
    for linha in a.dados:
        bruto = linha[a.idx_num] if a.idx_num < len(linha) else ""
        nome = linha[a.idx_nome].strip() if a.idx_nome is not None and a.idx_nome < len(linha) else ""
        resumo.total += 1

        r = formatar_numero(bruto)
        if r.status == "ok":
            if r.numero in posicao:
                resumo.duplicados += 1
                existente = resumo.ok[posicao[r.numero]]
                if not existente["nome"] and nome:  # aproveita o nome da linha repetida
                    existente["nome"] = nome
                continue
            posicao[r.numero] = len(resumo.ok)
            resumo.ok.append({"nome": nome, "numero": r.numero})
        elif r.status == "fixo":
            resumo.fixos.append({"nome": nome, "original": bruto, "motivo": r.motivo})
        else:
            resumo.invalidos.append({"nome": nome, "original": bruto, "motivo": r.motivo})
    return resumo


def previa_csv(conteudo: str | bytes, n: int = 8) -> dict:
    """Dados para o preview da tela: mostra exatamente como o sistema vai ler o arquivo."""
    a = analisar(conteudo)
    if a is None:
        return {"vazio": True}
    ncols = max([a.ncols, len(a.cabecalho)])
    cabecalho = a.cabecalho if a.tem_cabecalho else []
    cabecalho = [*cabecalho, *[f"Coluna {i + 1}" for i in range(len(cabecalho), ncols)]]
    linhas = [[*l, *[""] * (ncols - len(l))] for l in a.dados[:n]]
    return {
        "vazio": False,
        "formato": a.formato,
        "delimitador": a.detalhe if a.formato == "csv" else "",
        "aba": a.detalhe if a.formato == "xlsx" else "",
        "tem_cabecalho": a.tem_cabecalho,
        "cabecalho": cabecalho,
        "linhas": linhas,
        "idx_numero": a.idx_num,
        "total_linhas": len(a.dados),
    }


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
    assert r.ok[0]["nome"] == "Lucia"            # repetido não troca um nome já existente

    talvez = (
        "Telefone\n5521986128098\n5521973701889\n5521986128098\n"
        "209083319713962\n"
    )
    r = processar_csv(talvez)
    assert (r.total, len(r.ok), r.duplicados) == (4, 2, 1)
    assert len(r.invalidos) == 1                 # 15 dígitos, não é telefone
    assert r.invalidos[0]["motivo"] == "tamanho fora do padrão"

    # separador ponto e vírgula (Excel em português), com vírgula dentro de aspas
    ponto_virgula = (
        'Nome do Contato;WhatsApp do Contato;Etapa\n'
        '"Silva, João";5521994833600;Fez Contato\n'
        'Ana;(34) 99123-4567;Fez Contato\n'
    )
    r = processar_csv(ponto_virgula)
    assert [(c["nome"], c["numero"]) for c in r.ok] == [
        ("Silva, João", "+5521994833600"), ("Ana", "+5534991234567"),
    ], r.ok
    assert detectar_delimitador(ponto_virgula) == ";"

    # tabulação, coluna única (sem separador) e vírgula continuam funcionando
    assert processar_csv("Nome\tTelefone\nLia\t5521986128098\n").ok[0]["numero"] == "+5521986128098"
    assert processar_csv("Telefone\n5521986128098\n").ok[0]["numero"] == "+5521986128098"
    assert detectar_delimitador("a,b,c\n1;2;3") == ","

    # arquivo salvo pelo Excel (cp1252) com acento
    r = processar_csv("Nome;Telefone\nJosé;5521986128098\n".encode("cp1252"))
    assert r.ok[0]["nome"] == "José"

    # lista só com números, SEM cabeçalho: nenhuma linha pode ser perdida
    r = processar_csv("5521994833600\n5521986128098\n5532988176797\n")
    assert (r.total, len(r.ok)) == (3, 3), r

    # várias colunas: só a do número é usada
    ok = ["+5521994833600", "+5521986128098"]
    r = processar_csv("Número do Pedido,Telefone\n1001,5521994833600\n1002,5521986128098\n")
    assert [c["numero"] for c in r.ok] == ok
    r = processar_csv("Telefone Fixo,WhatsApp\n(34) 3234-5678,5521994833600\n")
    assert [c["numero"] for c in r.ok] == ["+5521994833600"] and not r.fixos
    r = processar_csv("ID,Contato\n1,5521994833600\n2,5521986128098\n")  # sem palavra-chave
    assert [c["numero"] for c in r.ok] == ok
    r = processar_csv("Telefone,Celular\n5521994833600,\n5521986128098,\n")  # Celular vazio
    assert [c["numero"] for c in r.ok] == ok
    r = processar_csv("Sobrenome,Nome,Tel\nSilva,Ana,5521994833600\n")
    assert (r.ok[0]["nome"], r.ok[0]["numero"]) == ("Ana", "+5521994833600")

    # duplicado aproveita o nome da linha repetida; célula vazia é motivo "vazio"
    r = processar_csv("Nome,Telefone\n,5521994833600\nLucia,5521994833600\n")
    assert r.ok == [{"nome": "Lucia", "numero": "+5521994833600"}] and r.duplicados == 1
    r = processar_csv("Nome,Telefone\nMaria,\nJoão,5521994833600\n")
    assert r.invalidos[0]["motivo"] == "vazio" and len(r.ok) == 1

    # arquivo vazio / só cabeçalho não quebram
    assert processar_csv("").total == 0 and processar_csv("Telefone\n").total == 0

    # preview mostra exatamente como o arquivo será lido
    d = previa_csv("5521994833600\n5521986128098\n")
    assert (d["tem_cabecalho"], d["cabecalho"], d["total_linhas"]) == (False, ["Coluna 1"], 2)
    d = previa_csv("Nome;WhatsApp\nAna;5521994833600\n")
    assert (d["delimitador"], d["idx_numero"], d["cabecalho"]) == (";", 1, ["Nome", "WhatsApp"])
    assert previa_csv("")["vazio"] is True

    # ---- planilhas .xlsx (o cliente enviou uma com 5 colunas) ----
    from openpyxl import Workbook

    def xlsx(linhas, abas_extras=False):
        wb = Workbook()
        ws = wb.active
        ws.title = "Contatos"
        for l in linhas:
            ws.append(l)
        if abas_extras:
            wb.create_sheet("Outra").append(["lixo", "lixo"])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    planilha = xlsx([
        ["Nome", "Email", "Telefone", "Cidade", "Etapa"],
        ["Ana", "ana@x.com", 5521994833600, "Rio", "Fez Contato"],         # número como inteiro
        ["Bia", "bia@x.com", "(21) 98612-8098", "Niterói", "Novo"],        # número como texto
        ["Caio", "caio@x.com", 5521986128098.0, "Rio", "Novo"],            # decimal: repete a Bia
        ["Duda", "duda@x.com", "(34) 3234-5678", "Uberlândia", "Novo"],    # fixo
        ["Eli", "eli@x.com", None, "SP", "Novo"],                          # célula vazia
    ], abas_extras=True)
    r = processar_csv(planilha)
    assert [(c["nome"], c["numero"]) for c in r.ok] == [("Ana", "+5521994833600"), ("Bia", "+5521986128098")], r.ok
    assert (r.total, r.duplicados, len(r.fixos), len(r.invalidos)) == (5, 1, 1, 1), r
    d = previa_csv(planilha)
    assert (d["formato"], d["aba"], d["idx_numero"], len(d["cabecalho"])) == ("xlsx", "Contatos", 2, 5), d

    # xlsx sem cabeçalho e no estilo "já contatados"
    assert len(processar_csv(xlsx([[5521994833600], [5521986128098]])).ok) == 2
    c = processar_csv(xlsx([["Nome do Contato", "WhatsApp do Contato", "Etapa da Jornada"],
                            ["Lucia", 5521994833600, "Fez Contato"]]))
    assert c.ok == [{"nome": "Lucia", "numero": "+5521994833600"}]

    # formatos que não dá para ler recebem mensagem clara (e não derrubam o servidor)
    for ruim, trecho in [
        (b"\xd0\xcf\x11\xe0" + b"x" * 50, ".xls antigo"),
        (b"PK\x03\x04 isto nao e uma planilha", "Não foi possível abrir"),
        (b"%PDF-1.4\x00\x01\x02 binario", "não suportado"),
    ]:
        try:
            processar_csv(ruim)
            raise AssertionError("deveria ter recusado")
        except ValueError as e:
            assert trecho in str(e), (trecho, str(e))

    # CSV em UTF-16 ("Texto Unicode" do Excel) também funciona
    utf16 = "Nome\tTelefone\nAna\t5521994833600\n".encode("utf-16")
    assert processar_csv(utf16).ok[0]["numero"] == "+5521994833600"
    print("testes da etapa 2 OK")


if __name__ == "__main__":
    _testes()