#!/root/rest_ssh/bin/python3
# -*- codign: utf-8

import click
import argparse
import shlex
import os
import sys
from yaml import safe_load as yamlload
from yaml.scanner import ScannerError
import logging
import pexpect
from OpenSSL import crypto

logging.basicConfig(
    format = '%(asctime)s - %(levelname)s - %(message)s',
    level = logging.INFO,
    filename = "rest_ssh.log")

console = logging.StreamHandler()
console.setLevel(logging.ERROR)
formatter = logging.Formatter('%(message)s')
console.setFormatter(formatter)
logging.root.addHandler(console)

configfile = "/root/rest_ssh/config.yml"

def iterate_list(l):
    """
    Перебрать последовательность (исключая строки) поэлемено,
    или же возвращает последовательность из одно элемента

    l1 = 1
    l2 = [1,2]
    for x in iterate_list(l1):
        print x

    :param l: Список, кортеж, или прочее
    :return:
    """
    if not isinstance(l, str):
        for x in l:
            yield x
    else:
        yield l

@click.group()
def master():
    pass

def rcupdate(action, services):
    @click.argument('service')
    def wrapper(service):
        if service == "list":
            print("\n".join(services))
            logging.info("Display {}able services".format(action))
            sys.exit(0)
        if service not in services:
            logging.error("{} {} is unavailable".format(action.capitalize(),
                                                             service))
            sys.exit(1)
        pr = pexpect.spawn("/etc/init.d/{}".format(service), [action])
        exitcode = pr.wait()
        if exitcode == 0:
            logging.info("Success {} service: {}".format(action, service))
        else:
            logging.error("Failed to {} service {}: {}".format(action, service, pr.read()))
        sys.exit(exitcode)
    return wrapper

def updatecert(sites):
    @click.argument('site')
    def wrapper(site):
        if site == "list":
            print("\n".join(sites))
            logging.info("Display site list for certificates")
            sys.exit(0)
        if site not in sites:
            logging.error("Certificate site is unavailable: {}".format(site))
            sys.exit(1)
        try:
            certificatepem = sys.stdin.read()
            crypto.load_certificate(crypto.FILETYPE_PEM, certificatepem)
            for fn in iterate_list(sites[site]):
                with open(fn, 'w') as f:
                    f.write(certificatepem)
        except Exception as e:
            logging.error("Certificate update for {} error: {}".format(site, str(e)))
            sys.exit(1)

        logging.info("Success update certificate for site: {}".format(site))
        sys.exit(0)
    return wrapper

def updatepem(sites):
    @click.argument('site')
    def wrapper(site):
        if site == "list":
            print("\n".join(sites))
            logging.info("Display site list for PEM")
            sys.exit(0)
        if site not in sites:
            logging.error("PEM site is unavailable: {}".format(site))
            sys.exit(1)
        try:
            pemdata = sys.stdin.read()
            crypto.load_privatekey(crypto.FILETYPE_PEM, pemdata)
            crypto.load_certificate(crypto.FILETYPE_PEM, pemdata)
            for fn in iterate_list(sites[site]):
                with open(fn, 'w') as f:
                    f.write(pemdata)
        except Exception as e:
            logging.error("PEM update for {} error: {}".format(site,str(e)))
            sys.exit(1)

        logging.info("Success update PEM for site: {}".format(site))
        sys.exit(0)
    return wrapper

def updateprivkey(sites):
    @click.argument('site')
    def wrapper(site):
        if site == "list":
            print("\n".join(sites))
            logging.info("Display site list for private key")
            sys.exit(0)
        if site not in sites:
            logging.error("Private key site is unavailable: {}".format(site))
            sys.exit(1)
        try:
            keypem = sys.stdin.read()
            crypto.load_privatekey(crypto.FILETYPE_PEM, keypem)
            for fn in iterate_list(sites[site]):
                with open(fn, 'w') as f:
                    f.write(keypem)
        except Exception as e:
            logging.error("Private key update for {} error: {}".format(site,str(e)))
            sys.exit(1)

        logging.info("Success update private key for site: {}".format(site))
        sys.exit(0)
    return wrapper

def main():
    ssh_args = shlex.split(os.environ.get("SSH_ORIGINAL_COMMAND",""))
    try:
        with open(configfile) as f:
            config = yamlload(f.read())
    except (ScannerError, FileNotFoundError) as e:
        logging.error("Failed to parse config: {}".format(str(e)))
        print("Service unavailable")
        sys.exit(1)
    for action in config['actions']:
        if action == 'certificate':
            master.command("privkey")(
                updateprivkey({k:v['privkey']
                for k,v in config['actions']['certificate'].items()
                if 'privkey' in v
                }))
            master.command("fullchain")(
                updatecert({k:v['cert']
                for k,v in config['actions']['certificate'].items()
                if 'cert' in v
                }))
            master.command("pem")(
                updatepem({k:v['pem']
                for k,v in config['actions']['certificate'].items()
                if 'pem' in v
                }))
        else:
            master.command(action)(rcupdate(action, config['actions'][action]))
    
    master(args=ssh_args)

if __name__ == '__main__':
    main()
