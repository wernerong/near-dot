"""Create an isolated test CA/server chain without inheriting host OpenSSL defaults."""
from pathlib import Path
import subprocess
import sys
import tempfile


def create(root):
    names = ['ca.cnf', 'ca.key', 'ca.pem', 'tls.key', 'server.csr', 'server.ext', 'server.pem', 'ca.srl']
    if any((root / name).exists() for name in names):
        raise SystemExit('Refusing to overwrite existing certificate material.')
    (root / 'ca.cnf').write_text(
        '[req]\nprompt=no\ndistinguished_name=dn\nx509_extensions=ca\n'
        '[dn]\nCN=Near Dot ephemeral test CA\n'
        '[ca]\nbasicConstraints=critical,CA:TRUE,pathlen:0\n'
        'keyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n'
    )
    (root / 'server.ext').write_text(
        'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\n'
        'extendedKeyUsage=serverAuth\nsubjectAltName=IP:127.0.0.1\n'
        'subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n'
    )
    def run(args):
        subprocess.run([str(arg) for arg in args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-sha256', '-nodes', '-config', root/'ca.cnf', '-keyout', root/'ca.key', '-out', root/'ca.pem', '-days', '2'])
    run(['openssl', 'req', '-new', '-newkey', 'rsa:2048', '-sha256', '-nodes', '-config', root/'ca.cnf', '-keyout', root/'tls.key', '-out', root/'server.csr', '-subj', '/CN=127.0.0.1'])
    run(['openssl', 'x509', '-req', '-sha256', '-in', root/'server.csr', '-CA', root/'ca.pem', '-CAkey', root/'ca.key', '-CAcreateserial', '-out', root/'server.pem', '-days', '1', '-extfile', root/'server.ext'])
    run(['openssl', 'verify', '-CAfile', root/'ca.pem', '-purpose', 'sslserver', root/'server.pem'])
    if sys.platform == 'darwin':
        # Evaluate with Apple's actual TLS policy, without changing any keychain.
        run(['security', 'verify-cert', '-c', root/'server.pem', '-r', root/'ca.pem', '-p', 'ssl', '-s', '127.0.0.1'])
    print('Isolated TLS certificate chain verified; system trust unchanged.')


if __name__ == '__main__':
    if len(sys.argv) == 2:
        create(Path(sys.argv[1]))
    elif len(sys.argv) == 1:
        with tempfile.TemporaryDirectory(prefix='neardot-tls-check-') as directory:
            create(Path(directory))
    else:
        raise SystemExit('Provide an empty test certificate directory, or no arguments for a self-test.')
