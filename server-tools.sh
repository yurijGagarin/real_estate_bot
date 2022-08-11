#!/bin/bash
# For autocomplete please run `complete -W "htop ssh start stop restart logs sync deploy autocomplete" server-tools.sh`
source .env || (echo "Can't find .env file" && exit 1)

if [ -z "${SERVER_NAME}" ]; then
    echo "Can't find SERVER_NAME env var"
    exit 1
fi

if [ -z "${PROJECT_NAME}" ]; then
    echo "Can't find PROJECT_NAME env var"
    exit 1
fi


if [ -z "${SERVER_DIR}" ]; then
    SERVER_DIR="~/$PROJECT_NAME"
fi

if [ -z "${COMPOSE_PROJECT_NAME}" ]; then
    COMPOSE_PROJECT_NAME="$PROJECT_NAME"
fi

SYNC_EXCLUDE=(.git node_modules .idea var/logs/* .DS_Store tmp venv __pycache__ **/dist **/node_modules .env *.sqlite)

if (( $# < 1 )); then
    echo -e "Illegal number of parameters. \nUsage sh tools.sh command"
    exit 1
fi

if [ "$1" = "show-config" ]; then
    echo "----"
    echo "CWD: $(pwd)"
    echo "SERVER_NAME: $SERVER_NAME"
    echo "PROJECT_NAME: $PROJECT_NAME"
    echo "SERVER_DIR: $SERVER_DIR"
    echo "----"
    exit 0
fi

echo "Connecting to $SERVER_NAME..."

case $1 in
    "" )
        echo "./server-tools.sh {command}"
        ;;
    "logs" )
        ssh $SERVER_NAME "cd $SERVER_DIR && docker-compose logs -f"
        ;;
    "ssh" )
        ssh $SERVER_NAME
        ;;
    "start" )
        ssh $SERVER_NAME "cd $SERVER_DIR && docker-compose start"
        ;;
    "stop" )
        ssh $SERVER_NAME "cd $SERVER_DIR && docker-compose stop"
        ;;
    "restart" )
        ssh $SERVER_NAME "cd $SERVER_DIR && docker-compose restart"
        ;;
    "htop" )
        ssh $SERVER_NAME -t  "htop -d 10"
        ;;
    "sync" )
        EXCLUDE=""
        for DIR in ${SYNC_EXCLUDE[@]}
        do
            EXCLUDE="$EXCLUDE --exclude=$DIR"
        done
        ssh $SERVER_NAME "mkdir -p $SERVER_DIR && cd $SERVER_DIR"
        rsync -avz $EXCLUDE . $SERVER_NAME:$SERVER_DIR
        ;;
    "deploy" )
        EXCLUDE=""
        for DIR in ${SYNC_EXCLUDE[@]}
        do
            EXCLUDE="$EXCLUDE --exclude=$DIR"
        done
        ssh $SERVER_NAME "mkdir -p $SERVER_DIR && cd $SERVER_DIR"
        rsync -avz $EXCLUDE . $SERVER_NAME:$SERVER_DIR
        ssh $SERVER_NAME "cd $SERVER_DIR && docker-compose build && docker-compose up -d"
        ;;
esac
