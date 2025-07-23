import os
import difflib

SW_NAME = 'RTARATP2'
BASE_DIR = os.path.join('backups', SW_NAME)

def listar_backups(backup_dir):
    pastas = [p for p in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, p))]
    pastas = sorted(pastas, reverse=True)  # ordena do mais recente para o mais antigo
    return pastas[:2]  # pega os dois mais recentes

def comparar_arquivos(arquivo1, arquivo2):
    with open(arquivo1, encoding='utf-8') as f1, open(arquivo2, encoding='utf-8') as f2:
        linhas1 = f1.readlines()
        linhas2 = f2.readlines()

    diff = difflib.unified_diff(
        linhas1, linhas2,
        fromfile=arquivo1,
        tofile=arquivo2,
        lineterm=''
    )

    print(f"\n====== Diferença: {os.path.basename(arquivo1)} ======")
    houve_diferenca = False
    for linha in diff:
        print(linha)
        houve_diferenca = True
    if not houve_diferenca:
        print("Nenhuma diferença encontrada.")

def main():
    if not os.path.exists(BASE_DIR):
        print(f"[ERRO] Pasta {BASE_DIR} não encontrada.")
        return

    pastas = listar_backups(BASE_DIR)
    if len(pastas) < 2:
        print("[ERRO] Menos de 2 backups encontrados.")
        return

    pasta_antiga = os.path.join(BASE_DIR, pastas[1])
    pasta_nova = os.path.join(BASE_DIR, pastas[0])

    print(f"[+] Comparando:\n - {pastas[1]}\n - {pastas[0]}")

    arquivos = os.listdir(pasta_nova)
    for nome_arquivo in arquivos:
        arq1 = os.path.join(pasta_antiga, nome_arquivo)
        arq2 = os.path.join(pasta_nova, nome_arquivo)
        if os.path.exists(arq1) and os.path.exists(arq2):
            comparar_arquivos(arq1, arq2)
        else:
            print(f"[!] Arquivo ausente em uma das pastas: {nome_arquivo}")

if __name__ == '__main__':
    main()
