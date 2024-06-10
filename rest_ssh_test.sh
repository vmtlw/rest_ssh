#!/bin/bash

# Logging setup
LOGFILE="rest_ssh.log"
exec 3>&1 1>>"${LOGFILE}" 2>&1

log_info() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - $1"
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - $1" >&2
}

CONFIGFILE="/root/rest_ssh/config.yml"

iterate_list() {
    local list="$1"
    if [[ "$list" =~ ^\[.*\]$ ]]; then
        echo "${list:1:-1}" | tr ',' '\n'
    else
        echo "$list"
    fi
}

rcupdate() {
    local action="$1"
    shift
    local services=("$@")
    local service="$1"

    if [ "$service" == "list" ]; then
        printf "%s\n" "${services[@]}"
        log_info "Display ${action}able services"
        exit 0
    fi

    if [[ ! " ${services[*]} " =~ " ${service} " ]]; then
        log_error "${action^} ${service} is unavailable"
        exit 1
    fi

    /etc/init.d/"$service" "$action"
    exitcode=$?

    if [ $exitcode -eq 0 ]; then
        log_info "Success ${action} service: ${service}"
    else
        log_error "Failed to ${action} service ${service}"
    fi
    exit $exitcode
}

updatecert() {
    local sites=("$@")
    local site="$1"

    if [ "$site" == "list" ]; then
        printf "%s\n" "${!sites[@]}"
        log_info "Display site list for private key"
        exit 0
    fi

    if [ -z "${sites[$site]}" ]; then
        log_error "Private key site is unavailable: ${site}"
        exit 1
    fi

    keypem=$(cat)

    for fn in $(iterate_list "${sites[$site]}"); do
        echo "$keypem" > "$fn"
    done

    log_info "Success update private key for site: ${site}"
    exit 0
}

main() {
    if [ ! -f "$CONFIGFILE" ]; then
        log_error "Config file not found: $CONFIGFILE"
        echo "Service unavailable" >&3
        exit 1
    fi

    config=$(<"$CONFIGFILE")
    declare -A actions
    eval $(echo "$config" | yq eval '.actions | to_entries | .[] | @sh "actions[\(.key)]=\(.value)"')

    ssh_args=($(echo $SSH_ORIGINAL_COMMAND))

    for action in "${!actions[@]}"; do
        if [ "$action" == "certificate" ]; then
            declare -A certs
            eval $(echo "$config" | yq eval '.actions.certificate | to_entries | .[] | @sh "certs[\(.key)]=\(.value)"')
            for site in "${!certs[@]}"; do
                cert="${certs[$site]}"
                updatecert "$cert"
            done
        else
            rcupdate "$action" "${actions[$action]}"
        fi
    done
}

main "$@"
