#!/bin/bash

# This script is meant to be called by the "script" step defined in
# .travis.yml.

check_error()
{
    local last_exit_code=$1
    local last_cmd=$2
    if [[ ${last_exit_code} -ne 0 ]]; then
        echo "${last_cmd} exited with code ${last_exit_code}"
        echo "TERMINATING TEST"
        exit 1
    else
        echo "${last_cmd} completed successfully"
    fi
}

# Install PyRDF
python setup.py install --user 

# Run tests
# -x exit instantly on first error or failed test
# -v increase verbosity
pytest -x -v
check_error $? "pytest"

# Run tutorials
echo "======== Running Spark tutorials ======== "

# Run Spark tutorials locally
for filename in ./tutorials/spark/df*.py
do
	echo " == Running $filename == "
	python "$filename" &> /dev/null
  check_error $? "$filename"
done
