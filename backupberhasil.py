import logging
import os
from dotenv import load_dotenv
from pyht import Client
from pyht.client import TTSOptions
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

class AudioGenerator:
    @staticmethod
    def generate_gtts(text, output_file, lang='id'):
        """
        Menghasilkan audio menggunakan Google Text-to-Speech
        
        Args:
        - text (str): Teks yang akan diubah menjadi audio
        - output_file (str): Path file output audio
        - lang (str): Bahasa teks
        """
        try:
            tts = gTTS(text, lang=lang)
            tts.save(output_file)
            logging.info(f"Audio saved as {output_file} (gTTS)")
        except Exception as e:
            logging.error(f"Error generating gTTS audio: {e}")

    @staticmethod
    def generate_playht(text, output_file, voice_url):
        """
        Menghasilkan audio menggunakan Play.ht
        
        Args:
        - text (str): Teks yang akan diubah menjadi audio
        - output_file (str): Path file output audio
        - voice_url (str): URL suara yang akan digunakan
        """
        try:
            # Konfigurasi Play.ht
            user_id = os.getenv("PLAY_HT_USER_ID")
            api_key = os.getenv("PLAY_HT_API_KEY")
            client = Client(user_id=user_id, api_key=api_key)

            options = TTSOptions(voice=voice_url)
            with open(output_file, "wb") as audio_file:
                for chunk in client.tts(text, options, voice_engine='PlayDialog', protocol='http'):
                    audio_file.write(chunk)
            
            logging.info(f"Audio saved as {output_file} (Play.ht) with voice: {voice_url}")
        except Exception as e:
            logging.error(f"Error generating Play.ht audio: {e}")

class ImageProcessor:
    @staticmethod
    def scale_image(image_path, target_height=400):
        """
        Scale gambar dengan mempertahankan rasio aspek
        
        Args:
        - image_path (str): Path gambar
        - target_height (int): Tinggi target gambar
        
        Returns:
        - PIL.Image: Gambar yang telah di-scale
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                aspect_ratio = width / height
                new_width = int(target_height * aspect_ratio)
                return img.resize((new_width, target_height), Image.Resampling.LANCZOS)
        except Exception as e:
            logging.error(f"Error scaling image: {e}")
            return None

class SubtitleGenerator:
    @staticmethod
    def create_subtitle_mask(w, h, text, fontsize=48):
        """
        Membuat mask subtitle dengan penanganan teks panjang
        
        Args:
        - w (int): Lebar frame
        - h (int): Tinggi frame
        - text (str): Teks subtitle
        - fontsize (int): Ukuran font
        
        Returns:
        - numpy.ndarray: Mask subtitle
        """
        mask = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(mask)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", fontsize)
        except:
            font = ImageFont.load_default()
        
        def wrap_text(text, font, max_width):
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                
                if bbox[2] - bbox[0] <= max_width:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines
        
        max_subtitle_width = w - 100
        current_fontsize = fontsize
        wrapped_lines = []
        
        while current_fontsize > 20:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", current_fontsize)
            wrapped_lines = wrap_text(text, font, max_subtitle_width)
            
            if len(wrapped_lines) <= 3:
                break
            
            current_fontsize -= 2
        
        wrapped_text = '\n'.join(wrapped_lines)
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (w - text_width) // 2
        y = (h - text_height) // 2
        
        outline_color = (0, 0, 0, 255)
        outline_width = 2
        for offset_x in range(-outline_width, outline_width + 1):
            for offset_y in range(-outline_width, outline_width + 1):
                draw.multiline_text((x + offset_x, y + offset_y), wrapped_text, 
                                    font=font, fill=outline_color, align='center')
        
        draw.multiline_text((x, y), wrapped_text, 
                            font=font, fill=(255, 255, 255, 255), align='center')
        
        return np.array(mask)

class Character:
    def __init__(self, name, image_path, voice_url, gender):
        """
        Inisialisasi karakter
        
        Args:
        - name (str): Nama karakter
        - image_path (str): Path gambar karakter
        - voice_url (str): URL suara karakter
        - gender (str): Gender karakter
        """
        self.name = name
        self.image_path = image_path
        self.voice_url = voice_url
        self.gender = gender
        self.scaled_image = None

    def scale_image(self, target_height=400):
        """Scale gambar karakter"""
        self.scaled_image = ImageProcessor.scale_image(self.image_path, target_height)
        return self.scaled_image

    def generate_audio(self, text, output_file, lang='en'):
        """
        Menghasilkan audio untuk karakter
        
        Args:
        - text (str): Teks yang akan diubah menjadi audio
        - output_file (str): Path file output audio
        - lang (str): Bahasa teks
        """
        if lang == 'id':
            AudioGenerator.generate_gtts(text, output_file)
        elif lang == 'en':
            AudioGenerator.generate_playht(text, output_file, self.voice_url)
        
        logging.info(f"Audio generated for {self.name} ({self.gender})")

class DialogClip:
    def __init__(self, background, char1, char2, text, speaking_char, duration):
        """
        Inisialisasi klip dialog
        
        Args:
        - background (PIL.Image): Latar bel akang
        - char1 (PIL.Image): Gambar karakter 1
        - char2 (PIL.Image): Gambar karakter 2
        - text (str): Teks dialog
        - speaking_char (int): Karakter yang berbicara (1 atau 2)
        - duration (float): Durasi klip
        """
        self.background = background
        self.char1 = char1
        self.char2 = char2
        self.text = text
        self.speaking_char = speaking_char
        self.duration = duration
        self.frame_width = 1920
        self.frame_height = 1080
        
    def __call__(self, t):
        frame = self.background.copy()
        
        char_height = 400
        margin = 10
        char1_width = self.char1.size[0]
        char2_width = self.char2.size[0]
        
        char1_x = margin
        char2_x = self.frame_width - char2_width - margin
        
        char_y = self.frame_height - char_height
        
        shake_amount = 5
        offset = int(shake_amount * np.sin(t * 10))
        
        if self.speaking_char == 1:
            frame.paste(self.char1, (char1_x + offset, char_y), self.char1)
            frame.paste(self.char2, (char2_x, char_y), self.char2)
        else:
            frame.paste(self.char1, (char1_x, char_y), self.char1)
            frame.paste(self.char2, (char2_x + offset, char_y), self.char2)
        
        subtitle = SubtitleGenerator.create_subtitle_mask(self.frame_width, self.frame_height, self.text)
        
        frame_array = np.array(frame)
        alpha_mask = subtitle[:, :, 3] > 0
        frame_array[alpha_mask] = subtitle[alpha_mask][:, :3]
        
        return frame_array



class VideoCreator:
    @staticmethod
    def create_conversation_video_oop(background_path, texts, languages, output_path="output.mp4"):
        """Membuat video dengan karakter dan subtitle"""
        background = Image.open(background_path).resize((1920, 1080))
    
        # Inisialisasi karakter
        host = Character(
            name="Host",
            image_path="karakter/karaktercowok1.png",
            voice_url="s3://voice-cloning-zero-shot/4adb8395-2eb3-4a8a-8a0d-0a78da2b7030/original/manifest.json",
            gender="male"
        )
    
        maya = Character(
            name="Maya",
            image_path="karakter/karaktercewek2.png",
            voice_url="s3://voice-cloning-zero-shot/a59cb96d-bba8-4e24-81f2-e60b888a0275/charlottenarrativesaad/manifest.json",
            gender="female"
        )

        host.scale_image()
        maya.scale_image()

        audio_files = [f"dialog_{i}.mp3" for i in range(len(texts))]
    
        for i, (text, output_file, lang) in enumerate(zip(texts, audio_files, languages)):
            # Tentukan karakter yang berbicara berdasarkan indeks
            is_host = i % 4 in [0, 1]  # Host berbicara pada indeks 0,1 dari setiap 4 dialog
            current_character = host if is_host else maya
            
            # Logic untuk pemilihan metode generate audio
            if lang == 'id':
                # Semua dialog Bahasa Indonesia menggunakan gTTS
                AudioGenerator.generate_gtts(text, output_file, lang='id')
            else:
                # Semua dialog Bahasa Inggris menggunakan Play.ht dengan voice masing-masing
                AudioGenerator.generate_playht(text, output_file, current_character.voice_url)
            
            print(i)
            print(f"{current_character.name} berbicara: {text}")

        clips = []
    
        for i, (text, audio_file) in enumerate(zip(texts, audio_files)):
            audio_clip = AudioFileClip(audio_file)
            duration = audio_clip.duration + 0.5
            speaking_char = 1 if i % 4 in [0, 1] else 2  # Sesuaikan dengan pola 4 dialog
        
            dialog = DialogClip(background, host.scaled_image, maya.scaled_image, text, speaking_char, duration)
            video_clip = VideoClip(dialog, duration=duration)
        
            final_clip = video_clip.set_audio(audio_clip)
            clips.append(final_clip)
    
        final_video = concatenate_videoclips(clips)
    
        final_video.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac'
        )
    
        for audio_file in audio_files:
            if os.path.exists(audio_file):
                os.remove(audio_file)


# Main program
if __name__ == "__main__":
    texts = [
        "Hai semuanya! Selamat datang di podcast 'Pikiran Random', tempat ide-ide gila jadi masuk akal! Kali ini aku nggak sendirian, aku bareng Maya! Halo Maya!",
        "Hey everyone! Welcome to the 'Random Thoughts' podcast, where crazy ideas make sense! Today, I'm not alone; I'm with Maya! Hi Maya!",
        "Halo semua! Terima kasih sudah mengundang aku. Ngomong-ngomong, 'pikiran random' ini kayaknya cocok banget sama hidupku!",
        "Hi everyone! Thanks for having me. By the way, 'random thoughts' perfectly describes my life!",
        "Haha, kita semua sama kok, Maya. Eh, pernah nggak sih kamu punya ide yang terlalu aneh sampai kamu mikir, 'Ini nggak mungkin berhasil'?",
        "Haha, we're all the same, Maya. So, have you ever had an idea so weird that you thought, 'This will never work'?",
        "Oh sering banget! Contohnya, waktu aku pengen belajar bahasa Inggris lewat lirik lagu. Aku coba nyanyi 'Shape of You', tapi malah terdengar kayak mantra.",
        "Oh, so many times! For example, when I tried to learn English through song lyrics. I sang 'Shape of You', but it sounded like a spell instead.",
        "Hahaha, jangan-jangan kamu bikin Ed Sheeran bingung! Tapi itu cara belajar yang seru, lho.",
        "Hahaha, you probably confused Ed Sheeran! But that's actually a fun way to learn.",
        "Iya, terus aku coba lagi dengan cara nonton film tanpa subtitle. Masalahnya, aku malah ketiduran karena nggak ngerti apa-apa.",
        "Yeah, then I tried watching movies without subtitles. The problem is, I fell asleep because I didn’t understand a thing.",
        "Waduh, itu tantangan banget sih. Tapi kan kamu tetep belajar dari pengalaman itu, kan?",
        "Wow, that's a real challenge. But you learned something from the experience, right?",
        "Iya, aku belajar kalau subtitle itu kayak sahabat sejati. Selalu ada di saat aku butuh.",
        "Yes, I learned that subtitles are like true friends. They're always there when you need them.",
        "Betul banget! Eh, ngomong-ngomong soal sahabat, kamu punya tips nggak buat orang yang lagi bingung cari tujuan hidup?",
        "Exactly! By the way, speaking of friends, do you have any tips for people who are confused about finding their life purpose?",
        "Hmm, menurut aku, coba tanya diri sendiri, apa hal yang bikin kamu senyum waktu melakukannya? Kalau itu jawabannya, fokus ke sana dulu.",
        "Hmm, I think you should ask yourself, what makes you smile when you do it? If that's the answer, focus on that first.",
        "Wah, itu bagus banget! Jadi misalnya aku senyum waktu makan martabak, artinya aku harus jadi tukang martabak?",
        "Wow, that's awesome! So if I smile when eating martabak, does that mean I should become a martabak seller?",
        "Haha, ya nggak gitu juga, Host! Tapi siapa tahu, kamu bisa bikin inovasi baru, martabak rasa pizza!",
        "Haha, not exactly, Host! But who knows, maybe you can create a new innovation, pizza-flavored martabak!",
        "Hmm, kayaknya aku lebih cocok jadi pelanggan setia martabak aja. Eh, Maya, kamu pernah merasa stuck nggak dalam belajar bahasa Inggris?",
        "Hmm, I think I’m better suited as a loyal martabak customer. Hey Maya, have you ever felt stuck while learning English?",
        "Oh sering banget! Kadang aku ngerasa, kenapa aku nggak paham-paham juga, padahal udah belajar lama.",
        "Oh, so many times! Sometimes I feel like, why don’t I understand it even after studying for so long?",
        "Terus apa yang kamu lakuin kalau udah kayak gitu?",
        "So, what do you do when you feel like that?",
        "Aku berhenti sebentar, terus nginget lagi kenapa aku mulai. Aku pengen bisa ngobrol sama banyak orang dari seluruh dunia.",
        "I take a break, then remind myself why I started. I want to be able to talk to people from all over the world.",
        "Wah, itu motivasi yang keren banget, Maya. Dan bener sih, kadang kita cuma perlu inget 'kenapa' kita mulai.",
        "Wow, that’s such a cool motivation, Maya. And it’s true, sometimes we just need to remember why we started.",
        "Iya, dan satu lagi, jangan lupa nikmatin prosesnya. Kalau nggak nikmatin, kita bakal gampang nyerah.",
        "Yes, and one more thing, don’t forget to enjoy the process. If you don’t enjoy it, you’ll easily give up.",
        "Setuju banget! Eh, ngomong-ngomong, kalau kamu bisa kasih pesan ke diri kamu di masa lalu, apa yang bakal kamu bilang?",
        "Totally agree! By the way, if you could send a message to your past self, what would you say?",
        "Aku bakal bilang, 'Hei, Maya, jangan takut salah. Semua orang belajar dari kesalahan.'",
        "I’d say, 'Hey Maya, don’t be afraid of making mistakes. Everyone learns from their mistakes.'",
        "Itu pesan yang bagus banget. Aku rasa banyak orang di luar sana juga butuh denger hal yang sama.",
        "That’s such a great message. I think a lot of people out there need to hear the same thing.",
        "Iya, semoga aja obrolan kita kali ini bisa bikin orang lebih semangat dan percaya diri!",
        "Yes, I hope our conversation today makes people more motivated and confident!",
        "Amin! Oke, teman-teman, itu aja untuk episode kali ini. Terima kasih, Maya, udah hadir di podcast ini.",
        "Amen! Okay, friends, that’s all for today’s episode. Thank you, Maya, for being on this podcast.",
        "Terima kasih juga sudah ngundang aku, Host! Sampai ketemu lagi semuanya!",
        "Thank you for inviting me too, Host! See you all next time!",
    ]

    languages = ['id', 'en'] * (len(texts) // 2)

    VideoCreator.create_conversation_video_oop(
        "background4.jpg",
        texts,
        languages,
        "output2.mp4"
    )

