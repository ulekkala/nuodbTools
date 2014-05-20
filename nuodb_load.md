## Using `nuodb_load.py`:
This is a rudimentary NuoDB load generation script which uses the python driver to execute some SQL on a NuoDB cluster. It is not a benchmarking tool, just a validation one. The load generator has two modes: random queries and sql file.

* Random Queries
 * The file will create a table on the database called "LOADERX" where X is a number corresponding to the load thread. Each thread will the execute a series of SELECT:INSERT:UPDATE:DELETE sql queries determined by the ratio flag (by default 5:2:1:1) on that table. Each thread will run for a duration of seconds (by default 10) before it is killed.

* SQL File
  * By passing in a text file of SQL commands this script will have each thread execute the SQL file in order. Please be aware that some write transactions will fail due to transactional overlap. When using this mode the Random Query fields described above are ignored. Each thread will run the file as quickly as possible and then exit.

<pre>
usage: nuodb_load.py [-h] -db DATABASE -b BROKER -u USER -p PASSWORD
                     [-t THREADS] [-f FILE] [-d DURATION] [-s SCHEMA]
                     [-r RATIO] [--initial-rows INITIAL_ROWS]
                     [--data-length VALUE_LENGTH]

optional arguments:
  -h, --help            show this help message and exit
  -db DATABASE, --database DATABASE
                        Target database
  -b BROKER, --broker BROKER
                        A running broker in the domain
  -u USER, --user USER  Database username
  -p PASSWORD, --password PASSWORD
                        Database Password
  -t THREADS, --threads THREADS
                        Number of parallel connections
  -f FILE, --file FILE  SQL file to use as import. Otherwise random queries are generated
  -d DURATION, --duration DURATION
                        Random queries: How many seconds to run
  -s SCHEMA, --schema SCHEMA
                        What DB schema to use
  -r RATIO, --ratio RATIO
                        Random queries: Ratio of SELECT:INSERT:UPDATE:DELETE
  --initial-rows INITIAL_ROWS
                        Random queries: Each connection pre-populates a table with a certain number of random data rows. This is how many rows to insert at start.
  --data-length VALUE_LENGTH
                        Random queries: Each row has a random string of the length defined here as a value
<pre>