#!/bin/bash
# Start ngrok with the configured domain to pass webhooks to the local backend
echo "Starting ngrok tunnel forwarding to http://localhost:8000..."
echo "Using domain: overmild-untenuously-penney.ngrok-free.dev"
ngrok http --domain=overmild-untenuously-penney.ngrok-free.dev 8000
