# Starter showing configuration driven transformation

## Defaults
* Port: 5500 (--host=0.0.0.0 --port=5500) 
```bash
export CDA_HOST='http://localhost:8080'
export FLASK_APP=app
flask run -h 0.0.0.0 -p 5500
```



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

## Full container setup with networking after building everything
* Depends on: https://github.com/yohanswanepoel/camel-fhir
* Depends on: HAPI FHIR JPA
* change your message type endpoint to: http://f2c-demo-camel:8080/dynamicRoute

Access UI: http://127.0.0.1:5500/
```bash
podman network create demonet
podman run --rm --name f2c-demo-ui --network -e CAMEL_HOST="http://localhost:8080" demonet -p 5500:5000 localhost/f2c-demo-ui
```


Did you build the camel route container as per the instructions in: https://github.com/yohanswanepoel/camel-fhir ?
```bash
podman run --rm --name f2c-demo-camel --network demonet -p 8080:8080 -e env_xslhost="http://f2c-demo-ui:5000/api/xsl?name=" -e env_fhirhost="http://fhirhost:8080/fhir" -e env_cdahost="http://10.215.66.15:5500/cda_system" f2c-demo-camel
```

If you want the FHIR host: http://localhost:8090/
```bash
podman run --rm --name fhirhost --network demonet -p 8090:8080  hapiproject/hapi:latest
```

Cleaning it all up
```bash
podman stop f2c-demo-ui
podman stop f2c-demo-camel
podman stop fhirhost
podman network rm demonet
```


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

