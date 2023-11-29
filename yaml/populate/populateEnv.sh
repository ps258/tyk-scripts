#!/bin/bash

# script to publish APIs and policies into a namespace which are linked to the named operator context

# parameters 
# -K Context (kubectl context)
# -N Namespace to publish APIs into
# -c operator context name
# -n namespace the context is in
# -b the name to give the APIs and policies (defaults to httpbin)
# -r number to create (defaults to 10)

SCRIPTNAME=$0
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:$PATH
SCRIPTDIR=$(
  cd "$(dirname $SCRIPTNAME)"
  echo $PWD
)

cd $SCRIPTDIR

APINAME=httpbin
POLICYNAME=$APINAME
COUNT=10

function help {
	echo "$0.sh -K kubectl_context -N Namespace_to_publish_CRDs_to -c Operator_context_name -n Namespace_containing_operatorcontext -b api/profile_base_name -r number_of_items_to_create"
}

while getopts :K:N:c:n:b:r: arg
do
  case $arg in
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

# create a portal config so that the portal will work

yq '.spec.contextRef.name = "'$OPERATORCONTEXT'"' -i PortalConfig.yaml
yq '.spec.contextRef.namespace = "'$OPERATORNAMESPACE'"' -i PortalConfig.yaml
kubectl apply -f PortalConfig.yaml -n $CRDNAMESPACE

API_YAML=ApiDefinition.yaml
POLICYL_YAML=SecurityPolicy.yaml
DESCRIPTION_YAML=APIDescription.yaml
PORTALCATALOGUE_YAML=PortalAPICatalogue.yaml
FIRST=1
for i in $(seq 1 $COUNT); do
	# API
	yq '.spec.contextRef.name = "'$OPERATORCONTEXT'"' -i $API_YAML
	yq '.spec.contextRef.namespace = "'$OPERATORNAMESPACE'"' -i $API_YAML
	yq '.spec.name = "'$APINAME$i'"' -i $API_YAML
	yq '.metadata.name = "'$APINAME$i'"' -i $API_YAML
	yq '.spec.proxy.listen_path = "/'$APINAME$i'/"' -i $API_YAML
	yq '.spec.proxy.target_url = "http://httpbin.org/anything/'$i'/"' -i $API_YAML
	kubectl apply -f $API_YAML -n $CRDNAMESPACE --cluster=$KUBECONTEXT
done

for i in $(seq 1 $COUNT); do
	# Policy
	yq '.spec.contextRef.name = "'$OPERATORCONTEXT'"' -i $POLICYL_YAML
	yq '.spec.contextRef.namespace = "'$OPERATORNAMESPACE'"' -i $POLICYL_YAML
	yq '.spec.name = "'$APINAME$i'"' -i $POLICYL_YAML
	yq '.metadata.name = "'$APINAME$i'"' -i $POLICYL_YAML
	yq '.spec.access_rights_array.[0].name = "'$APINAME$i'"' -i $POLICYL_YAML
	yq '.spec.access_rights_array.[0].namespace = "'$CRDNAMESPACE'"' -i $POLICYL_YAML
	kubectl apply -f $POLICYL_YAML -n $CRDNAMESPACE --cluster=$KUBECONTEXT
done

for i in $(seq 1 $COUNT); do
  # API description
	yq '.spec.contextRef.name = "'$OPERATORCONTEXT'"' -i $DESCRIPTION_YAML
	yq '.spec.contextRef.namespace = "'$OPERATORNAMESPACE'"' -i $DESCRIPTION_YAML
	yq '.spec.name = "sample API description '$APINAME$i'"' -i $DESCRIPTION_YAML
	yq '.metadata.name = "sample-api-description-'$APINAME$i'"' -i $DESCRIPTION_YAML
	yq '.spec.policyRef.name = "'$APINAME$i'"' -i $DESCRIPTION_YAML
	yq '.spec.policyRef.namespace = "'$OPERATORNAMESPACE'"' -i $DESCRIPTION_YAML
	kubectl apply -f $DESCRIPTION_YAML -n $CRDNAMESPACE --cluster=$KUBECONTEXT
done

for i in $(seq 1 $COUNT); do
  # Portal API Catalogue
	yq '.spec.contextRef.name = "'$OPERATORCONTEXT'"' -i $PORTALCATALOGUE_YAML
	yq '.spec.contextRef.namespace = "'$OPERATORNAMESPACE'"' -i $PORTALCATALOGUE_YAML
	yq '.metadata.name = "sample-portal-api-catalogue"' -i $PORTALCATALOGUE_YAML
  if [[ $FIRST -eq 1 ]]; then
    yq '.spec.apis = [{"apiDescriptionRef": {"name": "sample-api-description-'$APINAME$i'", "namespace": "'$CRDNAMESPACE'"}}]' -i $PORTALCATALOGUE_YAML
    FIRST=2
  else
    yq '.spec.apis += [{"apiDescriptionRef": {"name": "sample-api-description-'$APINAME$i'", "namespace": "'$CRDNAMESPACE'"}}]' -i $PORTALCATALOGUE_YAML
  fi
done
# apply the catalogue after everything so that it's only done once with all APIs in it
kubectl apply -f $PORTALCATALOGUE_YAML -n $CRDNAMESPACE --cluster=$KUBECONTEXT
