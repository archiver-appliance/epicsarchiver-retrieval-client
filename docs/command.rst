.. _command:

Command-line
------------

The package also installs a command line tool: `epicsarchiver`

It can be used to send a list of PVs to archive or to rename (from CSV files).

archive command
~~~~~~~~~~~~~~~

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
      archive  Archive all PVs included in the files passed as parameters
      rename   Rename all PVs included in the files passed as parameters


    $ epicsarchiver archive --help
    Usage: epicsarchiver archive [OPTIONS] [FILES]...

      Archive all PVs included in the files passed as parameters

    Options:
      --appliance TEXT  Force PVs to be archived on the specified appliance (in a
                        cluster)
      --help            Show this message and exit.
        Usage: epicsarchiver archive [OPTIONS] [FILES]...


rename command
~~~~~~~~~~~~~~~

Each PV will be paused, renamed and resumed. The old name remains paused.

::

    $ epicsarchiver --hostname archiver-01.example.com rename file1 file2


The files shall be in CSV format (space separated) and include the current PV name
and the new one.
Empty lines and lines starting with "#" (comments) are allowed.

Here is an example::

    # PV current name                 new name
    ISrc-010:PwrC-CoilPS-01:CurS ISrc-010:PwrC-CoilPS-02:CurS
    ISrc-010:PwrC-CoilPS-01:CurR ISrc-010:PwrC-CoilPS-02:CurR
    # Comments are allowed
    LEBT-010:Vac-VCG-30000:PrsStatR LEBT-010:Vac-VCG-30001
