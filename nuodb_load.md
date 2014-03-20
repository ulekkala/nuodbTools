## Using `nuodb_load.py`:
* This script does random SELECT/INSERT/UPDATE/DELETES on a running nuodb cluster in a ratio defined by the user
* It is not efficient and should not be used for anything other than driving simple load.

`usage: nuodb_load.py [-h] -db DATABASE -b BROKER -u USER -p PASSWORD
                     [-t THREADS] [-d DURATION] [-s SCHEMA] [-r RATIO]
                     [--initial-rows INITIAL_ROWS]
                     [--data-length VALUE_LENGTH]`