Download your Aiven MySQL service's CA certificate (Aiven's dashboard has a
download button for it, usually labeled "CA Certificate") and save it here
as `ca.pem`. Then set DB_SSL_CA=certs/ca.pem in your environment variables.
