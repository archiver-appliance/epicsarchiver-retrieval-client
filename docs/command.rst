.. _command:

Command-line
------------

The package also installs a command line tool: `epicsarchiver`

It can be used to send a list of PVs to archive (from CSV files).

::

    $ epicsarchiver --hostname archiver-01.example.com archive file1.archive file2.archive


The files shall be in CSV format (space separated) and include one PV name per line.
A file can also include the name of the policy to force (optional).
Empty lines and lines starting with "#" (comments) are allowed.

Here is an example::

    # PV name    Policy
    ISrc-010:PwrC-CoilPS-01:CurS
    ISrc-010:PwrC-CoilPS-01:CurR slow
    # Comments are allowed
    LEBT-010:Vac-VCG-30000:PrsStatR


The "slow" policy will be forced for the second PV.
Check the help for more information::

    $ epicsarchiver --help
    Usage: epicsarchiver [OPTIONS] COMMAND [ARGS]...

    Options:
      --version        Show the version and exit.
      --hostname TEXT  Achiver Appliance hostname or IP [default: localhost]
      --debug          Enable debug logging
      --help           Show this message and exit.

    Commands:
      archive  Archive all PVs included in the files passed...


    $ epicsarchiver archive --help
    Usage: epicsarchiver archive [OPTIONS] [FILES]...

      Archive all PVs included in the files passed as parameters

    Options:
      --help  Show this message and exit.
