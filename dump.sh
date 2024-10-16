docker exec opensweepmap-postgres-1 pg_dump -U joey -d sweepmaps -f /tmp/db_dump.sql
DUMP_FILENAME="sweepmaps_backup_$(date +%Y%m%d_%H%M%S).sql"
docker cp opensweepmap-postgres-1:/tmp/db_dump.sql ./$DUMP_FILENAME
aws s3 cp $DUMP_FILENAME s3://dunnie
rm $DUMP_FILENAME
echo "Successfully took a dump and uploaded it to s3://dunnie/$DUMP_FILENAME"
