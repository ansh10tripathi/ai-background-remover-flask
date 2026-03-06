from flask import Flask, render_template, request
from rembg import remove
from PIL import Image
import os

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "static/outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():

    original_image = None
    output_image = None

    if request.method == "POST":

        file = request.files["image"]

        if file:

            input_path = os.path.join(UPLOAD_FOLDER, file.filename)
            output_path = os.path.join(OUTPUT_FOLDER, "output.png")

            file.save(input_path)

            input_img = Image.open(input_path)

            output = remove(input_img)

            output.save(output_path)

            original_image = input_path
            output_image = output_path

    return render_template(
        "index.html",
        original_image=original_image,
        output_image=output_image
    )


if __name__ == "__main__":
    app.run(debug=True)