#!/bin/bash

# assumes local mongo with no auth requirements

if [[ $# -lt 2 ]]
then
  echo "[FATAL]Usage $0 <start epoch end> <end epoch second>"
  echo "Summarises Errors by API between timestamps"
  exit 1
fi

alias mongo-command="mongo --quiet --host 10.0.0.21 --port 7003"

db.tyk_analytics.aggregate([
   { $match: { timestamp: { $gte: new Date(1634601600000), $lte: new Date(2635379140000) } } },
   { $sort: { apiname: -1 } }, 
   { $group: { _id: { ResponseCode: "$total.responsecode" }, Hits: { $sum: "$total.errorlist.count" }, Error: { $sum: "$total.errorlist.count" } } }
]);

