
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                           Image Processing Telegram Bot                       ║
║                                                                               ║
║  A Telegram bot that processes images by adding customizable text banners     ║
║  and optional video effects.                                                  ║
║                                                                               ║
║  Author: Focus                                                                ║
║  GitHub: https://github.com/focus-on1                                         ║
║  Created: January 2025                                                        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""


import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import moviepy.editor as mpy


# Dictionnaire pour suivre l'état des utilisateurs (si une vidéo a été générée ou non)
user_state = {}


"""

Cours 


fromarray = sert a conevertire l'image avec le cannaux approprie
Image.new = cree une nouvelle image
paste = copie l'image sur une image 

"""
# Fonction pour traiter l'image et ajouter du texte
def process_image(image_path, text, output_image="final_output.jpg"): 
    image = cv2.imread(image_path) # lire l'image 
    if image is None: 
        raise FileNotFoundError(f"Image non trouvée : {image_path}")

    ######################################
    #           Creaction de la bannier #
    # ###################################
    height, width, _ = image.shape # extraire la hauteur largeur le cannaux 
    cm_to_pixels = 96 / 2.54  # cree notre pixel 
    banner_height = int(5 * cm_to_pixels) #l'initialisation de notre bannier 
 
    
    image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)) # on convertir l'image 
    image_pil_with_banner = Image.new('RGB', (width, height + banner_height), (255, 255, 255))  # ici on cree une nouvelle image ca sera la banier blanche 
    image_pil_with_banner.paste(image_pil, (0, banner_height)) # cette metode permet de colle une image sur une autre la banier position 0 en haut a gauche sera colel sur image pil 

    image_with_banner = cv2.cvtColor(np.array(image_pil_with_banner), cv2.COLOR_RGB2BGR) #  convertie l'image en cannauxRGB
    cv2.imwrite(output_image, image_with_banner)

    image_with_banner_pil = Image.open(output_image) # charge l'image 
    draw = ImageDraw.Draw(image_with_banner_pil)  #  applique les modification 
    

    #######################################
    #           Application de l'ecriture #
    #######################################

    font_path = "Rubik-Bold.ttf"  # Front 
    font, lines = get_max_font_size(text, width, banner_height, font_path, draw) # permet d'affiche le text sans depasse
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

# Fonction pour calculer la taille de police maximale et découper le texte en lignes
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

# Fonction pour découper le texte en plusieurs lignes
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

########################################"
#                                       #
#           Fonction Pour le BOt        #
# #######################################"

# Commande de démarrage
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Envoie une image que tu veux personnaliser !")

# Gestionnaire pour l'image envoyée
def handle_image(update: Update, context: CallbackContext):
    user = update.message.from_user 
    photo = update.message.photo[-1].get_file()
    photo.download("user_image.jpg") 
    
    # Réinitialiser l'état de l'utilisateur lorsqu'une nouvelle image est envoyée
    user_state[user.id] = {'video_generated': False}
    
    update.message.reply_text("Maintenant, envoie le texte à ajouter sur l'image.")

# Gestionnaire pour le texte envoyé
def handle_text(update: Update, context: CallbackContext):
    user = update.message.from_user
    text = update.message.text
    image_path = "user_image.jpg"

    output_image = process_image(image_path, text)
    with open(output_image, 'rb') as photo:
        keyboard = [
            [InlineKeyboardButton("Mettre en vidéo", callback_data="video")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_photo(photo=photo, caption="Voici ton image personnalisée !", reply_markup=reply_markup)



# Gestionnaire pour choisir un mood d'animation
def choose_animation(update: Update, context: CallbackContext):
    user = update.callback_query.from_user
    
    # Vérifier si l'utilisateur a déjà généré une vidéo
    if user_state.get(user.id, {}).get('video_generated', False):
        update.callback_query.message.reply_text("Tu as déjà généré une vidéo. Envoie une nouvelle photo pour recommencer.")
        return
    
    keyboard = [
        [InlineKeyboardButton("Contrast Black", callback_data="contrast_black")],
        [InlineKeyboardButton("Aucun effet", callback_data="no_effect")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text("Choisis le mood d'animation (ou aucun effet) :", reply_markup=reply_markup)

# Gestionnaire pour appliquer le choix de l'animation
def apply_animation_choice(update: Update, context: CallbackContext):
    user = update.callback_query.from_user
    animation_choice = update.callback_query.data
    
    # Stocker le choix de l'animation pour l'utilisateur
    context.user_data['animation_choice'] = animation_choice
    
    update.callback_query.message.reply_text(f"Animation choisie : {animation_choice}. Maintenant, choisis la durée de la vidéo.")

    # Proposer à l'utilisateur de choisir la durée de la vidéo
    keyboard = [
        [InlineKeyboardButton("0:10", callback_data="0:10"),
         InlineKeyboardButton("0:20", callback_data="0:20"),
         InlineKeyboardButton("0:30", callback_data="0:30"),
         InlineKeyboardButton("0:40", callback_data="0:40"),
         InlineKeyboardButton("0:50", callback_data="0:50"),
         InlineKeyboardButton("1:00", callback_data="1:00"),
         InlineKeyboardButton("1:10", callback_data="1:10")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text("Choisis la durée de la vidéo (de 0 à 1 minute 10 secondes) :", reply_markup=reply_markup)


# Gestionnaire pour la création de la vidéo avec animation et durée
def apply_contrast_black(image_path, crescendo_duration=4, total_duration=10):
    # Charge l'image
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image non trouvée : {image_path}")
    
    # Crée une séquence d'images avec un fondu lumineux progressif pendant les 4 premières secondes
    frames = []
    num_frames_crescendo = 30  # Nombre de frames pour l'animation de crescendo
    num_frames_static = int((total_duration - crescendo_duration) * 24)  # Nombre de frames pour l'image normale après l'animation
    
    # Animation crescendo (d'ombre à luminosité normale)
    for i in range(num_frames_crescendo):
        factor = i / num_frames_crescendo  # Le facteur va de 0 (sombre) à 1 (lumineux)
        bright_image = np.clip(image * factor, 0, 255).astype(np.uint8)
        frames.append(bright_image)
    
    # Ajouter des frames avec l'image normale pour compléter la durée
    for _ in range(num_frames_static):
        frames.append(image)
    
    # Créer un clip vidéo avec la séquence d'images
    clip = mpy.ImageSequenceClip(frames, durations=[1/24] * len(frames))  # Durée de chaque frame est 1/24 secondes
    return clip


# Fonction pour créer la vidéo avec animation et durée
def handle_video_duration(update: Update, context: CallbackContext):
    user = update.callback_query.from_user
    
    # Vérifier si l'utilisateur a déjà généré une vidéo
    if user_state.get(user.id, {}).get('video_generated', False):
        update.callback_query.message.reply_text("Tu as déjà généré une vidéo. Envoie une nouvelle photo pour recommencer.")
        return

    # Récupérer le choix de l'animation
    animation_choice = context.user_data.get('animation_choice', None)
    
    if not animation_choice:
        update.callback_query.message.reply_text("Choisis un type d'animation avant de créer la vidéo.")
        return

    # Récupérer la durée choisie
    duration_str = update.callback_query.data
    minutes, seconds = map(int, duration_str.split(":"))
    total_duration = minutes * 60 + seconds
    
    image_path = "final_output.jpg"
    
    # Appliquer l'animation
    if animation_choice == "contrast_black":
        clip = apply_contrast_black(image_path, crescendo_duration=4, total_duration=total_duration)
    else:
        clip = mpy.ImageClip(image_path).set_duration(total_duration)
    
    # Sauvegarder la vidéo
    output_video = "output_video.mp4"
    clip.write_videofile(output_video, fps=30)

    with open(output_video, 'rb') as video:
        update.callback_query.message.reply_video(video=video, caption="Voici ta vidéo personnalisée !")
    
    # Mettre à jour l'état de l'utilisateur pour indiquer que la vidéo a été générée
    user_state[user.id] = {'video_generated': True}

# Fonction principale pour configurer le bot
def main():
    api_key = "API"  # Remplacez par votre API key
    
    updater = Updater(api_key)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_image))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dispatcher.add_handler(CallbackQueryHandler(choose_animation, pattern="video"))
    dispatcher.add_handler(CallbackQueryHandler(apply_animation_choice, pattern="contrast_black|no_effect"))
    dispatcher.add_handler(CallbackQueryHandler(handle_video_duration, pattern=r"\d{1,2}:\d{2}"))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
