`py-doc tools build --ca-file FILE` copies a certificate here for the build, so apt, npm and pip work
behind a proxy that re-signs TLS. Nothing else belongs in this folder.
