#!/bin/bash
psql -d bokcirkel
psql -d bokcirkel -c "CREATE USER botuser WITH PASSWORD '123'; GRANT ALL PRIVILEGES ON DATABASE bokcirkel TO botuser;"
