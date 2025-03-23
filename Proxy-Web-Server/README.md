## Instructions to run project
### Web Server
Run the web server with
```shell
python webserver.py
```
and connect to the web server at http://localhost:8080/ from the same device.

You can test GET requests for a few content types with buttons in the HTML.

### Proxy Server
Run the proxy server with
```shell
python proxyserver.py
```
and connect to the proxy server at http://localhost:8080/ from the same device.

Proxy server can only handle one request at a time and the status is displayed in the terminal.

### Working Websites
* http://gaia.cs.umass.edu/wireshark-labs/HTTP-wireshark-file2.html
* http://gaia.cs.umass.edu/wireshark-labs/HTTP-wireshark-file3.html
* http://gaia.cs.umass.edu/wireshark-labs/HTTP-wireshark-file4.html
* http://gaia.cs.umass.edu/wireshark-labs/HTTP-wireshark-file5.html

### Libraries
* os
  * Used to create cache folder

