#!/bin/bash
# Manual start script for testing

echo "Starting Bananacraft..."
source venv/bin/activate

# Check if Minecraft is running (optional check)
# Start Streamlit
streamlit run app/main.py
