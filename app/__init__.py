from flask import Flask

# Function to create and configure the app
def create_app():
    app = Flask(__name__)
    
    # Import the routes after the app is created
    from .routes import main_bp
    
    # Register blueprint
    app.register_blueprint(main_bp)

    return app