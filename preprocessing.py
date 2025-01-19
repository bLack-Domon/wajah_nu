import os
import pickle
from deepface import DeepFace
from PIL import Image

# Folder tempat gambar referensi disimpan
REFERENCE_FOLDER = "static/reference_images"
# File output tempat embeddings akan disimpan
EMBEDDINGS_FILE = "reference_embeddings.pkl"

def extract_embeddings(reference_folder, embeddings_file):
    embeddings = {}
    # Ambil semua file gambar di folder reference_images
    for image_name in os.listdir(reference_folder):
        image_path = os.path.join(reference_folder, image_name)
        
        # Hanya proses file gambar dengan ekstensi yang valid
        if image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                # Gunakan DeepFace untuk ekstrak embeddings
                print(f"Processing {image_name}...")
                
                # Ekstraksi embeddings menggunakan DeepFace
                representations = DeepFace.represent(image_path, model_name="VGG-Face", enforce_detection=False)
                
                # Ambil embeddings pertama (jika lebih dari satu wajah terdeteksi)
                embeddings[image_name] = representations[0]['embedding']
                
                print(f"Extracted embedding for {image_name}")
            except Exception as e:
                print(f"Error processing {image_name}: {e}")
    
    # Simpan embeddings ke file pickle
    with open(embeddings_file, 'wb') as file:
        pickle.dump(embeddings, file)
    print(f"Embeddings saved to {embeddings_file}")

# Jalankan fungsi untuk mengekstrak dan menyimpan embeddings
extract_embeddings(REFERENCE_FOLDER, EMBEDDINGS_FILE)
