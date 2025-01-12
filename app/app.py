import os
from flask import Flask, render_template, request, send_file, jsonify
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mpy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.secret_key = 'votre_clé_secrète_ici'  # Nécessaire pour les sessions

# Assurez-vous que le dossier uploads existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Fonction pour traiter l'image et ajouter du texte
def process_image(image_path, text, output_image):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image non trouvée : {image_path}")

    height, width, _ = image.shape
    cm_to_pixels = 96 / 2.54
    banner_height = int(5 * cm_to_pixels)

    banner = np.ones((banner_height, width, 3), dtype=np.uint8) * 255
    image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    image_pil_with_banner = Image.new('RGB', (width, height + banner_height), (255, 255, 255))
    image_pil_with_banner.paste(image_pil, (0, banner_height))

    image_with_banner = cv2.cvtColor(np.array(image_pil_with_banner), cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_image, image_with_banner)

    image_with_banner_pil = Image.open(output_image)
    draw = ImageDraw.Draw(image_with_banner_pil)

    font_path = "static/fonts/Rubik-Bold.ttf"
    font, lines = get_max_font_size(text, width, banner_height, font_path, draw)
    
    total_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines]) + (len(lines) - 1) * 10
    space_between_lines = (banner_height - total_height) // (len(lines) + 1)

    line_y = 10 + space_between_lines
    for line in lines:
        line_width, line_height = draw.textbbox((0, 0), line, font=font)[2:4]
        line_x = (width - line_width) // 2
        draw.text((line_x, line_y), line, font=font, fill=(0, 0, 0))
        line_y += line_height + space_between_lines

    image_with_banner_pil.save(output_image)
    return output_image

def get_max_font_size(text, width, height, font_path, draw, max_font_size=200):
    font_size = max_font_size
    font = ImageFont.truetype(font_path, font_size)
    lines = wrap_text(text, font, width - 40, draw)

    while True:
        total_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines]) + (len(lines) - 1) * 10
        if total_height <= height - 20:
            break
        font_size -= 1
        font = ImageFont.truetype(font_path, font_size)
        lines = wrap_text(text, font, width - 40, draw)

        if font_size < 20:
            break
    
    return font, lines

def wrap_text(text, font, max_width, draw):
    lines = []
    words = text.split()
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        test_width, test_height = draw.textbbox((0, 0), test_line, font=font)[2:4]
        
        if test_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines

def apply_contrast_black(image_path, crescendo_duration=4, total_duration=10):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image non trouvée : {image_path}")
    
    frames = []
    num_frames_crescendo = int(crescendo_duration * 24)
    num_frames_static = int((total_duration - crescendo_duration) * 24)
    
    for i in range(num_frames_crescendo):
        factor = i / num_frames_crescendo
        bright_image = np.clip(image * factor, 0, 255).astype(np.uint8)
        frames.append(bright_image)
    
    for _ in range(num_frames_static):
        frames.append(image)
    
    clip = mpy.ImageSequenceClip(frames, fps=24)
    return clip

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier n\'a été envoyé'}), 400
    
    file = request.files['file']
    text = request.form.get('text', '')
    
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'processed_{filename}')
        
        file.save(input_path)
        
        try:
            processed_image = process_image(input_path, text, output_path)
            return jsonify({
                'success': True,
                'image_url': f'/static/uploads/processed_{filename}',
                'processed_image_path': output_path
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Type de fichier non autorisé'}), 400

@app.route('/create_video', methods=['POST'])
def create_video():
    data = request.json
    image_path = data.get('image_path')
    animation_type = data.get('animation_type')
    duration = int(data.get('duration', 10))
    
    if not image_path or not os.path.exists(image_path):
        return jsonify({'error': 'Image non trouvée'}), 400
    
    try:
        if animation_type == 'contrast_black':
            clip = apply_contrast_black(image_path, crescendo_duration=4, total_duration=duration)
        else:
            clip = mpy.ImageClip(image_path).set_duration(duration)
        
        video_filename = f'output_video_{os.path.basename(image_path)}.mp4'
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        clip.write_videofile(video_path, fps=24)
        
        return jsonify({
            'success': True,
            'video_url': f'/static/uploads/{video_filename}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True)