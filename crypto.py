import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def generate_ecdh_keypair():
    """Generates an ephemeral ECDH private key and serializes its public key."""
    private_key = ec.generate_private_key(ec.SECP384R1())
    public_key = private_key.public_key()
    
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_key, base64.b64encode(public_bytes).decode('utf-8')

def derive_aes_key(private_key, peer_public_b64):
    """Derives a 32-byte AES key given our private key and peer's public key string."""
    if not peer_public_b64:
        raise ValueError("Peer public key is missing")
        
    peer_bytes = base64.b64decode(peer_public_b64)
    peer_public_key = serialization.load_pem_public_key(peer_bytes)
    
    shared_key = private_key.exchange(ec.ECDH(), peer_public_key)
    
    # Derive a 32-byte key for AES-256
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'udp_file_transfer_aes_key',
    ).derive(shared_key)
    
    return derived_key

def encrypt_chunk(aes_key, seq_num, data):
    """Encrypts a chunk with zero padding overhead using AES-CTR mode."""
    if not aes_key:
        return data
    nonce = (0).to_bytes(12, 'big') + seq_num.to_bytes(4, 'big')
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(nonce))
    encryptor = cipher.encryptor()
    return encryptor.update(data) + encryptor.finalize()

def decrypt_chunk(aes_key, seq_num, cipher_data):
    """Decrypts a chunk. AES-CTR encryption is symmetrical to decryption."""
    if not aes_key:
        return cipher_data
    nonce = (0).to_bytes(12, 'big') + seq_num.to_bytes(4, 'big')
    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(nonce))
    decryptor = cipher.decryptor()
    return decryptor.update(cipher_data) + decryptor.finalize()
