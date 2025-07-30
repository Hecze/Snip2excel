#!/usr/bin/env python3
"""
Script para generar una clave de encriptación segura para Fernet.
Ejecuta este script una vez para obtener tu clave de encriptación.
"""

from cryptography.fernet import Fernet
import base64

def generate_encryption_key():
    """Genera una clave de encriptación segura para Fernet"""
    # Generar una clave aleatoria de 32 bytes
    key = Fernet.generate_key()
    
    # Convertir a string para usar en el código
    key_string = key.decode()
    
    print("=" * 60)
    print("CLAVE DE ENCRIPTACIÓN GENERADA")
    print("=" * 60)
    print()
    print("Copia esta clave y reemplázala en config_manager.py:")
    print()
    print(f'ENCRYPTION_KEY = "{key_string}"')
    print()
    print("=" * 60)
    print("IMPORTANTE:")
    print("- Guarda esta clave en un lugar seguro")
    print("- No la compartas con nadie")
    print("- Si pierdes esta clave, no podrás desencriptar las API keys guardadas")
    print("=" * 60)
    
    return key_string

if __name__ == "__main__":
    generate_encryption_key() 