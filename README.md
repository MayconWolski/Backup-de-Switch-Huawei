<<<<<<< HEAD
429: Too Many Requests
=======
# Esse projeto foi desenvolvido com o objetivo de realizar backups de switches Huawei, mantendo um histórico de atividades.

Ele também conta com uma ferramenta de comparação entre os dois últimos backups, permitindo identificar eventuais diferenças após atualizações no equipamento e verificar se todas as configurações foram mantidas corretamente.

# Parte visual principal:

<img width="829" height="523" alt="image" src="https://github.com/user-attachments/assets/d7b25881-aab1-4092-8c38-4f9412b14f79" />

# Estrutura do projeto:

<img width="372" height="312" alt="image" src="https://github.com/user-attachments/assets/c7c78e29-c47e-4d6a-9741-2421a52e04fe" />

# PASTA Backup = Cada equipamento configurado vai ter uma pasta e dentro dela sera criado outra basta com os backups

# Exemplo: 

<img width="356" height="138" alt="image" src="https://github.com/user-attachments/assets/aff28859-db54-4006-aaed-135568b74068" />

São utilizados os seguintes comandos para fazer o backup:

<img width="450" height="135" alt="image" src="https://github.com/user-attachments/assets/f8eb02f2-7ac9-4222-a9bb-c0d5537d938a" />

current_config": "display current-configuration all"
vlan": "display vlan"
"interfaces": "display interface brief"
"routing": "display ip routing-table"

# SCRIPT db.py = fica a configuração do banco de dados e a criptografia das senhas e criar o arquivo equipamentos.json com os dados

<img width="450" height="373" alt="image" src="https://github.com/user-attachments/assets/abb6bbb1-94d0-4e19-809f-0c5c02df92c8" />

# SCRIPT main.py = fica todas as configurações das funcionalidades e parte visual 

# OBS: Nessesario colocar os dados do jumper manualmente para da o Salto para o SW 

<img width="549" height="214" alt="image" src="https://github.com/user-attachments/assets/ebd4aa5b-c31f-4e30-bf26-16c9e9cfb991" />


 





>>>>>>> 6c3d8576399aed8dd62aa406d916b17e3c9dc7d2
