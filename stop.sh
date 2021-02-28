#!/bin/sh

/usr/bin/docker kill --signal="SIGINT" papycast > /dev/null
/usr/bin/docker stop -t 30 papycast > /dev/null
/usr/bin/docker rm papycast > /dev/null
