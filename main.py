import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
from datetime import datetime
import base64
import paramiko
import time
import threading
import queue
import subprocess
import platform
import difflib

EQUIPAMENTOS_FILE = "equipamentos.json"
BACKUP_DIR = "backups"

COMANDOS = {
    "current_config": "display current-configuration",
    "vlan": "display vlan",
    "interfaces": "display interface brief",
    "routing": "display ip routing-table"
}

def criptografar(texto):
    return base64.b64encode(texto.encode()).decode()

def descriptografar(texto):
    return base64.b64decode(texto.encode()).decode()

def carregar_equipamentos():
    if not os.path.exists(EQUIPAMENTOS_FILE):
        with open(EQUIPAMENTOS_FILE, "w") as f:
            json.dump([], f)
        return []
    with open(EQUIPAMENTOS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            messagebox.showerror("Erro", f"Arquivo {EQUIPAMENTOS_FILE} está corrompido!")
            return []

def salvar_equipamento(nome, ip, usuario, senha):
    equipamentos = carregar_equipamentos()
    equipamentos.append({
        "nome": nome,
        "ip": ip,
        "usuario": usuario,
        "senha": criptografar(senha)
    })
    with open(EQUIPAMENTOS_FILE, "w") as f:
        json.dump(equipamentos, f, indent=4)

def atualizar_lista():
    equipamentos = carregar_equipamentos()
    lista.delete(0, tk.END)
    for eq in equipamentos:
        lista.insert(tk.END, f"{eq['nome']} - {eq['ip']} ({eq['usuario']})")

def abrir_cadastro(equip=None):
    def salvar():
        nome = nome_entry.get()
        ip = ip_entry.get()
        usuario = usuario_entry.get()
        senha = senha_entry.get()
        if not (nome and ip and usuario):
            messagebox.showwarning("Campos vazios", "Preencha todos os campos, exceto senha se não quiser alterar.")
            return

        equipamentos = carregar_equipamentos()

        if equip:
            for e in equipamentos:
                if e["nome"] == equip["nome"]:
                    e["nome"] = nome
                    e["ip"] = ip
                    e["usuario"] = usuario
                    if senha:
                        e["senha"] = criptografar(senha)
                    break
            messagebox.showinfo("Sucesso", "Equipamento editado com sucesso!")
        else:
            nomes = [e["nome"] for e in equipamentos]
            if nome in nomes:
                messagebox.showerror("Erro", "Já existe equipamento com este nome!")
                return
            if not senha:
                messagebox.showwarning("Campos vazios", "Preencha a senha!")
                return
            salvar_equipamento(nome, ip, usuario, senha)
            messagebox.showinfo("Sucesso", "Equipamento salvo com sucesso!")

        with open(EQUIPAMENTOS_FILE, "w") as f:
            json.dump(equipamentos, f, indent=4)

        cadastro_win.destroy()
        atualizar_lista()

    global cadastro_win
    if cadastro_win and cadastro_win.winfo_exists():
        cadastro_win.destroy()

    cadastro_win = tk.Toplevel(root)
    cadastro_win.title("Cadastro de Equipamento")

    tk.Label(cadastro_win, text="Nome").grid(row=0, column=0)
    tk.Label(cadastro_win, text="IP").grid(row=1, column=0)
    tk.Label(cadastro_win, text="Usuário").grid(row=2, column=0)
    tk.Label(cadastro_win, text="Senha").grid(row=3, column=0)

    nome_entry = tk.Entry(cadastro_win)
    ip_entry = tk.Entry(cadastro_win)
    usuario_entry = tk.Entry(cadastro_win)
    senha_entry = tk.Entry(cadastro_win, show="*")

    nome_entry.grid(row=0, column=1)
    ip_entry.grid(row=1, column=1)
    usuario_entry.grid(row=2, column=1)
    senha_entry.grid(row=3, column=1)

    if equip:
        nome_entry.insert(0, equip["nome"])
        ip_entry.insert(0, equip["ip"])
        usuario_entry.insert(0, equip["usuario"])

    tk.Button(cadastro_win, text="Salvar", command=salvar).grid(row=4, columnspan=2)

def excluir_equipamento():
    selected = lista.curselection()
    if not selected:
        messagebox.showwarning("Atenção", "Selecione um equipamento para excluir!")
        return
    equipamentos = carregar_equipamentos()
    equip = equipamentos[selected[0]]
    resposta = messagebox.askyesno("Confirmar exclusão", f"Excluir equipamento {equip['nome']}?")
    if resposta:
        equipamentos.pop(selected[0])
        with open(EQUIPAMENTOS_FILE, "w") as f:
            json.dump(equipamentos, f, indent=4)
        atualizar_lista()

def executar_backup_thread(equip, log_queue):
    try:
        jump_host = "45.167.183.21"
        jump_port = 22587
        jump_user = "noc.psne"
        jump_pass = "Qwe@1234!"

        def log(msg):
            log_queue.put(msg)

        log("[*] Conectando ao Jump Server...")
        jump_ssh = paramiko.SSHClient()
        jump_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        jump_ssh.connect(jump_host, port=jump_port, username=jump_user, password=jump_pass)
        log("[+] Conectado ao Jump Server")

        channel = jump_ssh.invoke_shell()
        time.sleep(1)
        channel.recv(9999)

        log(f"[*] Conectando ao equipamento {equip['nome']} ({equip['ip']})...")
        channel.send(f'ssh {equip["usuario"]}@{equip["ip"]}\n')
        time.sleep(5)

        output = channel.recv(65535).decode(errors='ignore')
        if 'yes/no' in output.lower():
            channel.send('yes\n')
            time.sleep(2)
            output += channel.recv(65535).decode(errors='ignore')
            log("[*] Confirmado o host remoto")

        if 'password' in output.lower():
            channel.send(descriptografar(equip['senha']) + '\n')
            log("[*] Enviando senha...")
            time.sleep(3)

        channel.send('screen-length 0 temporary\n')
        time.sleep(1)
        channel.recv(9999)

        pasta_equip = os.path.join(BACKUP_DIR, equip["nome"])
        os.makedirs(pasta_equip, exist_ok=True)
        data_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        pasta_backup = os.path.join(pasta_equip, f"{equip['nome']}_{data_str}")
        os.makedirs(pasta_backup, exist_ok=True)

        for nome, comando in COMANDOS.items():
            log(f"[*] Executando comando: {comando}")
            channel.send(comando + '\n')
            time.sleep(3)
            saida = channel.recv(99999).decode(errors='ignore')
            with open(os.path.join(pasta_backup, f"{nome}.txt"), "w", encoding='utf-8') as f:
                f.write(saida)
            log(f"[+] Comando '{comando}' salvo.")

        log(f"[+] Backup concluído em: {pasta_backup}")
        log_queue.put("=== FIM DO LOG ===")
    except Exception as e:
        log_queue.put(f"[ERRO] {e}")

def abrir_log_backup(equip):
    global janela_log
    if janela_log and janela_log.winfo_exists():
        janela_log.destroy()

    janela_log = tk.Toplevel(root)
    janela_log.title(f"Log de Backup - {equip['nome']}")
    janela_log.geometry("600x400")

    texto_log = scrolledtext.ScrolledText(janela_log, state='normal')
    texto_log.pack(expand=True, fill='both')

    log_queue = queue.Queue()

    def atualizar_log():
        try:
            while True:
                linha = log_queue.get_nowait()
                texto_log.insert(tk.END, linha + "\n")
                texto_log.see(tk.END)
                if linha == "=== FIM DO LOG ===":
                    messagebox.showinfo("Backup", f"Backup concluído em: backups/{equip['nome']}")
                    janela_log.destroy()
                    return
        except queue.Empty:
            pass
        janela_log.after(100, atualizar_log)

    thread = threading.Thread(target=executar_backup_thread, args=(equip, log_queue))
    thread.daemon = True
    thread.start()

    atualizar_log()

def abrir_backup(arquivo_path):
    sistema = platform.system()
    try:
        if sistema == "Windows":
            os.startfile(arquivo_path)
        elif sistema == "Darwin":
            subprocess.run(["open", arquivo_path])
        else:
            subprocess.run(["xdg-open", arquivo_path])
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao abrir arquivo: {e}")

def exibir_backups():
    selected = lista.curselection()
    if not selected:
        messagebox.showwarning("Atenção", "Selecione um equipamento!")
        return
    equip = carregar_equipamentos()[selected[0]]
    pasta_equip = os.path.join(BACKUP_DIR, equip["nome"])
    if not os.path.exists(pasta_equip):
        messagebox.showinfo("Backups", "Nenhum backup encontrado.")
        return
    backups = os.listdir(pasta_equip)
    backups.sort(reverse=True)
    if not backups:
        messagebox.showinfo("Backups", "Nenhum backup encontrado.")
        return

    def abrir_selecionado(event):
        index = lb.curselection()
        if not index:
            return
        pasta = os.path.join(pasta_equip, backups[index[0]])
        arquivos = os.listdir(pasta)
        for arq in arquivos:
            abrir_backup(os.path.join(pasta, arq))

    win = tk.Toplevel(root)
    win.title(f"Backups de {equip['nome']}")

    lb = tk.Listbox(win, width=60)
    lb.pack(padx=10, pady=10)
    for b in backups:
        lb.insert(tk.END, b)
    lb.bind("<Double-1>", abrir_selecionado)

def comparar_backups_selecionado():
    selected = lista.curselection()
    if not selected:
        messagebox.showwarning("Atenção", "Selecione um equipamento!")
        return
    equipamento = carregar_equipamentos()[selected[0]]
    nome_equipamento = equipamento["nome"]
    comparar_backups_equipamento(nome_equipamento)

def comparar_backups_equipamento(nome_equip):
    pasta_equip = os.path.join(BACKUP_DIR, nome_equip)
    if not os.path.exists(pasta_equip):
        messagebox.showerror("Erro", f"Nenhum backup encontrado para {nome_equip}")
        return

    pastas = sorted([p for p in os.listdir(pasta_equip) if os.path.isdir(os.path.join(pasta_equip, p))], reverse=True)
    if len(pastas) < 2:
        messagebox.showwarning("Aviso", "São necessários pelo menos 2 backups para comparar.")
        return

    pasta_nova = os.path.join(pasta_equip, pastas[0])
    pasta_antiga = os.path.join(pasta_equip, pastas[1])

    arquivos = os.listdir(pasta_nova)

    janela_diff = tk.Toplevel(root)
    janela_diff.title(f"Comparação de backups - {nome_equip}")
    janela_diff.geometry("800x600")

    texto = scrolledtext.ScrolledText(janela_diff, font=("Courier", 10))
    texto.pack(expand=True, fill='both')

    texto.insert(tk.END, f"Comparando:\n- {pastas[1]}\n- {pastas[0]}\n\n")

    for nome_arquivo in arquivos:
        arq1 = os.path.join(pasta_antiga, nome_arquivo)
        arq2 = os.path.join(pasta_nova, nome_arquivo)

        if os.path.exists(arq1) and os.path.exists(arq2):
            with open(arq1, encoding='utf-8') as f1, open(arq2, encoding='utf-8') as f2:
                linhas1 = f1.readlines()
                linhas2 = f2.readlines()

            diff = difflib.unified_diff(
                linhas1, linhas2,
                fromfile=nome_arquivo + " (antigo)",
                tofile=nome_arquivo + " (novo)",
                lineterm=''
            )

            texto.insert(tk.END, f"\n====== Diferença: {nome_arquivo} ======\n")
            houve_diferenca = False
            for linha in diff:
                texto.insert(tk.END, linha + "\n")
                houve_diferenca = True
            if not houve_diferenca:
                texto.insert(tk.END, "Nenhuma diferença encontrada.\n")
        else:
            texto.insert(tk.END, f"[!] Arquivo ausente em uma das pastas: {nome_arquivo}\n")

    texto.config(state='disabled')

def editar_equipamento():
    selected = lista.curselection()
    if not selected:
        messagebox.showwarning("Atenção", "Selecione um equipamento para editar!")
        return
    equip = carregar_equipamentos()[selected[0]]
    abrir_cadastro(equip)

root = tk.Tk()
root.title("Cadastro de Switch Huawei")
root.geometry("600x400")  # janela mais larga para acomodar a lista e os botões

cadastro_win = None
janela_log = None

# Frame principal
frame_principal = tk.Frame(root)
frame_principal.pack(fill='both', expand=True)

# Frame da lista (lado esquerdo)
frame_lista = tk.Frame(frame_principal)
frame_lista.pack(side='left', fill='both', expand=True, padx=10, pady=10)

lista = tk.Listbox(frame_lista, width=40, height=15)
lista.pack(side='left', fill='both', expand=True)

scrollbar = tk.Scrollbar(frame_lista)
scrollbar.pack(side='right', fill='y')
lista.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=lista.yview)

# Frame dos botões (lado direito)
frame_botoes = tk.Frame(frame_principal)
frame_botoes.pack(side='right', padx=15, pady=10, fill='y')

btn_cadastrar = tk.Button(frame_botoes, text="Cadastrar Equipamento", width=25, command=lambda: abrir_cadastro(None))
btn_editar = tk.Button(frame_botoes, text="Editar Equipamento", width=25, command=editar_equipamento)
btn_excluir = tk.Button(frame_botoes, text="Excluir Equipamento", width=25, command=excluir_equipamento)
btn_backup = tk.Button(
    frame_botoes,
    text="Executar Backup",
    width=25,
    command=lambda: abrir_log_backup(carregar_equipamentos()[lista.curselection()[0]]) if lista.curselection() else messagebox.showwarning("Atenção", "Selecione um equipamento!")
)
btn_ver_backups = tk.Button(frame_botoes, text="Ver Backups", width=25, command=exibir_backups)
btn_comparar = tk.Button(frame_botoes, text="Comparar Backups", width=25, command=comparar_backups_selecionado)

# Adiciona os botões verticalmente
btn_cadastrar.pack(pady=5)
btn_editar.pack(pady=5)
btn_excluir.pack(pady=5)
btn_backup.pack(pady=5)
btn_ver_backups.pack(pady=5)
btn_comparar.pack(pady=5)

atualizar_lista()
root.mainloop()
