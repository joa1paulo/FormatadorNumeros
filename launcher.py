"""Ponto de entrada do executável: sobe o servidor local e abre o navegador."""
import socket
import threading
import time
import webbrowser

HOST = "127.0.0.1"  # só aceita conexões da própria máquina (não fica exposto na rede)
PORTA_PREFERIDA = 8000


def porta_livre(preferida: int = PORTA_PREFERIDA) -> int:
    """Usa a porta preferida; se estiver ocupada, pede uma livre ao sistema."""
    for porta in (preferida, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, porta))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("Nenhuma porta livre encontrada.")


def abrir_navegador_quando_pronto(porta: int, tentativas: int = 50) -> None:
    """Espera o servidor responder e só então abre o navegador."""
    for _ in range(tentativas):
        try:
            with socket.create_connection((HOST, porta), timeout=0.3):
                break
        except OSError:
            time.sleep(0.2)
    webbrowser.open(f"http://{HOST}:{porta}")


def iniciar() -> None:
    import uvicorn
    from main import app  # importado aqui para o PyInstaller incluir o app e suas dependências

    porta = porta_livre()
    print("=" * 56)
    print(" Formatador de Contatos")
    print(f" Rodando em http://{HOST}:{porta}")
    print(" O navegador abrirá sozinho.")
    print(" Para ENCERRAR o sistema, feche esta janela.")
    print("=" * 56)

    threading.Thread(target=abrir_navegador_quando_pronto, args=(porta,), daemon=True).start()
    uvicorn.run(app, host=HOST, port=porta, log_level="warning")


def _testes():
    # porta preferida ocupada -> devolve outra porta que realmente está livre
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ocupada:
        ocupada.bind((HOST, 0))
        porta_ocupada = ocupada.getsockname()[1]
        outra = porta_livre(porta_ocupada)
        assert outra != porta_ocupada
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, outra))

    # porta preferida livre -> mantém a preferida
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        livre = s.getsockname()[1]
    assert porta_livre(livre) == livre
    print("testes do launcher OK")


if __name__ == "__main__":
    import sys
    if "--testar" in sys.argv:
        _testes()
    else:
        iniciar()