import os
import re
import base64
import shutil
import random
import subprocess
import platform
import sys
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests
import json
import time
from dotenv import load_dotenv
import pdf417
from PIL import Image
import atexit



# Determine OS and architecture
def get_system_info():
    os_name = platform.system().lower()
    arch = platform.machine().lower()
    if arch in ('x86_64', 'amd64'):
        arch = 'amd64'
    elif arch in ('arm64', 'aarch64'):
        arch = 'arm64'
    return os_name, arch

# Map OS and architecture to binary names
binary_map = {
    ('windows', 'amd64'): 'amd64_windows_NICServer.exe',
    ('linux', 'amd64'): 'amd64_linux_NICServer',
    ('darwin', 'amd64'): 'amd64_darwin_NICServer',
    ('darwin', 'arm64'): 'arm64_darwin_NICServer',
    ('linux', 'arm64'): 'arm64_linux_NICServer',
}

# Check for Go installation
def is_go_installed():
    try:
        subprocess.run(['go', 'version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

# Start the NIC server
def start_nic_server():
    os_name, arch = get_system_info()
    binary_folder = 'bin'
    binary_name = binary_map.get((os_name, arch))
    binary_path = resource_path(os.path.join(binary_folder, binary_name)) if binary_name else None

    if binary_path and os.path.isfile(binary_path):
        if os_name in ('linux', 'darwin'):
            os.chmod(binary_path, 0o755)
        creation_flags = subprocess.CREATE_NO_WINDOW if os_name == 'windows' else 0
        return subprocess.Popen([binary_path], creationflags=creation_flags)
    else:
        if is_go_installed():
            go_file = resource_path(os.path.join('gendata', 'nic_generator.go'))
            if os.path.isfile(go_file):
                return subprocess.Popen(['go', 'run', 'nic_generator.go'], cwd=resource_path('gendata'))
        print("Can't find any matching NICServer binary.")
        sys.exit(1)
        
# Initialize the NIC server
server_process = start_nic_server()

# Clean up the NIC server process on exit
def cleanup_nic_server():
    if server_process:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)  # Wait up to 5 seconds for graceful termination
        except subprocess.TimeoutExpired:
            server_process.kill()  # Force kill if it doesn't terminate

atexit.register(cleanup_nic_server)

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')
    
    
#######################################################3

provinces = {
    1: ['Colombo', 'Gampaha', 'Kalutara'],                     # Western Province
    2: ['Kandy', 'Matale', 'Nuwara Eliya'],                    # Central Province
    3: ['Galle', 'Matara', 'Hambantota'],                      # Southern Province
    4: ['Jaffna', 'Kilinochchi', 'Mannar', 'Vavuniya', 'Mullaitivu'],  # Northern Province
    5: ['Trincomalee', 'Batticaloa', 'Ampara'],                # Eastern Province
    6: ['Kurunegala', 'Puttalam'],                             # North Western Province (Wayamba)
    7: ['Anuradhapura', 'Polonnaruwa'],                        # North Central Province
    8: ['Badulla', 'Moneragala'],                              # Uva Province
    9: ['Ratnapura', 'Kegalle'],                               # Sabaragamuwa Province
}

def get_random_district(province_number):
    return random.choice(provinces.get(province_number, ['Colombo']))  # Default to Colombo if invalid

def generate_address(province_number):
    district = get_random_district(province_number)
    prompt = (
        f"generate me a real sri lankan address in {district} district area for my tales book. "
        f"need to be more detailed looking real mailing address. number, Lane, road, town, city, village etc. "
        f"Avoid generating fake lanes etc because I write this as a real story.. only print the address. nothing else."
    )

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/last_address_response.json", "w", encoding="utf-8") as logf:
            json.dump(payload, logf, ensure_ascii=False, indent=2)

        api_key = os.getenv("GEMINI_API_KEY", "HARDCODED_API_KEY_BACKUP")
        res = requests.post(url, headers=headers, params={"key": api_key}, json=payload)
        res.raise_for_status()

        parts = res.json()['candidates'][0]['content']['parts']
        address = parts[0]['text'].strip()
        return address
        
    except Exception as e:
        print("Gemini address generation error:", e)
        return "Unknown Address"

########################################################
def generate_pdf417_base64(barcode_text, output_path=None):
    codes = pdf417.encode(barcode_text, columns=6, security_level=5)
    image = pdf417.render_image(codes)  # Returns a PIL image

    if output_path:
        image.save(output_path)

    from io import BytesIO
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return "data:image/png;base64," + encoded
    
def generate_name(sex):
    prompt = (
        f"Generate a random, authentic Sri Lankan {sex} full name. The name must follow a traditional multi-component structure, typically including:\n\n"
        f"1. A 'Ge' or \"Lage\" name (a traditional family, ancestral, or house name prefix).\n"
        f"2. One or more {sex} given names.\n"
        f"3. A Sri Lankan surname.\n"
        f"4. The name in Sinhala and Tamil text.\n\n"
        f"For example, a name like 'Vidanelage Upeksha Priyadarshani Ratnayake' or 'Hewagamage Tharushi Kumari Dissanayake' demonstrates the desired structure and level of detail.\n\n"
        f'And the format matches:\n\n'
        f'"Vidanelage Upeksha Priyadarshani Ratnayake"\n'
        f'"විදානෙලාගේ උපේක්ශා ප්‍රියදර්ශණී රත්නායක"\n'
        f'"விதானெலவின் உபேக்ஷா பிரியதர்ஷனி ரத்நாயக்க"\n\n'
        f'"Senanayake Mudiyansalage Himasha Madushani Wijesinghe"\n'
        f'"සේනානායක මුදියන්සේලාගේ හිමාෂා මදුෂානි විජේසිංහ"\n'
        f'"சேனநாயக்க முதியன்சேலாகே ஹிமாஷா மதுஷானி விஜேசிங்க"\n\n'
        f"Your response must consist of *only* the generated full name. Do not include any surrounding text, explanations, labels, or introductory phrases"
    )

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        # Log the request payload
        #os.makedirs("logs", exist_ok=True) #<-- jsut uncomment these 3 lines if you wanna see gemini request
        #with open("logs/last_name_response.json", "w", encoding="utf-8") as logf: #<-- jsut uncomment these 3 lines if you wanna see gemini request
        #    json.dump(payload, logf, ensure_ascii=False, indent=2)  # Changed 'data' to 'payload' <-- jsut uncomment these 3 lines if you wanna see gemini request

        # Replace 'HARDCODED_API_KEY_BACKUP' with a valid API key (not recommended) or load from environment (recommended)
        api_key = os.getenv("GEMINI_API_KEY", "HARDCODED_API_KEY_BACKUP")  # Load from environment variable
        res = requests.post(url, headers=headers, params={"key": api_key}, json=payload)
        res.raise_for_status()

        # Parse the response
        parts = res.json()['candidates'][0]['content']['parts']
        lines = parts[0]['text'].strip().splitlines()
        if len(lines) < 3:
            return ("Unknown", "නොදන්නා", "தெரியாத")
        return lines[0].strip(), lines[1].strip(), lines[2].strip()
    except Exception as e:
        print("Gemini name generation error:", e)
        return ("Unknown", "නොදන්නා", "தெரியாத")
        
        
@app.route('/generate-nic', methods=['POST'])
def generate_nic():
    data = request.json
    sex = data['sex']
    year = data['year']
    month = data['month']
    day = data['day']

    date = f"{year}-{month:02d}-{day:02d}"
    res = requests.get(f"http://localhost:3000/v1/generator?date={date}&sex={sex}")

    if res.status_code != 200:
        return jsonify({"error": "NIC server error"}), 500

    nic_data = res.json()

    birth_date = datetime.strptime(nic_data["date"], "%Y-%m-%d")
    today = datetime.today()
    age = relativedelta(today, birth_date)
    nic_data["age"] = {
        "years": age.years,
        "months": age.months,
        "days": age.days
    }

    english_name, sinhala_name, tamil_name = generate_name(sex)
    nic_data["name"] = {
        "english": english_name,
        "sinhala": sinhala_name,
        "tamil": tamil_name
    }
    address = "Unknown Address"
    province_number = nic_data['province']['number']
    for _ in range(3):  # Retry up to 3 times
        address = generate_address(province_number)
        if address != "Unknown Address":
            break
    nic_data["address"] = address
    time.sleep(3)

    folder = os.path.join("generated", nic_data["nnic"])
    os.makedirs(folder, exist_ok=True)

    with open(os.path.join(folder, "data.txt"), "w", encoding="utf-8") as f:
        f.write(f"New NIC No.: {nic_data['nnic']}\n")
        f.write(f"Old NIC No.: {nic_data['onic']}\n")
        f.write(f"DOB: {nic_data['date']}\n")
        f.write(f"Sex: {nic_data['sex'].capitalize()}\n")
        f.write(f"SN: New: {nic_data['sn']['new']}, Old: {nic_data['sn']['old']}\n")
        f.write(f"Age: {age.years} years, {age.months} months, {age.days} days\n")
        f.write(f"Province Name: {nic_data['province']['name']}\n")
        f.write(f"Province Number: {nic_data['province']['number']}\n")
        f.write(f"Name (English): {english_name}\n")
        f.write(f"Name (Sinhala): {sinhala_name}\n")
        f.write(f"Name (Tamil): {tamil_name}\n")
        f.write(f"Address: {address}\n")

    barcode_text = nic_data["barcode"]["content"]
    barcode_base64 = generate_pdf417_base64(barcode_text)
    nic_data["barcode"]["image"] = barcode_base64  # overwrite the empty one from Go

    with open(os.path.join(folder, "barcode.png"), "wb") as f:
        f.write(base64.b64decode(barcode_base64.split(",")[1]))

    return jsonify(nic_data)

@app.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.json
        sex = data.get("sex")
        age = data.get("age")
        nic = data.get("nic")

        if not sex or age is None:
            return jsonify({"error": "Missing sex or age"}), 400

        skin_tones = ['fair', 'light brown', 'medium brown', 'dark brown', 'tan', 'olive']
        male_hairstyles = ['short curly', 'buzz cut', 'faded sides', 'neatly combed', 'side-parted']
        female_hairstyles = ['shoulder-length straight', 'tied back', 'long wavy', 'loose curls', 'sri lankan style', 'neatly pulled back']
        male_cloths = ['T-shirt', 'Shirt', 'Polo Shirt', 'Sweater', 'Blazer', 'collared shirt']
        female_cloths = ['T-shirt', 'Blouse', 'Top', 'Cardigan', 'Saree Blouse', 'Saree', 'collared shirt']
        facial_expressions = ['neutral', 'natural', 'slight smile']
        backdrop_colors = ['very light blue', 'white', 'off white']

        skin_tone = random.choice(skin_tones)
        hair_style = random.choice(male_hairstyles if sex == 'male' else female_hairstyles)
        cloth = random.choice(male_cloths if sex == 'male' else female_cloths)
        expression = random.choice(facial_expressions)
        color = random.choice(backdrop_colors)
        GEMINI_KEY = os.getenv("GEMINI_API_KEY")

        prompt = (
            f"A photorealistic portrait of a Sri Lankan {age} year old {sex} with a {skin_tone} skin tone "
            f"and {hair_style} hairstyle. Both shoulders are clearly visible. The subject is wearing {cloth}. "
            f"The face should be clearly visible with natural texture, showing subtle imperfections. "
            f"The subject is facing straight ahead, with a {expression} expression. "
            f"The background is a plain light {color} studio backdrop. The photo is in portrait orientation with a 7:9 aspect ratio, "
            f"suitable for a driving license card. Use realistic lighting and photographic style, avoid outlines and white outlines. "
            f"The framing should ensure that the subject's face occupies less than 30% of the image, with at least 90% of both shoulders visible. "
            f"Apply the rule of thirds for composition. Avoid borders. The final image should resemble a professional photograph."
        )

        curl_command = [
            'curl', '-s', '-X', 'POST',
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent?key={GEMINI_KEY}',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
            })
        ]

        result = subprocess.run(curl_command, capture_output=True, text=True)
        match = re.search(r'"data": "([^"]*)"', result.stdout)

        if not match:
            print("Curl failed or unexpected output:")
            print(result.stdout)
            return jsonify({"error": "No image found"}), 500

        image_data = base64.b64decode(match.group(1))

        # Use app.root_path instead of resource_path for PyInstaller compatibility
        portrait_dir = os.path.join(app.root_path, "static", "portrait")
        os.makedirs(portrait_dir, exist_ok=True)
        temp_image_path = os.path.join(portrait_dir, "temp.jpg")
        with open(temp_image_path, "wb") as f:
            f.write(image_data)

        if nic:
            generated_dir = os.path.join(app.root_path, "generated")
            nic_folder = os.path.join(generated_dir, nic)
            os.makedirs(nic_folder, exist_ok=True)
            with open(os.path.join(nic_folder, "portrait.jpg"), "wb") as f:
                f.write(image_data)

        return send_file(temp_image_path, mimetype='image/jpeg')

    except Exception as e:
        print("generate-image error:", e)
        return jsonify({"error": str(e)}), 500


@app.route('/save-data', methods=['POST'])
def save_data():
    data = request.json
    nic = data['nic']
    image_b64 = data.get('image')

    folder = os.path.join("generated", nic)
    os.makedirs(folder, exist_ok=True)

    if image_b64:
        with open(os.path.join(folder, "portrait.jpg"), "wb") as f:
            f.write(base64.b64decode(image_b64))

    return jsonify({"message": "Saved successfully"})
    
# For compiled apps
def resource_path(relative_path):
    """Get absolute path to resource (compatible with PyInstaller)"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Development: use current directory
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
    
@app.route('/download-zip')
def download_zip():
    nic = request.args.get('nic')
    time_stamp = request.args.get('time')

    folder = os.path.join("generated", nic)
    zip_base = os.path.join("downloads", f"{nic}-{time_stamp}")
    zip_path = f"{zip_base}.zip"

    os.makedirs("downloads", exist_ok=True)

    portrait_path = os.path.join(folder, "portrait.jpg")
    if not os.path.isfile(portrait_path) or os.path.getsize(portrait_path) < 1000:
        return jsonify({"error": "portrait.jpg missing or corrupted"}), 500

    shutil.make_archive(zip_base, 'zip', folder)

    if not os.path.exists(zip_path):
        return jsonify({"error": "ZIP creation failed"}), 500

    return send_from_directory("downloads", os.path.basename(zip_path), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False)
