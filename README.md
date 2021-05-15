nord-server-select
===
Select a VPN endpoint from the NordVPN list of servers based on distance and load.

The recommended way to run the tool is using the container:
```
docker image build -t vpn-select .
docker container run --rm vpn-select -h
```
Use the location flag to pass in your GPS coords, or the script will use the geographic center of the US lower 48 by default.
You can change the default value/set any of the commandline flags by creating a userconfig.yml file with the value of the flag in it. For example:

```
location: (41.878100, -87.629800)
max_load: 30
```
Map your config file into the container to be used when you run:

`docker container run --rm -v $(pwd)/userconfig.yml:/userconfig.yml vpn-select`
