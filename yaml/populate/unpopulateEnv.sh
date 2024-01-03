#!/bin/bash

# script to publish APIs and policies into a namespace which are linked to the named operator context

# parameters 
# -K Context (kubectl context)
# -N Namespace to publish APIs into
# -c operator context name
# -n namespace the context is in
# -b the name to give the APIs and policies (defaults to httpbin)
# -r number to create (defaults to 10)
# -G CE gateway mode (no catalogue etc)

SCRIPTNAME=$0
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:$PATH
SCRIPTDIR=$(
  cd "$(dirname $SCRIPTNAME)"
  echo $PWD
)

cd $SCRIPTDIR

KUBECONTEXT=minikube
GATEWAY_MODE=
APINAME=httpbin
POLICYNAME=$APINAME
COUNT=10

function help {
	echo "$0.sh -K kubectl_context -N Namespace_to_publish_CRDs_to -c Operator_context_name -n Namespace_containing_operatorcontext -b api/profile_base_name -r number_of_items_to_create"
}

while getopts :GK:N:c:n:b:r: arg
do
  case $arg in
    G)
      GATEWAY_MODE=TRUE
      ;;
    K)
      KUBECONTEXT=$OPTARG
      ;;
    N)
      CRDNAMESPACE=$OPTARG
      ;;
    c)
      OPERATORCONTEXT=$OPTARG
      ;;
    n)
      OPERATORNAMESPACE=$OPTARG
      ;;
  r)
      COUNT=$OPTARG
      ;;
    b)
			APINAME=$OPTARG
      POLICYNAME=$APINAME
      ;;
    :)
      echo "Option -$OPTARG requires an arguement."
      exit 1
      ;;
    \?)
      echo "Invalid option: -$OPTARG"
      exit 1
      ;;
  esac
done

if [[ -z $KUBECONTEXT || -z $CRDNAMESPACE || -z $OPERATORCONTEXT || -z $OPERATORNAMESPACE ]]; then
  help
  exit 1
fi

API_YAML=ApiDefinition.yaml
POLICYL_YAML=SecurityPolicy.yaml
DESCRIPTION_YAML=APIDescription.yaml
PORTALCATALOGUE_YAML=PortalAPICatalogue.yaml
FIRST=1

if [[ -z $GATEWAY_MODE ]]; then
	# delete the portal catalogue
	kubectl delete portalapicatalogue.tyk.tyk.io/sample-portal-api-catalogue -n $CRDNAMESPACE --cluster=$KUBECONTEXT
	# delete the portal config
	kubectl delete portalconfig.tyk.tyk.io/sample-portal-config -n $CRDNAMESPACE --cluster=$KUBECONTEXT
fi

for i in $(seq 1 $COUNT); do
  # delete API descriptions
	kubectl delete apidescription.tyk.tyk.io/sample-api-description-$APINAME$i -n $CRDNAMESPACE --cluster=$KUBECONTEXT
done

for i in $(seq 1 $COUNT); do
	# delete policies
	kubectl delete securitypolicy.tyk.tyk.io/$APINAME$i -n $CRDNAMESPACE --cluster=$KUBECONTEXT
done

for i in $(seq 1 $COUNT); do
	# delete APIs
	kubectl delete apidefinition.tyk.tyk.io/$APINAME$i -n $CRDNAMESPACE --cluster=$KUBECONTEXT
done

# show the results
kubectl api-resources --verbs=list --namespaced -o name | grep tyk | xargs -n 1 kubectl get --show-kind --ignore-not-found -n $CRDNAMESPACE --cluster=$KUBECONTEXT
