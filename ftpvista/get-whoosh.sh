#!/bin/bash
#
# Install Whoosh into the local repository.

set -e

if [[ -e whoosh ]]; then
  echo "Whoosh already installed."
  exit 42
fi

svn co http://svn.whoosh.ca/projects/whoosh/trunk/src/whoosh/ whoosh
