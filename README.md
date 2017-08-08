Suetonius
===========================================================
# Suetonius is meant to be a simple imageboard archiver. It
# identifies thread URLs from the catalog of multiple image
# boards and then downloads every thread in JSON format and
# tags them with metadata before storing them in MongoDB,
# This program is intended to be an uncomplicated way to hold
# imageboard comments for later processing or storage in an
# RDBMS. It currently supports 4chan, 8chan, lainchan, endchan
# 32chan and wizardchan. The config.ini variables are self-
# explanatory support can be added for any board that has either
# 'threads.json' or 'catalog.json' pages available.

Classes:
Request Handler
-------------------------------------------------------------
Container for requests objects. Makes HTTP requests for JSONs 
of the threadlist or catalog (not all image boards support the
threads.json functionality). This is also where we get each
individual 'thread.json' file.

Mongo Handler
--------------------------------------------------------------
Container method for MongoDB calls. This class exists for the
sake of tidyness.

Thread Processor
--------------------------------------------------------------
Class for any future plans for post-processing. Currently, the
only post processing is 'tagging' the thread JSONs. This is done
because their formats are not uniform across image boards, and
generally, you would want to be able to search on some basic
parameters, like thread id numbers, the board name, and last update.
Last update can be useful in that if it is concurrent with the last
run of the script, that is a reliable indication of a thread still
in the catalog.

What's next?
--------------------------------------------------------------
Presently, Suetonius has all the functionality I originally
wanted. If more complex post-processing is needed, that may be
included.
