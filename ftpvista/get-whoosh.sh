#!/bin/bash
#
# Install Whoosh into the local repository.

set -e

if [[ -e whoosh ]]; then
  echo "Whoosh already installed."
  exit 42
fi

hg clone http://bitbucket.org/mchaput/whoosh whoosh.git