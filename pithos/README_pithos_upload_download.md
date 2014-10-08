pithos examples
========
Python and kamaki script with pithos examples for uploading and downloading files 

Python 2.7.5+
Kamaki 0.13

### Prerequisites
Install python and kamaki on  the machine you want to run the examples.
 
### Run command 

```bash
python pithos_upload_download.py -t  uploadBfile -f 26mb.zip -c pithos

-t, default="downloadBig","type of action upload, uploadBfile, uploadurl,download,downloadBig"
-u, "the url of the file to upload"
-f, "the name of the file to download"
-c, "the name of the container to upload"
```

### Python script

#### Main Vars

- AUTH_URL='https://accounts.okeanos.grnet.gr/identity/v2.0' or 
	'https://accounts.demo.synnefo.org/identity/v2.0' if you have an account a demo.synnefo.org
- AUTH_TOKEN=OKEANOS TOKEN


### Pithos upload - download  Examples

- upload method in general  
	Calculate the hash value for each block of the object to be uploaded.
    Send a hashmap PUT request for the object. This is a PUT request
    with a hashmap request parameter appended to it. If the parameter is
    not present, the object's data (or part of it) is provided with the
    request. If the parameter is present, the object hashmap
    is provided with the request.
    
    if the server responds with status 201 (Created), the blocks are
    already on the server and we do not need to do anything more.
    If the server responds with status 409 (Conflict), the server's response
    body contains the hashes of the blocks that do not exist on the server.
    Then, for each hash value in the server's response (or all hashes together)
    send a POST request to the server with the block's data.
	

	- uploadfile: Upload a big selected file 
	- uploadURL : Upload a big file to Pithos from a url. 
	
- download : Makes use of the standard download_object with the use of threads
- downloadBig: Downloads chunk of the object and write to a file.
    The download_to_string method downloads a remote object from pithos into a
    string, which is then returned. Download an object to a string
    (multiple connections).This method uses threads for http requests,
    but stores all content in memory.
- downloadSendBig: make use of the same methods as downloadBig, but with the use 
	of the SilentEvent Thread-run method of kamaki sends the downloaded block 
	to a third client.  
