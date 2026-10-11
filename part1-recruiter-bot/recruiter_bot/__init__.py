import os
from flask import Flask, jsonify
from .routes import bp, close_db
from .utils import get_connection, init_schema

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recruiter_bot.db")


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.environ.get("RECRUITER_BOT_DB", DEFAULT_DB_PATH)
    app.json.sort_keys = False

    conn = get_connection(app.config["DATABASE"])
    init_schema(conn)
    conn.close()

    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "method not allowed"}), 405

    return app
