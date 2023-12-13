from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import os
from flasgger import Swagger



app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir, "db.sqlite"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)
swagger = Swagger(app)



class Part(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(200))
    release_date = db.Column(db.Integer)
    core_clock = db.Column(db.Integer)
    boost_clock = db.Column(db.Integer, nullable=True)
    clock_unit = db.Column(db.String(10))
    price = db.Column(db.Float)
    TDP = db.Column(db.Integer)
    part_no = db.Column(db.String(100))

    def __init__(
        self, name, type, release_date, core_clock, boost_clock, clock_unit, price, TDP, part_no
    ):
        self.name = name
        self.type = type
        self.release_date = release_date
        self.core_clock = core_clock
        self.boost_clock = boost_clock
        self.clock_unit = clock_unit
        self.price = price
        self.TDP = TDP
        self.part_no = part_no


with app.app_context():
    db.create_all()


class PartScehma(ma.Schema):
    class Meta:
        fields = (
            "id",
            "name",
            "type",
            "release_date",
            "core_clock",
            "boost_clock",
            "clock_unit",
            "price",
            "TDP",
            "part_no",
        )


part_schema = PartScehma()
parts_schema = PartScehma(many=True)

@app.before_request
def validate_request():
    if request.method not in ["PUT", "POST", "GET", "PATCH", "DELETE"] and request.path.startswith("/parts"):
        return jsonify({
            "status": 1,
            "message": "405 Method Not Allowed Allow: GET, POST, PUT, PATCH, DELETE"
        }), 405

# Adds part to DB
@app.route("/parts", methods=["PUT"])
def add_part():
    """
    Add a new part to the database
    ---
    tags:
      - Parts
    parameters:
      - name: part
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            type:
              type: string
            release_date:
              type: string
              format: date
            core_clock:
              type: number
            clock_unit:
              type: string
            price:
              type: number
            TDP:
              type: number
            part_no:
              type: string
    responses:
      200:
        description: The part was successfully added to the database
      400:
        description: The request was missing required fields
      405:
        description: The request method is not allowed
    """
    
    #check for missing fields
    required_fields = ["name", "type", "release_date", "core_clock", "clock_unit", "price", "TDP", "part_no"]
    missing_fields = [field for field in required_fields if field not in request.json]

    if missing_fields:
        return jsonify({
            "status": 1,
            "message": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400

    if "id" in request.json:
        return id_supplied_error()

    name = request.json["name"]
    type = request.json["type"]
    release_date = request.json["release_date"]
    core_clock = request.json["core_clock"]
    clock_unit = request.json["clock_unit"]
    price = request.json["price"]
    TDP = request.json["TDP"]
    part_no = request.json["part_no"]

    #boost_clock is optional
    if "boost_clock" in request.json:
        boost_clock = request.json["boost_clock"]
    else:
        boost_clock = None

    if type not in ["CPU", "GPU"]:
        return part_type_invalid()
    
    new_part = Part(
        name, type, release_date, core_clock, boost_clock, clock_unit, price, TDP, part_no
    )
    db.session.add(new_part)
    db.session.commit()

    success_dict = {
        "status": 0,
        "message": "New part added",
        "id": new_part.id,
    }

    return success_dict, 200


# get with query string
@app.route("/parts", methods=["GET"])
def get_part():
    """
    Get all parts
    ---
    tags:
      - Parts
    responses:
      200:
        description: Returns a list of all parts
    """
    type = request.args.get("type")

    # if type exists
    if type:
        # if type is valid
        if type.upper() not in ["GPU", "CPU"]:
            return part_type_invalid()
        all_parts = Part.query.filter(Part.type.ilike(f"%{type}%")).all()
    else:
        all_parts = Part.query.all()

    result = []
    for part in all_parts:
        result.append(
            {"id": part.id, "name": part.name, "type": part.type, "price": part.price}
        )

    number_of_parts = len(result)

    if(number_of_parts != 0):
      total_price = sum(part["price"] for part in result)
      average_price = round(total_price / number_of_parts, 2)
    else:
      average_price = 0


    result_dict = {
        "status": 0,
        "total": number_of_parts,
        "average_price": average_price,
        "parts": result,
    }

    return jsonify(result_dict), 200


# get part with id
@app.route("/parts/<id>", methods=["GET"])
def get_part_by_id(id):
    """
    Get a part by ID
    ---
    tags:
      - Parts
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: The ID of the part to retrieve
    responses:
      200:
        description: Returns the part with the specified ID
      404:
        description: The specified part ID was not found
    """
    part = Part.query.get(id)
    if not part:
        return part_not_found()
                   

    result = part_schema.dump(part)

    return jsonify({"status": 0, **result}), 200


# update all fields of part with id
@app.route("/parts/<id>", methods=["POST"])
def update_part(id):
    """
    Update a part by ID
    ---
    tags:
      - Parts
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: The ID of the part to update
      - name: part
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            type:
              type: string
            release_date:
              type: string
              format: date
            core_clock:
              type: number
            clock_unit:
              type: string
            price:
              type: number
            TDP:
              type: number
            part_no:
              type: string
    responses:
      200:
        description: The part was successfully updated
      400:
        description: The request was missing required fields or the part type was invalid
      404:
        description: The specified part ID was not found
    """
    part = Part.query.get(id)
    if not part:
        return part_not_found()

    data = request.get_json()

    #check if user supplied id
    if "id" in data:
        return id_supplied_error()

    # Check if all required fields are present
    required_fields = ["name", "type", "release_date", "core_clock", "clock_unit", "price", "TDP", "part_no"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify(
                {
                    "status": 1,
                    "message": f"Missing fields: {', '.join(missing_fields)}",
                }
            ), 400

    # Check if type is CPU or GPU
    if data.get("type") and data["type"].upper() not in ["CPU", "GPU"]:
        return part_type_invalid()

    # Update the part details
    part.name = data["name"]
    part.type = data["type"]
    part.release_date = data["release_date"]
    part.core_clock = data["core_clock"]
    part.boost_clock = data.get("boost_clock")
    part.clock_unit = data["clock_unit"]
    part.price = data["price"]
    part.TDP = data["TDP"]
    part.part_no = data["part_no"]

    # Commit the changes to the database
    db.session.commit()

    # Return the response
    return jsonify({"status": 0, "message": "Part details updated"}), 200


# partially update a part
@app.route("/parts/<id>", methods=["PATCH"])
def modify_part(id):
    """
    Partially update a part by ID
    ---
    tags:
      - Parts
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: The ID of the part to update
      - name: part
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            type:
              type: string
            release_date:
              type: string
              format: date
            core_clock:
              type: number
            boost_clock:
              type: number
            clock_unit:
              type: string
            price:
              type: number
            TDP:
              type: number
            part_no:
              type: string
    responses:
      200:
        description: The part was successfully updated
      400:
        description: The request was missing required fields or the part type was invalid
      404:
        description: The specified part ID was not found
    """
    part = Part.query.get(id)
    if not part:
        return part_not_found()

    data = request.get_json()

    # Check if id is supplied in the request
    if "id" in data:
        return id_supplied_error()
    
    # Check if type is CPU or GPU
    if "type" in data and data["type"].lower() not in ["cpu", "gpu"]:
        return part_type_invalid()
    
    # Update the part details
    for key, value in data.items():
        if key == "name":
            part.name = value
        elif key == "type":
            part.type = value
        elif key == "release_date":
            part.release_date = value
        elif key == "core_clock":
            part.core_clock = value
        elif key == "boost_clock":
            part.boost_clock = value
        elif key == "clock_unit":
            part.clock_unit = value
        elif key == "price":
            part.price = value
        elif key == "TDP":
            part.TDP = value
        elif key == "part_no":
            part.part_no = value

    # Commit the changes to the database
    db.session.commit()

    # Return the response
    return jsonify({"status": 0, "message": "Part modified"}), 200


# delete part with id
@app.route("/parts/<id>", methods=["DELETE"])
def delete_part(id):
    """
    Delete a part by ID
    ---
    tags:
      - Parts
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: The ID of the part to delete
    responses:
      200:
        description: The part was successfully deleted
      404:
        description: The specified part ID was not found
    """
    part = Part.query.get(id)
    if not part:
        return part_not_found()

    # Delete the part from the database
    db.session.delete(part)
    db.session.commit()

    # Return the response
    return jsonify({"status": 0, "message": "Part deleted"}), 200

def part_not_found():
    return (
        jsonify(
            {
                "status": 1,
                "message": "Part not found.",
            }
        ),
        404,
    )

def part_type_invalid():
    return (
        jsonify(
            {
                "status": 1,
                "message": "Invalid type. Valid choices are ‘CPU’ and ‘GPU’.",
            }
        ),
        400,
    )

def id_supplied_error():
    return (
        jsonify(
            {
                "status": 1,
                "message": "Client cannot supply id.",
            }
        ),
        400,
    )

if __name__ == "__main__":
    app.run(host='[2605:fd00:4:1001:f816:3eff:feb7:7b0c]', port=8080)
