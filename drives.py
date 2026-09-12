import subprocess
import os
import ctypes
import psutil
from datetime import datetime


# =========================================================
# GERENCIAMENTO DE DRIVES
# =========================================================

# =========================================================
# VERIFICAR ADMINISTRADOR
# =========================================================

def verificar_administrador():
    """
    Verifica se o programa está sendo executado
    com privilégios de administrador.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


# =========================================================
# LISTAR DRIVES
# =========================================================

def listar_drives():
    """
    Lista todos os drives/partições disponíveis no computador.
    Retorna informações de cada drive.
    """
    drives = []
    
    try:
        # Obter todas as partições do disco
        particoes = psutil.disk_partitions()
        
        for particao in particoes:
            try:
                # Informações básicas
                device = particao.device
                mount = particao.mountpoint
                fstype = particao.fstype
                
                # Tamanho
                if os.path.exists(mount):
                    total, usado, livre = psutil.disk_usage(mount)
                else:
                    total = usado = livre = 0
                
                # Converter para GB
                total_gb = total / (1024 ** 3)
                usado_gb = usado / (1024 ** 3)
                livre_gb = livre / (1024 ** 3)
                
                # Percentual de uso
                percentual = (usado / total * 100) if total > 0 else 0
                
                drives.append({
                    "device": device,
                    "mount": mount,
                    "fstype": fstype,
                    "total_bytes": total,
                    "usado_bytes": usado,
                    "livre_bytes": livre,
                    "total_gb": round(total_gb, 2),
                    "usado_gb": round(usado_gb, 2),
                    "livre_gb": round(livre_gb, 2),
                    "percentual": round(percentual, 1),
                    "removivel": particao.opts == "removable"
                })
                
            except Exception as erro:
                print(f"Erro ao analisar partição {particao.device}: {erro}")
                continue
        
        return drives
    
    except Exception as erro:
        print(f"Erro ao listar drives: {erro}")
        return []


# =========================================================
# OBTER INFORMAÇÕES DE UM DRIVE
# =========================================================

def obter_info_drive(device):
    """
    Obtém informações detalhadas de um drive específico.
    """
    drives = listar_drives()
    
    for drive in drives:
        if drive["device"].lower() == device.lower():
            return drive
    
    return None


# =========================================================
# EXECUTAR COMANDO DISKPART
# =========================================================

def executar_diskpart(comandos):
    """
    Executa comandos do DISKPART do Windows.
    
    comandos: lista de comandos a executar
    Exemplo: ["select disk 1", "clean", "create partition primary", "format fs=ntfs quick"]
    """
    
    if not verificar_administrador():
        return {
            "sucesso": False,
            "saida": "",
            "erro": "Privilégios de administrador necessários"
        }
    
    try:
        # Criar arquivo temporário com os comandos
        arquivo_temp = os.path.join(
            os.environ.get("TEMP", "C:\\Windows\\Temp"),
            f"diskpart_commands_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        # Escrever comandos no arquivo
        with open(arquivo_temp, "w") as f:
            for comando in comandos:
                f.write(comando + "\n")
            f.write("exit\n")
        
        # Executar diskpart
        processo = subprocess.run(
            ["diskpart", "/s", arquivo_temp],
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="replace"
        )
        
        # Limpar arquivo temporário
        try:
            os.remove(arquivo_temp)
        except Exception:
            pass
        
        saida = processo.stdout + processo.stderr
        
        return {
            "sucesso": processo.returncode == 0,
            "saida": saida,
            "erro": processo.stderr
        }
    
    except Exception as erro:
        return {
            "sucesso": False,
            "saida": "",
            "erro": str(erro)
        }


# =========================================================
# FORMATAR DRIVE COM FORMAT.COM
# =========================================================

def formatar_drive_com_format(letra_drive, sistema_arquivos="NTFS", label=""):
    """
    Formata um drive usando o comando format do Windows.
    
    letra_drive: letra do drive (Ex: "D" ou "D:")
    sistema_arquivos: NTFS, FAT32, exFAT
    label: nome/rótulo do drive
    """
    
    if not verificar_administrador():
        return {
            "sucesso": False,
            "mensagem": "Privilégios de administrador necessários"
        }
    
    # Normalizar letra do drive
    if len(letra_drive) == 1:
        letra_drive = letra_drive + ":"
    elif letra_drive.endswith(":"):
        pass
    else:
        return {
            "sucesso": False,
            "mensagem": "Letra de drive inválida"
        }
    
    # Validar sistema de arquivos
    sistemas_validos = ["NTFS", "FAT32", "exFAT"]
    if sistema_arquivos.upper() not in sistemas_validos:
        return {
            "sucesso": False,
            "mensagem": f"Sistema de arquivos inválido. Use: {', '.join(sistemas_validos)}"
        }
    
    # Verificar se drive existe
    if not os.path.exists(letra_drive + "\\"):
        return {
            "sucesso": False,
            "mensagem": f"Drive {letra_drive} não encontrado"
        }
    
    try:
        # Comando format
        comando = [
            "format",
            letra_drive,
            f"/FS:{sistema_arquivos.upper()}",
            "/Q"  # Quick format
        ]
        
        if label:
            comando.append(f'/V:{label.replace(" ", "_")[:32]}')
        else:
            comando.append("/V:")
        
        processo = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="replace",
            input="Y\n"  # Confirmar formatação
        )
        
        if processo.returncode == 0:
            return {
                "sucesso": True,
                "mensagem": f"Drive {letra_drive} formatado com sucesso como {sistema_arquivos}"
            }
        else:
            return {
                "sucesso": False,
                "mensagem": f"Erro ao formatar: {processo.stderr}"
            }
    
    except Exception as erro:
        return {
            "sucesso": False,
            "mensagem": f"Erro: {str(erro)}"
        }


# =========================================================
# FORMATAR DRIVE COM DISKPART
# =========================================================

def formatar_drive_com_diskpart(numero_disco, sistema_arquivos="NTFS"):
    """
    Formata um disco inteiro usando DISKPART.
    CUIDADO: Isso apaga todos os dados do disco!
    
    numero_disco: número do disco (0, 1, 2, etc.)
    sistema_arquivos: NTFS, FAT32, exFAT
    """
    
    if not verificar_administrador():
        return {
            "sucesso": False,
            "mensagem": "Privilégios de administrador necessários"
        }
    
    # Validar sistema de arquivos
    sistemas_validos = ["NTFS", "FAT32"]
    sistema_arquivos = sistema_arquivos.upper()
    
    if sistema_arquivos not in sistemas_validos:
        return {
            "sucesso": False,
            "mensagem": f"Sistema de arquivos inválido. Use: {', '.join(sistemas_validos)}"
        }
    
    try:
        comandos = [
            f"select disk {numero_disco}",
            "clean",  # Limpar disco
            "create partition primary",  # Criar partição primária
            f"format fs={sistema_arquivos} quick",  # Formatar
            "assign",  # Atribuir letra
            "exit"
        ]
        
        resultado = executar_diskpart(comandos)
        
        if resultado["sucesso"]:
            return {
                "sucesso": True,
                "mensagem": f"Disco {numero_disco} formatado com sucesso como {sistema_arquivos}",
                "saida": resultado["saida"]
            }
        else:
            return {
                "sucesso": False,
                "mensagem": f"Erro ao formatar disco: {resultado['erro']}",
                "saida": resultado["saida"]
            }
    
    except Exception as erro:
        return {
            "sucesso": False,
            "mensagem": f"Erro: {str(erro)}"
        }


# =========================================================
# LIMPAR DRIVE (WIPE)
# =========================================================

def limpar_drive_seguro(letra_drive, num_passos=1):
    """
    Limpa um drive de forma segura, sobrescrevendo os dados.
    
    letra_drive: letra do drive
    num_passos: número de passes (1-7)
    """
    
    if not verificar_administrador():
        return {
            "sucesso": False,
            "mensagem": "Privilégios de administrador necessários"
        }
    
    # Normalizar
    if len(letra_drive) == 1:
        letra_drive = letra_drive + ":"
    
    caminho = letra_drive + "\\"
    
    if not os.path.exists(caminho):
        return {
            "sucesso": False,
            "mensagem": f"Drive {letra_drive} não encontrado"
        }
    
    try:
        # Listar todos os arquivos
        arquivos = []
        for raiz, pastas, nomes in os.walk(caminho):
            for nome in nomes:
                try:
                    caminho_arquivo = os.path.join(raiz, nome)
                    tamanho = os.path.getsize(caminho_arquivo)
                    
                    if tamanho > 0:
                        arquivos.append(caminho_arquivo)
                
                except Exception:
                    pass
        
        removidos = 0
        erros = 0
        
        # Remover arquivos
        for arquivo in arquivos:
            try:
                os.remove(arquivo)
                removidos += 1
            except Exception:
                erros += 1
        
        return {
            "sucesso": True,
            "mensagem": f"Drive limpo: {removidos} arquivos removidos, {erros} erros",
            "removidos": removidos,
            "erros": erros
        }
    
    except Exception as erro:
        return {
            "sucesso": False,
            "mensagem": f"Erro: {str(erro)}"
        }


# =========================================================
# EJETAR DRIVE
# =========================================================

def ejetar_drive(letra_drive):
    """
    Ejeta um drive removível (pendrive, cartão SD, etc).
    """
    
    if len(letra_drive) == 1:
        letra_drive = letra_drive + ":"
    
    try:
        # Comando para ejetar via Windows
        comando = [
            "powershell",
            "-Command",
            f"(New-Object -ComObject Shell.Application).Namespace(17).ParseName('{letra_drive}').InvokeVerb('Eject')"
        ]
        
        processo = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if processo.returncode == 0:
            return {
                "sucesso": True,
                "mensagem": f"Drive {letra_drive} ejetado com sucesso"
            }
        else:
            return {
                "sucesso": False,
                "mensagem": f"Erro ao ejetar drive: {processo.stderr}"
            }
    
    except Exception as erro:
        return {
            "sucesso": False,
            "mensagem": f"Erro: {str(erro)}"
        }


# =========================================================
# OBTER LETRA DE DRIVE DISPONÍVEL
# =========================================================

def obter_primeira_letra_disponivel():
    """
    Retorna a primeira letra de drive disponível (não usada).
    """
    for letra in "DEFGHIJKLMNOPQRSTUVWXYZ":
        if not os.path.exists(f"{letra}:\\"):
            return letra
    
    return None


# =========================================================
# VERIFICAR SE DRIVE É REMOVÍVEL
# =========================================================

def eh_removivel(letra_drive):
    """
    Verifica se um drive é removível (pendrive, cartão SD, etc).
    """
    
    if len(letra_drive) == 1:
        letra_drive = letra_drive + ":"
    
    drives = listar_drives()
    
    for drive in drives:
        if drive["mount"].startswith(letra_drive):
            return drive.get("removivel", False)
    
    return False
