#!/usr/bin/python
import sys
#from progress.bar import Bar
import json
from kamaki.clients import ClientError
from kamaki.clients.astakos import AstakosClient
from kamaki.clients.pithos import PithosClient
from kamaki.cli.logger import deactivate
deactivate('kamaki.clients.send')
deactivate('kamaki.clients.recv')

#AUTHENTICATION_URL = 'https://accounts.okeanos.grnet.gr/identity/v2.0'
#TOKEN = 'YOUR TOKEN'
AUTHENTICATION_URL = 'https://accounts.demo.synnefo.org/identity/v2.0'
TOKEN = 'YOUR TOKEN'
SMALLFILE = 'A NAME OF A SMALL FILE (in test folder)'
BIGFILE = 'A NAME OF A BIG FILE (in test folder)'
TMPFILE = 'A NAME OF A TMP FILE (in test folder)'
FILETOPUBLISH = 'THE NAME OF THE FILE YOU WANT TO PUBLISH (in test folder)'
YOUR_CONTAINER = 'THE NAME OF THE CONTAINER WITH FOLDERS'
YOUR_FOLDER_PATH = 'THE FOLDER(S) PATH IN A CONTAINER'

try:
    from progress.bar import Bar

    def create_pb(msg):
        def generator(n):
            bar = Bar(msg)
            for i in bar.iter(range(int(n))):
                yield
            yield
        return generator
except ImportError:
    print >>sys.stderr, "Suggestion: install python-progress\n"

    def create_pb(msg):
        return None


def parseContainers(decoded_response):
    """
    function to parse the endpoints and get
    the publicURL of the selected service
    Args
        param decoded_response: (json) the json data
    Returns:
        a string with the containers
    """
    containers = []
    json.dumps(decoded_response, sort_keys=True,
               indent=4, separators=(',', ': '))
    jsonData = decoded_response
    for item in jsonData:
        name = item.get("name")
        containers.append(name)
        print "Container Name=", name
    return containers


def PrintContainerObjects(pithos, containerName, prefixName=None):
    """
    function to print the objects of a container
    Args
        param pithos: (object) initialization PithosClient
        param containerName: (string) the container name
        param prefixName: (string) Return objects starting with this
        prefix. It is actually the folder path of the object, used
        in pithos.list_objects.
   """
    pithos.container = containerName
    print "------------"
    print "Printing objects of container:", containerName
    obj_list = pithos.list_objects(prefix=prefixName)
    for obj in obj_list:
        print 'Name:  %s of %s bytes' % (obj['name'], obj['bytes'])


def main():
    #authenticate to Astakos
    print"---------------------------------------------------"
    print"******* Authenticating to Astakos******************"
    print"---------------------------------------------------"
    try:
        my_astakos_client = AstakosClient(AUTHENTICATION_URL,
                                          TOKEN)
        my_accountData = my_astakos_client.authenticate()
        ACCOUNT_UUID = my_accountData['access']['user']['id']
        print "Status: Authenticated"
    except ClientError:
        print"Failed to authenticate user token"

    print"\n"
    print"---------------------------------------------------"
    print"**********Getting Endpoints for pithos*************"
    print"---------------------------------------------------"
    #get endpoint url
    try:
        endpoints = my_astakos_client.get_service_endpoints('object-store')
        PITHOS_URL = endpoints['publicURL']
        print "The public URL:", PITHOS_URL
    except ClientError:
        print "Failed to get endpoints for pithos"

    print"\n"
    print"---------------------------------------------------"
    print"**********Authenticating to Pithos*****************"
    print"---------------------------------------------------"
    #Initialize pithos client
    try:
        pithos = PithosClient(PITHOS_URL, TOKEN)
        pithos.account = ACCOUNT_UUID
        pithos.container = ''
    except ClientError:
        print "Failed to initialize Pithos+ client"

    print"\n"
    print"---------------------------------------------------"
    print"**********LIST ALL CONTAINERS IN YOUR ACCOUNT******"
    print"---------------------------------------------------"
    #list all containers
    try:
        container_list = pithos.list_containers()
        containers = parseContainers(container_list)
        ContNums = len(containers)
        print "The number of Containers in your account:", ContNums
        print "The containers are"
        print ','.join(containers)
    except ClientError:
        print"Error in container list"

    print"\n"
    print"---------------------------------------------------"
    print"******LIST OBJECTS OF A FOLDER IN A CONTAINER******"
    print"---------------------------------------------------"
    #list all containers
    try:
        PrintContainerObjects(pithos, YOUR_CONTAINER,
                              prefixName=YOUR_FOLDER_PATH)
    except ClientError:
        print"Error in listing folder objects"

    print"\n"
    print"---------------------------------------------------"
    print"**********Print objects for all containers*********"
    print"---------------------------------------------------"

    try:
        for i in range(len(containers)):
            PrintContainerObjects(pithos, containers[i])
    except ClientError as e:
        print('Error: %s' % e)
        if e.status:
            print('- error code: %s' % e.status)
        if e.details:
            for detail in e.details:
                print('- %s' % detail)

    #  Create and set a different container than pithos
    print "Create a new container - my container"
    CONTAINER = 'my container'
    pithos.create_container(CONTAINER)
    pithos.container = CONTAINER

    print"\n"
    print"---------------------------------------------------"
    print"**********UPLOAD AND DOWNLOAD**********************"
    print"---------------------------------------------------"
    """
    B. UPLOAD AND DOWNLOAD
    """
    print "Upload a small file to pithos"
    #  Upload a small file
    print './test/'+SMALLFILE
    with open('./test/'+SMALLFILE) as f:
        pithos.upload_object(SMALLFILE, f)

    print "Download a small file from pithos and store to string"
    print SMALLFILE
    FILETOSTRING = pithos.download_to_string(SMALLFILE,
                                             download_cb=
                                             create_pb('Downloading...'))
    print "Small file string:", FILETOSTRING
    #To optimize for large files, allow pithos client
    # to use multiple threads! pithos client will
    # auto-adjust the number of threads, up to a limit
    pithos.MAX_THREADS = 5
    print "Upload a large file to pithos"
    #  Now, large file upload will be optimized:
    #  dd if=/dev/zero of=test/large.txt count=8 bs=1073741824
    with open('./test/'+BIGFILE) as f:
        pithos.upload_object(BIGFILE, f,
                             hash_cb=create_pb('Calculating hashes...'),
                             upload_cb=create_pb('Uploading...'))

    print "Create my own metadata for object"
    tags = {}
    tags['mytag'] = 12
    pithos.set_object_meta(BIGFILE, tags)
    myOwnMetadataObject = pithos.get_object_meta(BIGFILE)
    print "Object Metatadata", myOwnMetadataObject
    print "Download a large file from pithos"
    #  Download a file (btw, MAX_THREADS are still 5)
    with open('./test/'+TMPFILE, 'wb+') as f:
        pithos.download_object(BIGFILE, f,
                               download_cb=create_pb('Downloading...'))

    #  HIGHLIGHTS: If parts of the file are already uploaded or downloaded,
    #  corresponding methods will transfer only the missing parts!
    print"\n"
    print"---------------------------------------------------"
    print"**********CREATE A NEW CONTAINER AND MOVE OBJECT***"
    print"---------------------------------------------------"

    """ Create a new container and move object"""
    print "Create a new container - containerToCopy"
    CONTAINERNEW = 'containertocopy'
    pithos.create_container(CONTAINERNEW)
    pithos.move_object(CONTAINER, SMALLFILE, CONTAINERNEW, SMALLFILE)
    print"\n"
    print"---------------------------------------------------"
    print"**********DELETE AND RECOVER***********************"
    print"---------------------------------------------------"
    """
    C. DELETE AND RECOVER
    """
    #  Delete a file
    pithos.container = CONTAINER
    pithos.delete_object(BIGFILE)
    #  Recover file
    file_versions = pithos.get_object_versionlist(BIGFILE)
    print "The file versions"
    for data in file_versions:
        print "The value of id=", data[0], "date=", data[1]

    first_version = file_versions[0]
    v_id, v_date = first_version
    pithos.copy_object(CONTAINER, BIGFILE,
                       CONTAINER, BIGFILE,
                       source_version=v_id)

    print"\n"
    print"---------------------------------------------------"
    print"**********GET FILE DETAILS************************"
    print"---------------------------------------------------"
    objectDetails = pithos.get_object_info(BIGFILE)
    for obj in objectDetails:
        print "The value of", obj, "=", objectDetails.get(obj)

    print"\n"
    print"---------------------------------------------------"
    print"**********SHARING AND PUBLISHING*******************"
    print"---------------------------------------------------"
    """
    D. SHARING AND PUBLISHING
    """
    #  Read permission to all pithos users
    pithos.set_object_sharing(FILETOPUBLISH, read_permission='*')

    #  Publish and get public URL
    pithos.publish_object(FILETOPUBLISH)
    print "Get sharing and public information"
    #  Get sharing and public information
    info = pithos.get_object_info(FILETOPUBLISH)
    for data in info:
        print "The value of", data, "=", info.get(data)

    sharing = info.get('x-object-sharing', {})
    print sharing

    public = info.get('x-object-public', None)
    print "The public URL=", public
    print "Remove sharing and publishing"
    #  Remove sharing and publishing
    pithos.del_object_sharing(FILETOPUBLISH)
    pithos.unpublish_object(FILETOPUBLISH)

    print "Get sharing and public information"
    #  Get sharing and public information
    info = pithos.get_object_info(FILETOPUBLISH)
    sharing = info.get('x-object-sharing', {})
    public = info.get('x-object-public', None)
    print "The public URL=", public

if __name__ == "__main__":
    sys.exit(main())
