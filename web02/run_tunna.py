from exploit import start_tunna_server, upload_tunna_socks
from config import config

if __name__ == '__main__':
    print "Setup connection"
    if config['upload_tunna']:
        upload_tunna_socks()
    if config['use_tunna_server']:
        start_tunna_server()