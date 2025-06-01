from flask import Flask, render_template
from app import app

# Keep only unique routes that aren't in demo_routes.py
# All duplicate routes have been removed to prevent conflicts