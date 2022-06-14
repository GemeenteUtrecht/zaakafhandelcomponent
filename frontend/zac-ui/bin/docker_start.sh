#!/bin/sh

# Set environment variables.
export EXISTING_VARS=$(printenv | awk -F= '{print $1}' | sed 's/^/\$/g' | paste -sd,);

# Replace environment variables in source files.
for i in `grep -r '\$ALFRESCO_' /apps/zac-ui/ --files-with-match`; do cat $i | envsubst $EXISTING_VARS | tee $i; done

nginx -g "daemon off;"
