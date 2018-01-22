from exploit import start_tunna_server, upload_tunna_socks
from config import config

if __name__ == '__main__':
    # Setup connection
    upload_tunna_socks(config['verbose'])
    start_tunna_server(config['verbose'])
