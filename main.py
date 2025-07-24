import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
from datetime import datetime
import base64
import paramiko
import time
import subprocess
import platform
import threading
import re

EQUIPAMENTOS_FILE = "equipamentos.json"
BACKUP_DIR = "backups"

COMANDOS = {
    "current_config": "display current-configuration all",
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
        return []
    try:
        with open(EQUIPAMENTOS_FILE, "r") as f:
            conteudo = f.read().strip()
            if not conteudo:
                return []
            return json.loads(conteudo)
    except (json.JSONDecodeError, IOError):
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

def atualizar_equipamentos(equipamentos):
    with open(EQUIPAMENTOS_FILE, "w") as f:
        json.dump(equipamentos, f, indent=4)

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

# Função para receber saída completa até o prompt
def receber_saida_completa(channel, prompt, timeout=15):
    buffer = ''
    channel.settimeout(1.0)
    tempo_inicio = time.time()

    while True:
        if channel.recv_ready():
            resp = channel.recv(4096).decode(errors='ignore')
            buffer += resp
            tempo_inicio = time.time()  # reseta timeout ao receber dados
            # Detecta se o prompt apareceu no final da saída
            if buffer.strip().endswith(prompt):
                break
        else:
            if time.time() - tempo_inicio > timeout:
                break
            time.sleep(0.2)
    return buffer

# Variáveis globais para janelas únicas
janela_cadastro = None
janela_edicao = None
janela_backups = None
janela_log = None

def atualizar_lista():
    lista.delete(0, tk.END)
    for eq in carregar_equipamentos():
        lista.insert(tk.END, f"{eq['nome']} - {eq['ip']} ({eq['usuario']})")

def abrir_cadastro():
    global janela_cadastro
    if janela_cadastro and janela_cadastro.winfo_exists():
        janela_cadastro.destroy()

    def salvar():
        nome = nome_entry.get()
        ip = ip_entry.get()
        usuario = usuario_entry.get()
        senha = senha_entry.get()
        if nome and ip and usuario and senha:
            salvar_equipamento(nome, ip, usuario, senha)
            messagebox.showinfo("Sucesso", "Equipamento salvo com sucesso!")
            janela_cadastro.destroy()
            atualizar_lista()
        else:
            messagebox.showwarning("Campos vazios", "Preencha todos os campos!")

    janela_cadastro = tk.Toplevel(root)
    janela_cadastro.title("Cadastro de Equipamento")

    tk.Label(janela_cadastro, text="Nome").grid(row=0, column=0)
    tk.Label(janela_cadastro, text="IP").grid(row=1, column=0)
    tk.Label(janela_cadastro, text="Usuário").grid(row=2, column=0)
    tk.Label(janela_cadastro, text="Senha").grid(row=3, column=0)

    nome_entry = tk.Entry(janela_cadastro)
    ip_entry = tk.Entry(janela_cadastro)
    usuario_entry = tk.Entry(janela_cadastro)
    senha_entry = tk.Entry(janela_cadastro, show="*")

    nome_entry.grid(row=0, column=1)
    ip_entry.grid(row=1, column=1)
    usuario_entry.grid(row=2, column=1)
    senha_entry.grid(row=3, column=1)

    tk.Button(janela_cadastro, text="Salvar", command=salvar).grid(row=4, columnspan=2)

def abrir_edicao():
    global janela_edicao
    if janela_edicao and janela_edicao.winfo_exists():
        janela_edicao.destroy()

    selected = lista.curselection()
    if not selected:
        messagebox.showwarning("Atenção", "Selecione um equipamento para editar!")
        return

    index = selected[0]
    equip = carregar_equipamentos()[index]

    def salvar():
        nome = nome_entry.get()
        ip = ip_entry.get()
        usuario = usuario_entry.get()
        senha = senha_entry.get()
        if nome and ip and usuario:
            equipamentos = carregar_equipamentos()
            if senha:
                senha_cript = criptografar(senha)
            else:
                senha_cript = equipamentos[index]['senha']
            equipamentos[index] = {
                "nome": nome,
                "ip": ip,
                "usuario": usuario,
                "senha": senha_cript
            }
            atualizar_equipamentos(equipamentos)
            messagebox.showinfo("Sucesso", "Equipamento atualizado com sucesso!")
            janela_edicao.destroy()
            atualizar_lista()
        else:
            messagebox.showwarning("Campos vazios", "Preencha todos os campos (exceto senha que pode ficar vazia)!")

    janela_edicao = tk.Toplevel(root)
    janela_edicao.title("Editar Equipamento")

    tk.Label(janela_edicao, text="Nome").grid(row=0, column=0)
    tk.Label(janela_edicao, text="IP").grid(row=1, column=0)
    tk.Label(janela_edicao, text="Usuário").grid(row=2, column=0)
    tk.Label(janela_edicao, text="Senha").grid(row=3, column=0)

    nome_entry = tk.Entry(janela_edicao)
    ip_entry = tk.Entry(janela_edicao)
    usuario_entry = tk.Entry(janela_edicao)
    senha_entry = tk.Entry(janela_edicao, show="*")

    nome_entry.grid(row=0, column=1)
    ip_entry.grid(row=1, column=1)
    usuario_entry.grid(row=2, column=1)
    senha_entry.grid(row=3, column=1)

    nome_entry.insert(0, equip["nome"])
    ip_entry.insert(0, equip["ip"])
    usuario_entry.insert(0, equip["usuario"])
    senha_entry.insert(0, descriptografar(equip["senha"]))

    tk.Button(janela_edicao, text="Salvar", command=salvar).grid(row=4, columnspan=2)

    def excluir():
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este equipamento?"):
            equipamentos = carregar_equipamentos()
            equipamentos.pop(index)
            atualizar_equipamentos(equipamentos)
            messagebox.showinfo("Sucesso", "Equipamento excluído com sucesso!")
            janela_edicao.destroy()
            atualizar_lista()

    tk.Button(janela_edicao, text="Excluir", fg="red", command=excluir).grid(row=5, columnspan=2)

def exibir_backups():
    global janela_backups
    if janela_backups and janela_backups.winfo_exists():
        janela_backups.destroy()

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

    janela_backups = tk.Toplevel(root)
    janela_backups.title(f"Backups de {equip['nome']}")

    lb = tk.Listbox(janela_backups, width=60)
    lb.pack(padx=10, pady=10)
    for b in backups:
        lb.insert(tk.END, b)
    lb.bind("<Double-1>", abrir_selecionado)

def executar_backup_thread(equip, text_widget, janela_log, callback):
    try:
        jump_host = "45.167.183.21"
        jump_port = 22587
        jump_user = "noc.psne"
        jump_pass = "Qwe@1234!"

        def log(msg):
            text_widget.insert(tk.END, msg + "\n")
            text_widget.see(tk.END)

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

        # Ajuste para detectar prompt, ex: <rtaratp2>
        # Pegamos o nome do switch do output ou você pode definir fixo
        prompt_match = re.search(r'<[\w\-\d]+>', output)
        prompt = prompt_match.group(0) if prompt_match else '>'

        # Desliga paginação
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
            time.sleep(1)
            saida = receber_saida_completa(channel, prompt)
            with open(os.path.join(pasta_backup, f"{nome}.txt"), "w", encoding='utf-8') as f:
                f.write(saida)
            log(f"[+] Comando '{comando}' salvo.")

        log(f"[+] Backup concluído em: {pasta_backup}")
        messagebox.showinfo("Backup", f"Backup concluído em: {pasta_backup}")
        janela_log.destroy()
        callback()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao executar backup: {e}")
        janela_log.destroy()
        callback()

def abrir_log_backup_sequencial(equipamentos, index=0):
    if index >= len(equipamentos):
        return  # terminou todos

    global janela_log
    if janela_log and janela_log.winfo_exists():
        janela_log.destroy()

    equip = equipamentos[index]
    janela_log = tk.Toplevel(root)
    janela_log.title(f"Log de Backup - {equip['nome']}")
    janela_log.geometry("600x400")

    texto_log = scrolledtext.ScrolledText(janela_log, state='normal')
    texto_log.pack(expand=True, fill='both')

    def proximo_backup():
        abrir_log_backup_sequencial(equipamentos, index + 1)

    thread = threading.Thread(target=executar_backup_thread, args=(equip, texto_log, janela_log, proximo_backup))
    thread.start()

root = tk.Tk()
root.title("Cadastro de Equipamentos")

# Lista à esquerda
lista = tk.Listbox(root, width=35, height=10, selectmode=tk.MULTIPLE)

lista.pack(side="left", padx=10, pady=10, fill="y")

# Frame à direita com os botões empilhados
frame_botoes = tk.Frame(root)
frame_botoes.pack(side="right", padx=10, pady=10, fill="y")

btn_cadastrar = tk.Button(frame_botoes, text="Cadastrar Equipamento", command=abrir_cadastro)
btn_editar = tk.Button(frame_botoes, text="Editar/Excluir Equipamento", command=abrir_edicao)
btn_backup = tk.Button(frame_botoes, text="Executar Backup (Múltiplos)", command=lambda: (
    abrir_log_backup_sequencial(
        [carregar_equipamentos()[i] for i in lista.curselection()]
    ) if lista.curselection() else messagebox.showwarning("Atenção", "Selecione pelo menos um equipamento!")
))
btn_ver_backups = tk.Button(frame_botoes, text="Ver Backups", command=exibir_backups)

# Empilha os botões verticalmente
btn_cadastrar.pack(fill="x", pady=2)
btn_editar.pack(fill="x", pady=2)
btn_backup.pack(fill="x", pady=2)
btn_ver_backups.pack(fill="x", pady=2)

atualizar_lista()
root.mainloop()

