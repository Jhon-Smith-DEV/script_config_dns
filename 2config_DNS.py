#!/usr/bin/env python3
import subprocess
import os
import shutil
from pathlib import Path

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
DOMAIN = "tallerandino.com.bo"
IP_DNS = "192.168.56.236"
IP_MAIL = "192.168.56.237"
IP_WWW = "192.168.56.238"
ADMIN_MAIL = "abd23esc.gmail.com."  # SOA contact
ZONE_DIR = Path("/var/named")
NAMED_CONF = Path("/etc/named.conf")

# Archivos de zona
ZONE_FILE = ZONE_DIR / f"{DOMAIN}.zone"
REVERSE_ZONE = "56.168.192.in-addr.arpa"
REVERSE_FILE = ZONE_DIR / f"{REVERSE_ZONE}.zone"


# ==============================
# FUNCIONES AUXILIARES
# ==============================
def run_cmd(cmd, check=True, capture=False):
    """Ejecutar un comando en shell"""
    print(f"[+] Ejecutando: {cmd}")
    if capture:
        return subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True).stdout
    else:
        subprocess.run(cmd, shell=True, check=check)


def install_packages():
    print("\n=== Instalando paquetes necesarios ===")
    run_cmd("dnf install -y bind bind-chroot bind-utils")


def verify_packages():
    print("\n=== Verificando instalación de BIND ===")
    try:
        output = run_cmd("rpm -q bind bind-chroot bind-utils", capture=True)
        print(output)
    except subprocess.CalledProcessError:
        print("❌ Paquetes BIND no están instalados.")


def create_zone_files():
    print("\n=== Creando archivo de zona directa ===")
    zone_content = f"""$TTL 86400
@   IN  SOA {DOMAIN}. {ADMIN_MAIL} (
    2025091601 ; Serial
    28800      ; Refresh
    7200       ; Retry
    604800     ; Expire
    86400 )    ; Minimum TTL

@       IN  NS      dns
@       IN  MX  10  mail
@       IN  A       {IP_DNS}
dns     IN  A       {IP_DNS}
mail    IN  A       {IP_MAIL}
www     IN  A       {IP_WWW}
ftp     IN  CNAME   www
"""
    ZONE_FILE.write_text(zone_content)
    os.chown(ZONE_FILE, 25, 25)  # user: named, group: named
    os.chmod(ZONE_FILE, 0o640)

    print("\n=== Creando archivo de zona inversa ===")
    reverse_content = f"""$TTL 86400
@   IN  SOA {DOMAIN}. {ADMIN_MAIL} (
    2025091601 ; Serial
    28800      ; Refresh
    7200       ; Retry
    604800     ; Expire
    86400 )    ; Minimum TTL

@       IN  NS      dns.{DOMAIN}.
236     IN  PTR     dns.{DOMAIN}.
237     IN  PTR     mail.{DOMAIN}.
238     IN  PTR     www.{DOMAIN}.
"""
    REVERSE_FILE.write_text(reverse_content)
    os.chown(REVERSE_FILE, 25, 25)
    os.chmod(REVERSE_FILE, 0o640)


def verify_zone_files():
    print("\n=== Verificando archivos de zona ===")
    if ZONE_FILE.exists():
        print(f"✅ Archivo de zona directa encontrado: {ZONE_FILE}")
    else:
        print(f"❌ No existe {ZONE_FILE}")

    if REVERSE_FILE.exists():
        print(f"✅ Archivo de zona inversa encontrado: {REVERSE_FILE}")
    else:
        print(f"❌ No existe {REVERSE_FILE}")


def configure_named_conf():
    print("\n=== Configurando named.conf ===")

    # Crear copia de seguridad
    backup_file = NAMED_CONF.with_suffix(NAMED_CONF.suffix + "-bak")
    shutil.copy2(NAMED_CONF, backup_file)
    print(f"[+] Copia de seguridad creada: {backup_file}")

    conf_lines = NAMED_CONF.read_text().splitlines()

    # Ajustar listen-on
    conf_lines = [line.replace(
        "listen-on port 53 { 127.0.0.1; };",
        f"listen-on port 53 {{ 127.0.0.1; {IP_DNS}; }};"
    ) if "listen-on port 53" in line else line for line in conf_lines]

    # Ajustar allow-query
    conf_lines = [line.replace(
        "allow-query     { localhost; };",
        "allow-query     { localhost; any; };"
    ) if "allow-query" in line else line for line in conf_lines]

    # Definir bloque de zonas
    zone_block = f"""
zone "{DOMAIN}" {{
    type master;
    file "{ZONE_FILE.name}";
    allow-update {{ none; }};
}};

zone "{REVERSE_ZONE}" {{
    type master;
    file "{REVERSE_FILE.name}";
    allow-update {{ none; }};
}};
"""

    # Agregar zonas solo si no existen ya
    if ZONE_FILE.name not in "\n".join(conf_lines):
        # Insertar al final, antes de cerrar el archivo
        conf_lines.append(zone_block.strip())

    # Guardar cambios
    NAMED_CONF.write_text("\n".join(conf_lines))
    print("[+] Zonas añadidas al final de named.conf")


def verify_named_conf():
    print("\n=== Verificando configuración de named.conf ===")
    conf_text = NAMED_CONF.read_text()
    if DOMAIN in conf_text and REVERSE_ZONE in conf_text:
        print("✅ Zonas de dominio e inversa están configuradas en named.conf")
    else:
        print("❌ No se encontraron las zonas configuradas en named.conf")


def verify_config():
    print("\n=== Verificando configuración de BIND ===")
    run_cmd("/usr/sbin/named-checkconf -z /etc/named.conf")


def start_services():
    print("\n=== Iniciando y habilitando servicio named ===")
    run_cmd("systemctl start named")
    run_cmd("systemctl restart named")
    run_cmd("systemctl enable named")
    run_cmd("systemctl status named --no-pager")


def test_queries():
    print("\n=== Realizando consultas de prueba ===")
    run_cmd(f"nslookup mail.{DOMAIN} {IP_DNS}")
    run_cmd(f"nslookup www.{DOMAIN} {IP_DNS}")
    run_cmd(f"nslookup ftp.{DOMAIN} {IP_DNS}")
    run_cmd(f"nslookup {IP_DNS} {IP_DNS}")


def stop_firewalld():
    print("\n=== Deteniendo firewalld para pruebas ===")
    run_cmd("systemctl stop firewalld")


# ==============================
# MAIN CON MENÚ
# ==============================
if __name__ == "__main__":
    while True:
        print("\n=== Menú de configuración DNS ===")
        print("1) Instalar paquetes BIND")
        print("2) Verificar instalación de BIND")
        print("3) Crear archivos de zona (directa e inversa)")
        print("4) Verificar archivos de zona")
        print("5) Configurar named.conf (con backup)")
        print("6) Verificar named.conf")
        print("7) Verificar configuración BIND")
        print("8) Iniciar y habilitar servicio named")
        print("9) Realizar consultas de prueba")
        print("10) Detener firewalld para pruebas")
        print("11) Ejecutar TODO en orden")
        print("12) Salir")

        choice = input("Selecciona una opción: ")

        if choice == "1":
            install_packages()
        elif choice == "2":
            verify_packages()
        elif choice == "3":
            create_zone_files()
        elif choice == "4":
            verify_zone_files()
        elif choice == "5":
            configure_named_conf()
        elif choice == "6":
            verify_named_conf()
        elif choice == "7":
            verify_config()
        elif choice == "8":
            start_services()
        elif choice == "9":
            test_queries()
        elif choice == "10":
            stop_firewalld()
        elif choice == "11":
            install_packages()
            verify_packages()
            create_zone_files()
            verify_zone_files()
            configure_named_conf()
            verify_named_conf()
            verify_config()
            start_services()
            test_queries()
            stop_firewalld()
            print("\n✅ Configuración completa ejecutada.")
        elif choice == "12":
            print("Saliendo...")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")
