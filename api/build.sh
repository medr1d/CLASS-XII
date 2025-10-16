#!/bin/bash
# Build script for Vercel deployment
echo "Running database migrations..."
cd api
python manage.py migrate --noinput
echo "Migrations complete!"
