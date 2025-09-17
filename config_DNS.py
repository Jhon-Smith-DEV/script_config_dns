#!/usr/bin/env python3
import subprocess
import os
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
def run_cmd(cmd, check=True):
    """Ejecutar un comando en shell"""
    print(f"[+] Ejecutando: {cmd}")
    subprocess.run(cmd, shell=True, check=check)


def install_packages():
    print("\n=== Instalando paquetes necesarios ===")
    run_cmd("dnf install -y bind bind-chroot bind-utils")


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


def configure_named_conf():
    print("\n=== Configurando named.conf ===")
    conf_text = NAMED_CONF.read_text()

    # Ajustar listen-on
    if "listen-on port 53" in conf_text:
        conf_text = conf_text.replace(
            "listen-on port 53 { 127.0.0.1; };",
            f"listen-on port 53 {{ 127.0.0.1; {IP_DNS}; }};"
        )

    # Ajustar allow-query
    if "allow-query" in conf_text:
        conf_text = conf_text.replace(
            "allow-query     { localhost; };",
            "allow-query     { localhost; any; };"
        )

    # Agregar zonas antes de include
    zone_block = f"""
zone "{DOMAIN}" IN {{
    type master;
    file "{ZONE_FILE.name}";
    allow-update {{ none; }};
}};

zone "{REVERSE_ZONE}" IN {{
    type master;
    file "{REVERSE_FILE.name}";
    allow-update {{ none; }};
}};
"""

    if ZONE_FILE.name not in conf_text:
        conf_text = conf_text.replace('include "/etc/', zone_block + '\ninclude "/etc/')

    NAMED_CONF.write_text(conf_text)


def verify_config():
    print("\n=== Verificando configuración de BIND ===")
    run_cmd("/usr/sbin/named-checkconf -z /etc/named.conf")


def start_services():
    print("\n=== Iniciando y habilitando servicio named ===")
    run_cmd("systemctl start named")
    run_cmd("systemctl enable named")
    run_cmd("systemctl status named --no-pager")


def test_queries():
    print("\n=== Realizando consultas de prueba ===")
    run_cmd(f"nslookup mail.{DOMAIN}")
    run_cmd(f"nslookup www.{DOMAIN}")
    run_cmd(f"nslookup ftp.{DOMAIN}")
    run_cmd(f"nslookup {IP_DNS}")


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
        print("2) Crear archivos de zona (directa e inversa)")
        print("3) Configurar named.conf")
        print("4) Verificar configuración")
        print("5) Iniciar y habilitar servicio named")
        print("6) Realizar consultas de prueba")
        print("7) Detener firewalld para pruebas")
        print("8) Ejecutar TODO en orden")
        print("9) Salir")

        choice = input("Selecciona una opción: ")

        if choice == "1":
            install_packages()
        elif choice == "2":
            create_zone_files()
        elif choice == "3":
            configure_named_conf()
        elif choice == "4":
            verify_config()
        elif choice == "5":
            start_services()
        elif choice == "6":
            test_queries()
        elif choice == "7":
            stop_firewalld()
        elif choice == "8":
            install_packages()
            create_zone_files()
            configure_named_conf()
            verify_config()
            start_services()
            test_queries()
            stop_firewalld()
            print("\n✅ Configuración completa ejecutada.")
        elif choice == "9":
            print("Saliendo...")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")
