# Use the official PostgreSQL image as the base image
FROM postgres

# Install PostGIS
RUN apt-get update && apt-get install -y postgis

# Add initialization scripts (if needed)
# COPY init-db.sh /docker-entrypoint-initdb.d/

# Expose the default PostgreSQL port
EXPOSE 5432