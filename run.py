from app.factory import create_app,Flask
#from flask import Flask,jsonify

app = create_app(config_name="DEVELOPMENT")
app.app_context().push()
"""app = Flask(__name__)

@app.route("/TEST",methods=["GET"])
def test():
    return jsonify({"code":204,"msg":"error"})
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True)
