============
rsync-backup
============

rsync-backup is a simple python application that takes a configuration
file with backup jobs that it uses to spawns multiple rsync processes
that simultaneously copies your data.

rsync-backup supports stepping into the sourcedirectory and spawning rsync
workers for subdirectories while keeping the same structure at the target.

Getting Started
---------------

See examples/config.yaml for example config which is executed with the
`rsync-backup` command.

Contributing
------------

TODO


License
-------

rsync-backup is free software and is licensed under Apache License, version 2.0.
