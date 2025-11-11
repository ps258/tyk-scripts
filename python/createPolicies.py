#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

description = "Will take the template or create a policy in memory, apply the name (if given) then add as many as required copies of it to the dashboard or gateway"

parser = argparse.ArgumentParser(description=f'{scriptName}: {description}')

DashboardOrGateway = parser.add_mutually_exclusive_group(required=True)
DashboardOrGateway.add_argument('--dashboard', '-d', dest='dshb', help="URL of the dashboard")
DashboardOrGateway.add_argument('--gateway', '-g', dest='gatw', help="URL of the gateway")

parser.add_argument('--apiid', '-a', required=True, dest='apiids', nargs='+', help="List of API IDs to be added to the policy")
parser.add_argument('--cred', '-c', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('--name', '-n', default="Default policy name", dest='name', help="Base name of policy")
parser.add_argument('--number', '-N', required=True, default=1, type=int, dest='toAdd', help="Numer of policies to generate")
parser.add_argument('--template', '-t', dest='templateFile', help="Policy template file")
parser.add_argument('--rate', '-r', default=-1, type=int, dest='rate', help="Set the rate limit")
parser.add_argument('--per', '-p', default=-1, type=int, dest='rateper', help="Set the rate limit period")
parser.add_argument('--quota', '-q', default=-1, type=int, dest='quotamax', help="Set the global quota")
parser.add_argument('--quotaperiod', '-R', default=-1, type=int, dest='quotaPeriod', help="Set the global quota renewal rate")
parser.add_argument('--partitions', '-P', default="", type=str, dest='partitions', help="Enable partitions. eg. quota,rate_limit,complexity,acl,per_api")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# create a new dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    tykInstance = tyk.gateway(args.gatw, args.auth)

# read the policy defn
if args.templateFile:
    policy = tyk.policy(args.templateFile)
else:
    policy = tyk.policy()

policy.setName(args.name)

for apiid in args.apiids:
    policy.addAPI(apiid)

if args.quotamax > -1:
    if args.quotaPeriod > -1:
        policy.setGlobalQuota(args.quotamax,args.quotaPeriod)
    else:
        print('[FATAL]--quotaPeriod must be specified when --quota is')
        sys.exit(1)

if args.rate > -1:
    if args.rateper > -1:
        policy.setRate(args.rate)
        policy.setPer(args.rateper)
    else:
        print('[FATAL]--per must be specified when --rate is')
        sys.exit(1)

if args.partitions != "":
    policy.setPartitions(args.partitions)

if args.verbose:
    print(policy)

numberCreated = tykInstance.createPolicies(policy, args.toAdd)

if numberCreated == args.toAdd:
    print(f'Success: {numberCreated} Policies created')
else:
    print(f'Failure: Only {numberCreated} of {args.toAdd} policies created')
    sys.exit(1)
