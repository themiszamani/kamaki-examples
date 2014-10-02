from hashlib import new as newhashlib
from kamaki.clients.astakos import AstakosClient
from kamaki.clients.pithos import PithosClient
from progress.spinner import Spinner
from time import gmtime, strftime
import httplib
import random
import string
import time
import urlparse
from kamaki.clients import SilentEvent
from kamaki.clients import ClientError
from progress.spinner import Spinner
import requests
import sys
import argparse
import mimetypes
#import requests_ftp

try:
    from progress.bar import Bar

    def create_pb(msg):
        def generator(n):
            bar=Bar(msg)
            for i in bar.iter(range(int(n))):
                yield
            yield
        return generator
except ImportError:
    stderr.write('Suggestion: install python-progress\n')
    def create_pb(msg):
        return None

def parse_arguments(args):
    parser = argparse.ArgumentParser(description="Upload and download files")
    parser.add_argument("-t", "--typeof", type=str, default="downloadBig", dest="typeof",
                            help="type of action upload, uploadBfile, uploadurl, download,downloadBig")
    parser.add_argument("-u", "--url", type=str, default='', dest='url',
                            help="the url of the file to upload")
    parser.add_argument("-f", "--filename", type=str, default='', dest='filename',
                            help="the name of the file to download")
    parser.add_argument("-c", "--container", type=str, default='', dest='container',
                            help="the name of the container to upload to")
    args = parser.parse_args()
    print args
    if args.typeof=='downloadBig' and args.filename=='' and args.container=='': 
    	print >>sys.stderr, "The -f --filename, -c --container container name arguments is mandatory so as to download a file."
        parser.print_help()
        sys.exit(1)
    elif args.typeof=='download' and args.filename=='' and args.container=='': 
    	print >>sys.stderr, "The -f --filename, -c --container container name arguments is mandatory so as to download a file."
        parser.print_help()
        sys.exit(1)

    elif args.typeof=='upload' and args.container=='' and args.filename=='': 
    		print >>sys.stderr, "The -f --filename, -c --container container name arguments is mandatory so as to upload a file."
        	parser.print_help()
        	sys.exit(1)
    elif args.typeof=='uploadBfile' and args.container=='' and args.filename=='': 
    		print >>sys.stderr, "The -f --filename, -c --container container name arguments is mandatory so as to upload a file."
        	parser.print_help()
        	sys.exit(1)
    elif args.typeof=='uploadurl' and args.container=='' and args.url=='': 
    		print >>sys.stderr, "The -u --url, -c --container container name arguments is mandatory so as to upload a file."
        	parser.print_help()
        	sys.exit(1)

    return args

def stream(i,filenameToSave,bufs):
    with open(filenameToSave, "a") as f:
	    f.write(bufs[i])

def downloadAndSend(pithos,filename, CHUNK,filenameToSave,size):
    bufs={}
    print strftime("%Y-%m-%d %H:%M:%S", gmtime())
    start_time = time.time()
    test =  open(filenameToSave, 'w')
    for i in range(1 + (size / CHUNK)):
        from_size, to_size = CHUNK * i, min(CHUNK * (i + 1), size)
        buf_index = i % 2
        bufs[buf_index] = pithos.download_to_string(filename, range_str='%s-%s' % (from_size, to_size))
        if i and not proc.is_alive():
                proc.join()
        proc = SilentEvent(stream, buf_index,filenameToSave,bufs)
        proc.start()
    end_time = time.time()
    print("Elapsed time was %g seconds" % (end_time - start_time))

def download():

    '''
	Downloads chunk orf the object and write to a file. 
	The download_to_string method downloads a remote object from pithos into a
	string, which is then returned. Download an object to a string (multiple connections).
	This method uses threads for http requests, but stores all content in memory. 
	param obj: (str) remote object path, param range_str: (str) from, to are file positions (int) in bytes
    '''
    myRange = 0
    #write to local file
    print strftime("%Y-%m-%d %H:%M:%S", gmtime())
    start_time = time.time()
    test =  open(filenameToSave, 'w')
    while size >= myRange :
         from_size, to_size = myRange, (myRange+CHUNK)
	 block = pithos.download_to_string(filename, range_str = '%s-%s' % (from_size, to_size))
	 test.write(block)
 	 myRange = myRange + CHUNK
    end_time = time.time()
    print("Elapsed time was %g seconds" % (end_time - start_time))

def _pithos_hash(block, blockhash):
    '''
	Args:
          	block: The block of the object.
          	blockhash: The block hash algorithm
	Returns:
		the digest of the block passed to the update method
    '''
    #Secure hashes and message digests
    h = newhashlib(blockhash)
    #Update the hash object with the string. The block has been rstriped. It is a copy of the string in which all chars (\x00)
    #have been stripped from the end of the string 
    h.update(block.rstrip('\x00'))
    #Return the digest of the strings passed to the update() method so far,  as a string of double length, containing only hexadecimal digitse
    return h.hexdigest()

def uploadBfile(pithos,filename,meta,CHUNK):
    block_size = int(meta['x-container-block-size'])
    block_hash_algorithm = meta['x-container-block-hash']
    spinner = Spinner('Uploading blocks: ')
    filetoread = open(filename)
    hashes = []
    size = 0
    obj_name=filename
    while True:
        chunk = filetoread.read(block_size)
        if not chunk: break
        #create the block hash identifing the block content 
        hash_ = _pithos_hash(chunk, block_hash_algorithm)
	#append hashes for the final hashmap
        hashes.append(hash_)
        size += len(chunk)
	#put the chunk to pithos
        pithos._put_block(chunk, hash_)
        spinner.next()
	#create the final hashmap
        hashmap = dict(bytes=size, hashes=hashes)

    try:
	j=pithos.object_get(
        obj_name,
        format='json',
        hashmap=True,
	)
    except ClientError as e:
	try: 
		r = pithos.object_put(
		obj_name,
		format='json',
		hashmap=True,
		content_type= mimetypes.guess_type(filename)[0], 
		#con tent_encoding=r.encoding,
	#	if_etag_not_match='True',
		json=hashmap,
		success=201)
	except ClientError as e:
		print('Error: %s' % e)
		if e.status:
			print('- error code: %s' % e.status)
		if e.details:
			for detail in e.details:
				print('- %s' % detail)


def uploadurl(pithos,url,meta,CHUNK):
    '''
	Upload a big file to Pithos.
	Calculate the hash value for each block of the object to be uploaded.
    	Send a hashmap PUT request for the object. This is a PUT request with a hashmap request parameter appended to it. If the parameter is not present, the object's data (or part of it) is provided with the request. If the parameter is present, the object hashmap is provided with the request.
    	If the server responds with status 201 (Created), the blocks are already on the server and we do not need to do anything more.
    	If the server responds with status 409 (Conflict), the server's response body contains the hashes of the blocks that do not exist on the server. Then, for each hash value in the server's response (or all hashes together) send a POST request to the server with the block's data.
    '''
    #the obj name based on the url 
    obj_name=url.split("/")[-1:][0]
    # to know the size and the hash algorithm of the container
    block_size = int(meta['x-container-block-size'])
    block_hash_algorithm = meta['x-container-block-hash']
    spinner = Spinner('Uploading blocks: ')
    #In the event you are posting a very large file as a multipart/form-data request, you may want to stream the request.
    #If you want to do this, make sure you set stream=True in your initial request
    #verify  (optional) if True, the SSL cert will be verified. A CA_BUNDLE path can also be provided.
    #stream  (optional) if False, the response content will be immediately downloaded.
    r = requests.get(url, stream=True, verify=False)
    #r = urllib.urlretrieve(url, 'file')
    hashes = []
    size = 0
    #upload each chunk separatelry, create a hash for each block and append the hashmap
    #When you stream your data with stream=True, you should use a pattern like this to save what is being streamed. 
    for chunk in r.iter_content(block_size):
	print chunk
        #create the block hash identifing the block content 
        hash_ = _pithos_hash(chunk, block_hash_algorithm)
	#append hashes for the final hashmap
        hashes.append(hash_)
        size += len(chunk)

	#put the chunk to pithos
        pithos._put_block(chunk, hash_)
        spinner.next()
	#create the final hashmap
        hashmap = dict(bytes=size, hashes=hashes)
	print hashmap

    print hashmap
    print mimetypes.guess_type(url)[0]
    try:
	j=pithos.object_get(
        obj_name,
        format='json',
        hashmap=True,
	)
    except ClientError as e:
	try: 
		r = pithos.object_put(
		obj_name,
		format='json',
		hashmap=True,
		content_type= r.headers['content-type'] if mimetypes.guess_type(url)[0]=='None' else mimetypes.guess_type(url)[0], 
		content_encoding=r.encoding,
	#	if_etag_not_match='True',
		json=hashmap,
		success=201)
	except ClientError as e:
		print('Error: %s' % e)
		if e.status:
			print('- error code: %s' % e.status)
		if e.details:
			for detail in e.details:
				print('- %s' % detail)

def main():

    #AUTH_URL='https://accounts.okeanos.grnet.gr/identity/v2.0'
    #AUTH_TOKEN='YOUR TOKEN'
    AUTH_URL='https://accounts.demo.synnefo.org/identity/v2.0'
    AUTH_TOKEN='YOUR TOKEN'

    astakos = AstakosClient(AUTH_URL, AUTH_TOKEN)
    PITHOS_URL = astakos.get_service_endpoints('object-store')['publicURL']
    parts = urlparse.urlparse(PITHOS_URL) 
    pithos = PithosClient(PITHOS_URL, AUTH_TOKEN)
    pithos.account = astakos.user_info['id']

    """Parse arguments, use kamaki to create vm, setup using ssh"""
    args = parse_arguments(sys.argv[1:])
    print "type         ---",args.typeof
    print "url          ---",args.url
    print "file         ---",args.filename
    print "container    ---",args.container

    if (args.typeof=='uploadfile'):
	    filename = args.filename
	    container = args.container
	    pithos.container = container
	    # to know the block size and the hash algorithm 
	    #  To optimize for large files, allow pithos client to use multiple threads!
            #  pithos client will auto-adjust the number of threads, up to a limit
            pithos.MAX_THREADS = 5
	    print "Upload a large file to pithos"
            #  Now, large file upload will be optimized:
            with open(filename) as f:
           	 pithos.upload_object(filename,f,hash_cb=create_pb('Calculating hashes...'),upload_cb=create_pb('Uploading...'),content_type=mimetypes.guess_type(filename)[0])


    if (args.typeof=='uploadBfile'):
	    filename = args.filename
	    container = args.container
	    pithos.container = container
	    # to know the block size and the hash algorithm 
	    meta = pithos.get_container_info()
	    block_size = int(meta['x-container-block-size'])
	    CHUNK = block_size*4
	    filenameToSave = filename
	    uploadBfile(pithos,filename,meta,CHUNK)
    if (args.typeof=='uploadurl'):
	    url = args.url
	    container = args.container
	    pithos.container = container
	    # to know the block size and the hash algorithm 
	    meta = pithos.get_container_info()
	    block_size = int(meta['x-container-block-size'])
	    CHUNK = block_size*4
	    uploadurl(pithos,url,meta,CHUNK)

    if (args.typeof=='downloadBig'):
	    filename = args.filename
	    container = args.container
	    pithos.container = container
	    # to know the block size and the hash algorithm 
	    meta = pithos.get_container_info()
	    block_size = int(meta['x-container-block-size'])
	    CHUNK = block_size*4
	    ObjectData = pithos.get_object_info(filename)
	    size =  int(ObjectData['content-length'])
	    filenameToSave = filename
            downloadAndSend(pithos,filename, CHUNK,filenameToSave,size)
		
if __name__ == '__main__':
   sys.exit(main())

