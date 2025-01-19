from flask import Flask, request, render_template, redirect, url_for
import os
from deepface import DeepFace
import base64
from io import BytesIO
from PIL import Image
import pymysql

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

REFERENCE_FOLDER = os.path.join(app.root_path, 'static', 'reference_images')
RESULT_FOLDER = os.path.join(app.root_path, 'static', 'results')
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

# Database configuration
db = pymysql.connect(
    host="localhost",
    user="root",
    password=os.getenv('DB_PASSWORD', ''),
    database="db_paras_ulama"
)

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get("name")
        asal = request.form.get("origin")
        gender = request.form.get("gender")

        if not name or not asal or not gender:
            return "Semua field harus diisi", 400

        try:
            with db.cursor() as cursor:
                query = "SELECT * FROM tb_users WHERE name = %s AND asal = %s"
                cursor.execute(query, (name, asal))
                existing_user = cursor.fetchone()

                if existing_user:
                    return redirect(url_for('upload_file', name=name, gender=gender))
                
                query = "INSERT INTO tb_users (name, asal, gender) VALUES (%s, %s, %s)"
                cursor.execute(query, (name, asal, gender))
                db.commit()
        except Exception as e:
            db.rollback()
            return f"Terjadi kesalahan: {e}", 500

        return redirect(url_for('upload_file', name=name, gender=gender))

    return render_template('register.html')

@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    user_name = request.args.get("name") if request.method == 'GET' else request.form.get("name")
    gender = request.args.get("gender") if request.method == 'GET' else request.form.get("gender")

    if not user_name:
        return "Name parameter is missing", 400

    if request.method == 'POST':
        image_data = request.form.get('image')
        if not image_data:
            return "No image data provided", 400

        try:
            image_data = image_data.split(",")[1]  # Remove 'data:image/png;base64,' prefix
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            image = image.convert('RGB')
            user_image_filename = f"{user_name}_photo.jpg"
            user_image_path = os.path.join(app.config['UPLOAD_FOLDER'], user_image_filename)
            image.save(user_image_path, "JPEG")

            return redirect(url_for('process_image', name=user_name, gender=gender, user_image=user_image_filename))
        except Exception as e:
            return f"Error processing image: {e}", 500

    return render_template('index.html', name=user_name, gender=gender)

@app.route('/process', methods=['POST', 'GET'])
def process_image():
    if request.method == 'GET':
        user_name = request.args.get('name')
        gender = request.args.get('gender')
        user_image_filename = request.args.get('user_image')

        if not user_image_filename:
            return "User image is missing", 400

        user_image_path = os.path.join(UPLOAD_FOLDER, user_image_filename)
        reference_folder = os.path.join(REFERENCE_FOLDER, 'perempuan' if gender == 'perempuan' else 'lakilaki')
        reference_images = [os.path.join(reference_folder, f) for f in os.listdir(reference_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

        if not reference_images:
            print("Tidak ada gambar referensi di folder ulama.")
            return "Tidak ada gambar referensi di folder ulama.", 400

        # Data jabatan ulama
        ULAMA_JABATAN = {
            "KH Abdul Haq Zaini": "Ketua Yayasan Pondok Pesantren Nurul Jadid",
            "KH Abdul Wahab Hasbullah": "Pendiri Nadhatul Ulama",
            "KH Abdul Wahid Zaini": "Pengasuh Pondok Pesantren Nurul Jadid Ke-3",
            "KH Abdurrahman Wahid": "Presiden Indonesia ke-4",
            "KH As'ad Syamsul Arifin": "Pendiri Nadhatul Ulama",
            "KH Bisri Syansuri": "Pendiri Nadhatul Ulama",
            "KH Faqih Zawawi": "Dewan Pengasuh Dan Pengawas Pondok Pesantren Nurul Jadid",
            "KH Hasan Abdul Wafi": "Pengawas Pondok Pesantren Nurul Jadid",
            "KH Hasyim Asy'ari": "Pengawas Pondok Pesantren Nurul Jadid",
            "Kh Moh Hasyim Zaini": "Pengasuh Pondok Pesantren Nurul Jadid ke-2",
            "Kh Nur Chotim Zaini": "Ketua Yayasan Pondok Pesantren Nurul Jadid",
            "KH Zaini Abdul Mun'im": "Pendiri & Pengasuh Pondok Pesantren Nurul Jadid",
        }

        highest_similarity = 0
        best_match = None

        for ref_image in reference_images:
            try:
                ulama_name = os.path.splitext(os.path.basename(ref_image))[0]
                print(f"Memproses gambar referensi: {ref_image}")

                # Pastikan file gambar dapat diakses
                if not os.path.isfile(ref_image):
                    print(f"File tidak ditemukan: {ref_image}")
                    continue

                result = DeepFace.verify(user_image_path, ref_image)
                print(f"Hasil dari DeepFace.verify: {result}")

                similarity = result.get("distance", 1.0)
                similarity_percentage = (1 - similarity) * 100

                print(f"Nama Ulama: {ulama_name}, Persentase Kesamaan: {similarity_percentage}%")
                
                if similarity_percentage < 50:
                    similarity_percentage += 60

                if similarity_percentage > highest_similarity:
                    highest_similarity = similarity_percentage

                    jabatan = (
                        "Pahlawan Indonesia" if gender == 'perempuan' else ULAMA_JABATAN.get(ulama_name, "Pahlawan Wanita Nasional")
                    )
                    best_match = {
                        "user_name": user_name,
                        "ulama_name": ulama_name,
                        "jabatan": jabatan,
                        "similarity_percentage": round(similarity_percentage, 2),
                        "ref_image": os.path.basename(ref_image),
                        "gender": gender
                    }
            except Exception as e:
                print(f"Error processing reference image {ref_image}: {e}")
                continue

        if best_match:
            return render_template('result.html', name=user_name, gender=gender, user_image=user_image_filename, best_match=best_match)
        else:
            return "Tidak ada gambar yang cocok ditemukan.", 404

    return "Invalid request method", 405

if __name__ == '__main__':
    app.run(debug=True)
