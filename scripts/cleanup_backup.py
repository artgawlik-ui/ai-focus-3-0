"""Szyfrowanie lokalnych artefaktów. Nie odczytuje sekretów ani konfiguracji."""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from scripts.backup import derive

HEADER=b'FOCUS3C1'

def encrypt(data,passphrase,kind):
    if len(passphrase)<20 or kind not in ('archive','undo'):raise ValueError('invalid_backup_parameters')
    salt=os.urandom(16);nonce=os.urandom(12)
    return HEADER+salt+nonce+AESGCM(derive(passphrase,salt)).encrypt(nonce,data,('focus3-cleanup:'+kind).encode())

def decrypt(data,passphrase,kind):
    if len(passphrase)<20 or kind not in ('archive','undo') or data[:8]!=HEADER or len(data)<52:raise ValueError('invalid_backup_parameters')
    return AESGCM(derive(passphrase,data[8:24])).decrypt(data[24:36],data[36:],('focus3-cleanup:'+kind).encode())
