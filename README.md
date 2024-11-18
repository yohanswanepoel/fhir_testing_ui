# Starter showing configuration driven transformation

## Defaults
* Port: 5500

## Things to know
* Dynamic Routes in Camel: dynamicRoute: /api/xsl?name={FHIR Resource}
* Dynamic Routes in Camel with routing: {TODO}
* Patient only route: validate

## TODO
* Build containers

## Usage
* UI to create message types
* Message types can then have messages to test and send to Camel
* Message types can have transforms to serve to Camel 

## Getting message type transform
* curl "localhost:5500/api/xsl?name=Patient"


## containers

* TODO: Think about Podman network

Building for testing on mac
```bash
podman build . -t f2c-demo-ui
podman run --rm --name f2c-demo-ui -p 5500:5000 localhost/f2c-demo-ui
```

Building to push to x86 repo
```bash
podman build . -t f2c-demo-ui --platform linux/amd64
```