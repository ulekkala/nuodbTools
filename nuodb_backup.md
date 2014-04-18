## Using `nuodb_backup.py`:
* This script currently supports 3 types of backups
  * [EBS](http://aws.amazon.com/ebs/) snapshot (AWS specific)
  * [ZFS](http://en.wikipedia.org/wiki/ZFS) snapshot
  * Backup via tarball
* When creating your domain you should pay particular attention to how often you would like to back up the database. This will inform the way you run your [Storage Managers](http://doc.nuodb.com/display/doc/About+the+NuoDB+Architecture)

### How backups work in NuoDB
A backup of the database at a given time can be achieved by capturing a consistent version of all the atom states on disk for a Storage Manager (SM) all at once. You can do this by:
1. Stopping the SM - thereby stopping any atoms from changing on disk - then copying all the bits to another location (the tarball method). Simply copying files out from underneath a running SM will result in inconsistent file state and a corrupt database.
2. Running the SM on a block device that has point-in-time snapshot capability, like EBS, ZFS or a number of other vendor specific platforms. 
  * Because you are capturing all writes on disk at a given moment the database will be consistent. 
  * It is possible to run the journal and archive on two different block devices. However the downside of doing this is that the SM process will still need to be stopped to maintain consistency between the journal and archive. This is faster than the tarball method - taking block snapshots is usually a very fast process- however a SM will still be down for that duration.

You should always run more than one storage manager on a production database for reliability. If you are also going to be using the tarball method of backup then you may want to run more and two- since it will require you to stop one for the duration of the backup.

### Running the command
`usage: nuodb_backup.py [-h] -a {backup,restore,list} -db DATABASE --host HOST
                       --rest-url REST_URL --rest-username REST_USERNAME
                       --rest-password REST_PASSWORD [--aws-key AWS_KEY]
                       [--aws-secret AWS_SECRET] [--aws-region AWS_REGION]
                       [--ssh-username SSH_USERNAME] [--ssh-key SSH_KEYFILE]
                       [--backup-type {ebs,tarball,zfs}]
                       [--tarball-dest TARBALL_DESTINATION]
                       [--comment COMMENT]
                       [--db-user DB_USER] [--db-password DB_PASS]`

### Backing up & restoring a database to a point-in-time for selective recovery
* EBS Snapshots
  * These require your AWS credentials to interface directly with the AWS API
  * The SSH user should have passwordless sudo privileges (it mounts and unmounts volumes)
  * Backing Up a database
`./nuodb_backup.py -a backup -db mydb --host hostRunningNuoDBStorageManager --rest-url http://hostRunningNuoDBautoConsole.com:8888/api/ --rest-username domain --rest-password bird --aws-key MyAWSKey --aws-secret MyAWSSecret --aws-region us-east-1 --ssh-username ec2-user --ssh-key /my/ssh/private/key/on/local/machine [--comment mySpecialBackupName]`
  * Restoring a database
`./nuodb_backup.py -a restore -db mydb --host hostToRestoreTo --rest-url http://hostRunningNuoDBautoConsole.com:8888/api/ --rest-username domain --rest-password bird --aws-key MyAWSKey --aws-secret MyAWSSecret --aws-region us-east-1 --ssh-username ec2-user --ssh-key /my/ssh/private/key/on/local/machine --db-user dba --db-pass dba`
    * Choose a backup from the existing choices
    * A SM and TE will be started on the host you specify with the database snapshot running as {database}_{timestamp} where timestamp=the time the backup was taken.
    * To support more load you can start more TEs and SMs using the NuoDB console or the `nuodbmgr` command line tool
* Tarball backup
  * The SSH user should have read and write access to the directory where the SM is writing as well as the tarball destination directory
  * Backing up a database
`nuodb_backup.py -a backup -db mydb --host hostRunningNuoDBStorageManager --rest-url http://hostRunningNuoDBautoConsole.com:8888/api/ --rest-username domain --rest-password bird --ssh-username user --ssh-key /my/ssh/private/key/on/local/machine --tarball-dest /target/directory
  * Restoring a database
`nuodb_backup.py -a restore -db mydb --host hostRunningNuoDBStorageManager --rest-url http://hostRunningNuoDBautoConsole.com:8888/api/ --rest-username domain --rest-password bird --ssh-username user --ssh-key /my/ssh/private/key/on/local/machine --tarball-dest /source/tarball/directory --db-user dba --db-pass dba`
