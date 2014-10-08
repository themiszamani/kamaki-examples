Create VM examples
========
Python and kamaki script 

Python 2.7.5+
Kamaki 0.13

### Prerequisites
Install python and kamaki on  the machine you want to run the examples.
Create an admin folder so as to save the data for the vm creation 
 
### Run command 

```bash
python createvm.py -c 2 -m 2048 -d 10 -s drbd

-c, choices=[1, 2, 4, 8], "The number of CPU cores"
-m, choices=[512, 1024, 2048, 4096, 8192], "The memory size"
-d, choices=[5, 10, 20, 40], "The disk size"
-s, choices=["drbd", "ext_archipelago"], "The storage type"
-i, default='Debian Base', "the image name (e.g. Debian Base)"
-n, "The vm name"

### Python script

#### Main Vars


- AUTHENTICATION_URL='https://accounts.okeanos.grnet.gr/identity/v2.0' or 
	'https://accounts.demo.synnefo.org/identity/v2.0' if you have an account a demo.synnefo.org
- TOKEN=OKEANOS TOKEN
- DEFAULT_PREFIX= A default name for the new vm

### Description 

This example creates a new vm.
It parses the args and checks the quotas left so as
to ensure the creation. Then, it creates a floating_ip
and creates the vm. Every action is logged at example.log
and a file is saved at admin folder with the characteristics
of the new vm. 
If you want to automatically delete the new created vm uncomment
the last lines. 

