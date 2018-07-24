.. _command:

Command-line
------------

The package also installs a command line tool: `epicsarchiver`

It can be used to send a list of PVs to archive (from CSV files).

::

    $ epicsarchiver --hostname archiver-01.example.com archive file1.archive file2.archive


The files shall be in CSV format (space separated) and include:
 
  - PV name
  - sampling period (optional). Set to 1 second by default.
  - sampling method SCAN|MONITOR (optional). Set to MONITOR by default.

Here is an example::

    # PV name  Sampling period  Sampling method
    CrS-ACCP:CRYO-GT-34884:Val 30 monitor
    # Comments are allowed
    CrS-TICP:Cryo-TE-33483:Val 5.0 SCAN
    CrS-TICP:Cryo-TT-21220:Val 10
    CrS-TICP:Cryo-TE-31459B:Val


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
      --period TEXT            Sampling period in seconds to use if not provided
                               in the archive file [default: 1]
      --method [MONITOR|SCAN]  Sampling method to use if not provided in the
                               archive file [default: MONITOR]
      --help                   Show this message and exit.

