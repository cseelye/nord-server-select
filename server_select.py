#!/usr/bin/env python3

from urllib import parse
from pyapputil.appframework import PythonApp
from pyapputil.appconfig import appconfig
from pyapputil.argutil import ArgumentParser
from pyapputil.logutil import GetLogger
from pyapputil.netutil import DownloadFile
from pyapputil.typeutil import ValidateAndDefault, StrType, PositiveNonZeroIntegerType, GPSLocationType, OptionalValueType

from geopy.distance import distance
import json
import os
from tempfile import NamedTemporaryFile

@ValidateAndDefault({
    "location": (GPSLocationType(), None),
    "country": (StrType(allowEmpty=False), appconfig["country"]),
    "max_distance": (PositiveNonZeroIntegerType(), appconfig["max_distance"]),
    "max_load": (PositiveNonZeroIntegerType(), appconfig["max_load"]),
    "count": (PositiveNonZeroIntegerType(), appconfig["count"]),
    "output_file": (OptionalValueType(), None),
    "server_file": (OptionalValueType(), None),
    "server_stats_file": (OptionalValueType(), None),
})
def select(location, country, max_distance, max_load, count, output_file, server_file, server_stats_file):
    log = GetLogger()

    # Load the server list/stats from file if requested
    if server_file and server_stats_file:
        with open(server_file, "r") as fh:
            server_list = json.load(fh)
        with open(server_stats_file, "r") as fh:
            server_stats = json.load(fh)
    # Otherwise fetch the server list/file
    else:
        with NamedTemporaryFile() as srv, NamedTemporaryFile() as srv_stat:
            log.info("Downloading server list/stats")
            DownloadFile("https://nordvpn.com/api/server", srv.name)
            DownloadFile("https://nordvpn.com/api/server/stats", srv_stat.name)
            server_list = json.load(srv)
            server_stats = json.load(srv_stat)

    # Filter list to US servers
    start_len = len(server_list)
    filtered_servers = [s for s in server_list if s["flag"] == country]
    end_len = len(filtered_servers)
    log.info("Filtered out {} non-{} servers".format(start_len - end_len, country))

    # Filter list to standard VPN servers
    start_len = len(filtered_servers)
    standard_servers = []
    for idx in range(len(filtered_servers)):
        srv = filtered_servers[idx]
        categories = {
            "standard": False,
            "p2p": False
        }
        for cat in srv["categories"]:
            if cat["name"] == "Standard VPN servers":
                categories["standard"] = True
            elif cat["name"] == "P2P":
                categories["p2p"] = True
        if categories["standard"] and categories["p2p"]:
            standard_servers.append(srv)
    filtered_servers = standard_servers
    end_len = len(filtered_servers)
    log.info("Filtered out {} non-standard servers".format(start_len - end_len))

    # Filter by features
    start_len = len(filtered_servers)
    required_features = {
        "openvpn_udp" : True
    }
    for feature_name, feature_value in required_features.items():
        filtered_servers = [s for s in filtered_servers if s["features"].get(feature_name, None) == feature_value]   
    end_len = len(filtered_servers)
    log.info("Filtered out {} non-OpenVPN servers".format(start_len - end_len))

    # Calculate distance to each server
    for srv in filtered_servers:
        srv_location = srv["location"]["lat"], srv["location"]["long"]
        srv_distance = distance(location, srv_location)
        srv["location"]["distance"] = srv_distance.miles

    # Get the load for each server
    for srv in filtered_servers:
        srv["load"] = 999
        if srv["domain"] in server_stats:
            srv["load"] = server_stats[srv["domain"]]["percent"]

    # Sort by load and distance
    filtered_servers = sorted(filtered_servers, key=lambda x:(x["load"],x["location"]["distance"]))

    # Filter by max distance
    start_len = len(filtered_servers)
    filtered_servers = [s for s in filtered_servers if s["location"]["distance"] < max_distance]
    end_len = len(filtered_servers)
    log.info("Filtered out {} servers with distance too far".format(start_len - end_len))

    # Filter by max load
    start_len = len(filtered_servers)
    filtered_servers = [s for s in filtered_servers if s["load"] < max_load]
    end_len = len(filtered_servers)
    log.info("Filtered out {} servers with load too high".format(start_len - end_len))

    log.info("Selecting from {} servers".format(len(filtered_servers)))
    selected_servers = filtered_servers[:count]

    output = json.dumps(selected_servers, indent=4, sort_keys=True)
    if output_file:
        with open(output_file, "w") as fh:
            fh.write(output)
    else:
        log.raw(output)


if __name__ == "__main__":

    parser = ArgumentParser(description="Select a NordVPN server endpoint")
    parser.add_argument("-g", "--location", type=GPSLocationType(), default=appconfig["location"], help="GPS location, to determine server distance")
    parser.add_argument("-c", "--country", type=StrType(allowEmpty=False), default=appconfig["country"], help="country for the VPN endpoint")
    parser.add_argument("-m", "--max-distance", type=PositiveNonZeroIntegerType(), default=appconfig["max_distance"], metavar="MILES", help="max distance for a VPN endpoint (miles)")
    parser.add_argument("-l", "--max-load", type=PositiveNonZeroIntegerType(), default=appconfig["max_load"], metavar="PERCENT", help="max load for a VPN endpoint")
    parser.add_argument("-n", "--count", type=PositiveNonZeroIntegerType(), default=appconfig["count"], help="number of servers to include")
    parser.add_argument("-o", "--output-file", type=StrType(allowEmpty=False), default=None, metavar="FILE", help="file to write server selection to. If not specified it is printed to stdout")
    parser.add_argument("--server-list", type=StrType(allowEmpty=False), default=None, metavar="FILE", help="file containing server list. If not specified the most current one will be downloaded")
    parser.add_argument("--server-stats", type=StrType(allowEmpty=False), default=None, metavar="FILE", help="file containing server stats list. If not specified the most current one will be downloaded")
    args = parser.parse_args_to_dict()

    # Must specify neither or both server_list and server_stats 
    server_list = args.get("server_list", False)
    server_stats = args.get("server_stats", False)
    if any([server_list, server_stats]) and not all([server_list, server_stats]):
        parser.error("server_list and server_stats must be used together")

    app = PythonApp(select, timer=False)
    app.Run(**args)
