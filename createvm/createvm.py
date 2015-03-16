#!/usr/bin/python
import logging
import sys
import argparse
from datetime import datetime

import json
from kamaki.clients import ClientError
from kamaki.clients.astakos import AstakosClient
from kamaki.clients.cyclades import CycladesClient
from kamaki.clients.compute import ComputeClient
from kamaki.clients.cyclades import CycladesNetworkClient
#help(AstakosClient)

#AUTHENTICATION_URL = 'https://accounts.okeanos.grnet.gr/identity/v2.0/'
#TOKEN = 'YOUR TOKEN'
AUTHENTICATION_URL = 'https://accounts.demo.synnefo.org/identity/v2.0'
TOKEN = 'YOUR TOKEN'
DEFAULT_PREFIX = "createVmTest"
logging.basicConfig(filename='example.log',
                    level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')
logging.debug('Start writing to log file')
logging.info('Started vm creation')


def parse_arguments(args):
    """
    function to parse the input arguments
    """

    parser = argparse.ArgumentParser(description="Create vm")
    parser.add_argument("-c", "--cpu", type=int,
                        choices=[1, 2, 4, 8], dest="cpuid",
                        help="Choose number of CPU cores")
    parser.add_argument("-m", "--memory", type=int,
                        choices=[512, 1024, 2048, 4096, 8192],
                        dest="memory", help="Choose memory size")
    parser.add_argument("-d", "--disk", type=int,
                        choices=[5, 10, 20, 40], dest='disk',
                        help="Choose disk size")
    parser.add_argument("-s", "--storage", type=str,
                        choices=["drbd", "ext_archipelago"],
                        dest='storage', help="Choose storage type")
    parser.add_argument("-i", "--image",
                        type=str, default='Debian Base', dest='image',
                        help="image name (e.g. Debian Base)")
    parser.add_argument("-n", "--name", type=str, default=DEFAULT_PREFIX,
                        dest='name',
                        help="New machine name")
    args = parser.parse_args()
    logging.info('Asked for a Vm with CPU=%s MEMORY= %s ',
                 args.cpuid, args.memory)
    logging.info('DISK=%s STORAGE=%s IMAGE=%s NAME=%s',
                 args.disk, args.storage, args.image, args.name)

    if args.disk is None:
        print >>sys.stderr, "The -d --disk argument is mandatory."
        parser.print_help()
        sys.exit(1)
    if args.cpuid is None:
        print >>sys.stderr, "The -c --cpu argument is mandatory."
        parser.print_help()
        sys.exit(1)
    if args.memory is None:
        print >>sys.stderr, "The -m --memory argument is mandatory."
        parser.print_help()
        sys.exit(1)
    if args.storage is None:
        print >>sys.stderr, "The -s --storage argument is mandatory."
        parser.print_help()
        sys.exit(1)
    if args.name is None:
        print >>sys.stderr, "The -n --name argument is mandatory."
        parser.print_help()
        sys.exit(1)

    return args


def authenticate_clients():
    """
    function to instantiate Clients (astakos, cyclades, compute)
    """
    try:
        astakos_client = AstakosClient(AUTHENTICATION_URL,
                                       TOKEN)
        astakos_client.authenticate()
        logging.info('Successful authentication')
    except ClientError:
        logging.info('\n Failed to authenticate user token')
        print 'Failed to authenticate user token'
    try:
        endpoints = astakos_client.get_endpoints()
        cyclades_base_url = parse_astakos_endpoints(endpoints,
                                                  'cyclades_compute')
        cyclades_network_base_url = parse_astakos_endpoints(endpoints,
                                                          'cyclades_network')

    except ClientError:
        print('Failed to get endpoints for cyclades')
    try:
        cyclades_client = CycladesClient(cyclades_base_url, TOKEN)
        compute_client = ComputeClient(cyclades_base_url, TOKEN)
        network_client = CycladesNetworkClient(cyclades_network_base_url,
                                               TOKEN)
        return cyclades_client, compute_client, network_client, astakos_client
    except ClientError:
        print 'Failed to initialize Cyclades client'


def parse_network(decoded_response, itemToSearch):
    """function to parse the endpoints and get the
    publicURL of the selected service
    """

    jsonData = decoded_response
    for item in jsonData:
        networkId = item.get("id")
    return networkId


def check_all_quotas(quotas, tocheck):
    """
    function to check the quotas left
    @ the selected to check service
    Args
        param quotas: (json) all data
        param tocheck: string the service to check (cyclades.vm)
    Return
        the quotas left
    """

    for item in quotas:
        valueToCheck = quotas.get(item)
        limitCheck = valueToCheck.get(tocheck).get("limit")
        UsageCheck = valueToCheck.get(tocheck).get("usage")
        limit = 0 if limitCheck is None else limitCheck
        usage = 0 if UsageCheck is None else UsageCheck
        ToCheckResult = limit - usage

        return ToCheckResult


def parse_astakos_endpoints(decoded_response, itemToSearch):
    """
    function to parse the endpoints and get the publicURL
    endpoint of the selected service
    Args
        decoded_response : (json) the json data
        itemToSearch: (string) the selected service
    Return
        PUBLIC_URL string the public endpoint of the service
    """
    json.dumps(decoded_response, sort_keys=True,
               indent=4, separators=(',', ': '))
    jsonData = decoded_response["access"]['serviceCatalog']
    for item in jsonData:
        name = item.get("name")
        endpoints = item.get("endpoints")
        for details in endpoints:
            PUBLIC_URL = details.get("publicURL")
            if name == itemToSearch:
                return PUBLIC_URL


def get_image_id(compute_client, image_name):
    """ gets list of images from compute client
    then pick the one we need
    Args
        compute_client: (object) the computeClient initialization
        image_name: (string) the image name
    Return
        -1 or the image id if exists
    """
    images = compute_client.list_images()

    for image in images:
        if image['name'] == image_name:
            return image['id']
    return -1


def get_flavor_id(compute_client, args):
    """ gets full flavor list from compute client
    then synthesized name to pick
    Args
        compute_client: (object) the computeClient initialization
        args: the input args
    Return
        -1 or the flavor id if exists
    """
    name = 'C'+str(args.cpuid)+'R'+str(args.memory)
    name = name+'D'+str(args.disk)+args.storage
    flavors = compute_client.list_flavors()
    for flavor in flavors:
        if flavor['name'] == name:
            return flavor['id']
    return -1


def get_floating_ip(network_client, IpCheck):
    """
    get a floating ip to attach to the newly created
    server. Gets the floating ip list , checks if
    there is an available one. If no , creates a new
    one,
    Args
        compute_client: (object) the computeClient initialization
        ipCheck : (int) the num of remaining ips
    Returns
        the json of the floating ip
    """

    try:
        allIps = network_client.list_floatingips()
    except Exception:
        print('Failed to list ips')
        exit()

    
    foundIP = 0
    NewIP = None
    networkID = None
    #check if there is a free ip so as to use
    for ip in allIps:
        if ip['instance_id'] is None:
            NewIP = ip
            foundIP = 1
            break
    print NewIP
    if IpCheck > 0 and foundIP == 0:
        if NewIP:
            networkID = ip['floating_network_id']
        try:
            NewIP = network_client.create_floatingip(networkID)
        except:
            print('get_floating_ip - Failed to create a new ip')
            exit()
    return NewIP


def main():
    """Parse arguments, use kamaki to create vm, setup using ssh"""

    args = parse_arguments(sys.argv[1:])
    print "name   ", args.name
    print "image  ", args.image
    print "storage", args.storage
    print "cpu    ", args.cpuid
    print "memory ", args.memory
    print "disk   ", args.disk

    # Get a cyclades and a compute client
    cyclades, compute, network_client, astakos_client = authenticate_clients()
    allQuotas = astakos_client.get_quotas()

    VmCheck = check_all_quotas(allQuotas, 'cyclades.vm')
    print "Vm left:", VmCheck
    if VmCheck == 0:
        print "ERROR - No VM available in the pool"
        return 1

    IpCheck = check_all_quotas(allQuotas, 'cyclades.floating_ip')
    floatingIP = get_floating_ip(network_client, IpCheck)
    if IpCheck == 0 and floatingIP is None:
        print "ERROR - No IP available in the pool"
        return 1
    DiskCheck = check_all_quotas(allQuotas, 'cyclades.disk')
    print "DiskCheck availability", DiskCheck
    print "disk   ", args.disk
    if DiskCheck < 1024*1024*1024*8*args.disk:
        print "ERROR - The disk is not available"
        return 1

    RamCheck = check_all_quotas(allQuotas, 'cyclades.ram')
    print "RamCheck availability", RamCheck
    if RamCheck < args.memory:
        print "ERROR - The selected number of memory are not available"
        return 1
    CPUCheck = check_all_quotas(allQuotas, 'cyclades.cpu')
    print "CPUCheck availability", CPUCheck
    if CPUCheck < args.cpuid:
        print "ERROR - The selected number of CPU are not available"
        return 1

    # Create a file to store the root password for later use
    pass_fname = 'admin/adminPass'+str(datetime.now())[:19].replace(' ', '')
    adminPass_f = open(pass_fname, 'w')

    # select a flavor
    flavor_id = get_flavor_id(compute, args)
    print "The flavor id =", flavor_id

    # select debian base id
    img_id = get_image_id(compute, args.image)
    print "The image id =", img_id

    print "The floating ip =", floatingIP['floating_ip_address']
    # Create VM
    network = {'uuid': floatingIP['floating_network_id'],
               'floating_ip_address': floatingIP['floating_ip_address']}
    network_list = []
    network_list.append(network)

    try:
        r = cyclades.create_server(args.name, flavor_id,
                                   img_id, None, None, network_list)
        # wait until the creation of vm
        cyclades.wait_server(r['id'])
        print "\nMachine [", r['name'], "] has been created", r['created']
        print "\t", r['metadata']['os'], "::"
        print "\t", r['metadata']['users'], "::", r['adminPass']
        # save admin password
        mypass = r['adminPass']
        adminPass_f.write('machine = %s, password = %s\n'
                          % (floatingIP, mypass))
        print "Finished vm creation"
    except:
        print "Error while creating vm"

    #Uncomment if you want to instantly delete vm
    #after its creation
    #if r['id']:
     #  cyclades.delete_server(r['id'])
if __name__ == "__main__":
    sys.exit(main())
